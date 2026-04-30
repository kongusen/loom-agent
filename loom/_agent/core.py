"""Core public Agent implementation."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any, cast

from .._config import AgentConfig, Generation, Model
from ..config import (
    Gateway,
    HeartbeatConfig,
    Instructions,
    Knowledge,
    KnowledgeBundle,
    KnowledgeEvidence,
    KnowledgeQuery,
    KnowledgeSource,
    MemoryConfig,
    OrchestrationConfig,
    PolicyConfig,
    RuntimeConfig,
    RuntimeFallback,
    RuntimeFallbackMode,
    SafetyRule,
    ScheduleConfig,
    ScheduledJob,
    Toolset,
    ToolSpec,
)
from ..providers.base import LLMProvider
from ..runtime import RunContext, RunEvent, RunResult, Session, SessionConfig, SessionStore
from ..runtime.capability import CapabilitySource, activate_capabilities
from ..runtime.capability_compiler import CapabilityCompiler
from ..runtime.engine import AgentEngine
from ..runtime.feedback import FeedbackEvent
from ..runtime.signals import (
    AttentionPolicy,
    RuntimeSignal,
    RuntimeSignalAdapter,
    SignalAdapter,
    SignalDecision,
    adapt_signal,
    coerce_signal,
)
from ..runtime.task import RuntimeTask
from ..tools.base import Tool
from .engine_builder import EngineBuilderMixin
from .knowledge import _build_knowledge_bundle
from .normalization import (
    _normalize_capability_specs,
    _normalize_config,
    _normalize_generation,
    _normalize_heartbeat_config,
    _normalize_knowledge_sources,
    _normalize_memory_config,
    _normalize_model,
    _normalize_policy_config,
    _normalize_runtime_config,
    _normalize_safety_rules,
    _normalize_tool_specs,
    _resolve_session_ttl_hours,
)
from .providers import ProviderMixin
from .tools import _compile_tool_spec

logger = logging.getLogger(__name__)


@dataclass(init=False)
class Agent(EngineBuilderMixin, ProviderMixin):
    """Loom's single public agent API."""

    config: AgentConfig
    _sessions: dict[str, Session] = field(default_factory=dict, init=False, repr=False)
    _sessions_lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _session_ttl_hours: float = field(default=24.0, init=False, repr=False)
    _compiled_tools: list[Tool] = field(default_factory=list, init=False, repr=False)
    _provider: LLMProvider | None = field(default=None, init=False, repr=False)
    _provider_resolved: bool = field(default=False, init=False, repr=False)
    _provider_from_resolver: bool = field(default=False, init=False, repr=False)
    _provider_validated: bool = field(default=False, init=False, repr=False)
    _ecosystem: Any = field(default=None, init=False, repr=False)
    _evolution_engine: Any = field(default=None, init=False, repr=False)
    _coordinator: Any = field(default=None, init=False, repr=False)
    _last_engine: Any = field(default=None, init=False, repr=False)
    _hook_manager: Any = field(default=None, init=False, repr=False)
    _event_handlers: dict[str, list[Callable[..., None]]] = field(
        default_factory=dict, init=False, repr=False
    )
    _event_handlers_lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False
    )
    _session_store: SessionStore | None = field(default=None, init=False, repr=False)
    _pending_signals: list[RuntimeSignal] = field(default_factory=list, init=False, repr=False)
    _pending_signals_lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False
    )
    _schedule_registry: Any = field(default=None, init=False, repr=False)
    _schedule_ticker: Any = field(default=None, init=False, repr=False)
    _gateways: dict[str, RuntimeSignalAdapter] = field(
        default_factory=dict, init=False, repr=False
    )

    def __init__(
        self,
        config: AgentConfig | None = None,
        *,
        model: Model | str | None = None,
        instructions: str | Instructions = "",
        generation: Generation | None = None,
        tools: list[ToolSpec | Toolset] | Toolset | None = None,
        capabilities: list[Any] | Any | None = None,
        skills: list[Any] | Any | None = None,
        policy: PolicyConfig | None = None,
        memory: MemoryConfig | bool | None = None,
        heartbeat: HeartbeatConfig | None = None,
        runtime: RuntimeConfig | None = None,
        orchestration: bool | OrchestrationConfig | None = None,
        schedule: list[ScheduledJob] | None = None,
        gateways: list[Any] | Any | None = None,
        safety_rules: list[SafetyRule] | None = None,
        knowledge: list[KnowledgeSource] | KnowledgeSource | Knowledge | None = None,
        harness: Any | None = None,
        quality: Any | None = None,
        governance: Any | None = None,
        delegation: Any | None = None,
        feedback: Any | None = None,
        session_store: SessionStore | None = None,
    ) -> None:
        """Create an Agent from either a full config or the primary user API.

        Preferred:
            ``Agent(model=Model.openai("gpt-5.1"), instructions="...")``

        Advanced configuration:
            ``Agent(config=AgentConfig(...))``
        """
        if config is not None:
            explicit_fields = {
                "model": model,
                "generation": generation,
                "tools": tools,
                "capabilities": capabilities,
                "skills": skills,
                "policy": policy,
                "memory": memory,
                "heartbeat": heartbeat,
                "runtime": runtime,
                "orchestration": orchestration,
                "schedule": schedule,
                "gateways": gateways,
                "safety_rules": safety_rules,
                "knowledge": knowledge,
                "harness": harness,
                "quality": quality,
                "governance": governance,
                "delegation": delegation,
                "feedback": feedback,
            }
            provided = [name for name, value in explicit_fields.items() if value is not None]
            if instructions:
                provided.append("instructions")
            if provided:
                raise TypeError(
                    "Agent() accepts either config=AgentConfig(...) or direct keyword fields, "
                    f"not both; got {', '.join(provided)}"
                )
            self.config = config
        else:
            if model is None:
                raise TypeError("Agent() missing required argument: 'model'")
            if runtime is not None and orchestration is not None:
                raise TypeError("Agent() accepts runtime= or orchestration=, not both")
            runtime = _coerce_runtime_policies(
                runtime or _coerce_orchestration_to_runtime(orchestration),
                harness=harness,
                quality=quality,
                governance=governance,
                delegation=delegation,
                feedback=feedback,
            )
            self.config = AgentConfig(
                model=_coerce_model(model),
                instructions=_coerce_instructions(instructions),
                generation=generation or Generation(),
                tools=_coerce_tool_entries(tools),
                capabilities=[
                    *_coerce_capability_entries(capabilities),
                    *_coerce_capability_entries(skills),
                ],
                policy=policy,
                memory=_coerce_memory_config(memory),
                heartbeat=heartbeat,
                runtime=runtime,
                schedule=list(schedule or []),
                safety_rules=list(safety_rules) if safety_rules is not None else None,
                knowledge=_coerce_knowledge_entries(knowledge),
                gateways=_coerce_gateway_entries(gateways),
            )

        self._sessions = {}
        self._sessions_lock = threading.RLock()
        self._session_ttl_hours = 24.0
        self._compiled_tools = []
        self._provider = None
        self._provider_resolved = False
        self._provider_from_resolver = False
        self._provider_validated = False
        self._ecosystem = None
        self._evolution_engine = None
        self._coordinator = None
        self._last_engine = None
        self._hook_manager = None
        self._event_handlers = {}
        self._event_handlers_lock = threading.RLock()
        self._session_store = session_store
        self._pending_signals = []
        self._pending_signals_lock = threading.RLock()
        self._schedule_registry = None
        self._schedule_ticker = None
        self._gateways = {}
        self.__post_init__()

    @classmethod
    def from_config(cls, config: AgentConfig) -> Agent:
        """Create an Agent from a reusable config/spec object."""
        return cls(config=config)

    def __post_init__(self) -> None:
        config = _normalize_config(self.config, AgentConfig, "config")
        declared_tools = _normalize_tool_specs(config.tools)
        capabilities = _normalize_capability_specs(config.capabilities)
        compiled_capabilities = CapabilityCompiler().compile(
            tools=declared_tools,
            capabilities=capabilities,
        )
        declared_tools = compiled_capabilities.tool_specs
        normalized_tools: list[ToolSpec | Toolset] = list(declared_tools)
        orchestration = _coerce_orchestration_config(config.orchestration)
        if config.runtime is not None and orchestration is not None:
            raise TypeError("AgentConfig accepts runtime or orchestration, not both")
        runtime = config.runtime or _coerce_orchestration_to_runtime(orchestration)
        config = replace(
            config,
            model=_normalize_model(config.model),
            tools=normalized_tools,
            capabilities=capabilities,
            policy=_normalize_policy_config(config.policy),
            memory=_normalize_memory_config(config.memory),
            heartbeat=_normalize_heartbeat_config(config.heartbeat),
            generation=_normalize_generation(config.generation),
            runtime=_normalize_runtime_config(runtime),
            orchestration=orchestration,
            schedule=_normalize_schedule_jobs(config.schedule),
            knowledge=_normalize_knowledge_sources(config.knowledge),
            safety_rules=_normalize_safety_rules(config.safety_rules),
        )
        self.config = config
        self._gateways = _index_gateways(config.gateways)
        self._activate_configured_capabilities(capabilities)
        self._compiled_tools = [_compile_tool_spec(tool) for tool in declared_tools]
        self._session_ttl_hours = _resolve_session_ttl_hours(config.runtime)

    @property
    def ecosystem(self) -> Any:
        """Lazily created EcosystemManager for plugins, skills, and MCP servers."""
        if self._ecosystem is None:
            from ..ecosystem.integration import EcosystemManager

            self._ecosystem = EcosystemManager()
        return self._ecosystem

    def _activate_configured_capabilities(self, capabilities: list[Any]) -> None:
        """Activate explicit MCP/skill capabilities into the agent ecosystem."""
        if not any(
            capability.source in {CapabilitySource.MCP, CapabilitySource.SKILL}
            for capability in capabilities
        ):
            return
        activate_capabilities(capabilities, self.ecosystem)

    @property
    def evolution(self) -> Any:
        """Lazily created EvolutionEngine for tracking execution feedback."""
        if self._evolution_engine is None:
            from ..evolution.engine import EvolutionEngine

            self._evolution_engine = EvolutionEngine()
        return self._evolution_engine

    @property
    def working_memory(self) -> Any:
        """WorkingMemory scratchpad from the most recently built engine.

        Provides a dict-based scratchpad (``set_scratch`` / ``get_scratch``)
        and a live binding to the current execution dashboard.  Returns None
        when no engine has been constructed yet for this agent.
        """
        # Access via the _last_engine attribute set by _build_engine
        engine = getattr(self, "_last_engine", None)
        if engine is not None:
            return engine.working_memory
        return None

    @property
    def hook_manager(self) -> Any:
        """Agent-level HookManager — persists across engine rebuilds.

        Hooks registered here survive session boundaries and are merged into
        every engine created by ``_build_engine()``.  This is the correct
        target for ``PluginLoader.apply_to_agent()`` and any external code
        that wants to attach hooks without holding a reference to the engine.
        """
        if self._hook_manager is None:
            from ..safety.hooks import HookManager

            self._hook_manager = HookManager()
        return self._hook_manager

    @property
    def coordinator(self) -> Any:
        """Lazily created Coordinator for multi-agent task orchestration."""
        if self._coordinator is None:
            from ..orchestration.coordinator import Coordinator
            from ..orchestration.events import CoordinationEventBus
            from ..orchestration.subagent import SubAgentManager

            self._coordinator = Coordinator(CoordinationEventBus())
            self._coordinator.register_agent(
                str(id(self)),
                SubAgentManager(parent=self),
            )
        return self._coordinator

    def resolve_knowledge(self, query: KnowledgeQuery) -> KnowledgeBundle:
        """Resolve configured knowledge sources for one retrieval request."""
        if not isinstance(query, KnowledgeQuery):
            raise TypeError(f"query must be KnowledgeQuery, got {type(query).__name__}")
        evidence: list[KnowledgeEvidence] = []
        for source in self.config.knowledge:
            resolved = source.resolve(query)
            if resolved.items or resolved.citations:
                evidence.append(resolved)
        return _build_knowledge_bundle(query, evidence)

    async def run(
        self,
        prompt: str | RuntimeTask,
        context: RunContext | None = None,
    ) -> RunResult:
        """Execute a one-off run."""
        return await self.session().run(prompt, context=context)

    async def stream(
        self,
        prompt: str | RuntimeTask,
        context: RunContext | None = None,
    ) -> AsyncIterator[RunEvent]:
        """Stream events for a one-off run."""
        async for event in self.session().stream(prompt, context=context):
            yield event

    async def run_streaming(
        self,
        prompt: str | RuntimeTask,
        context: RunContext | None = None,
    ) -> AsyncIterator[Any]:
        """Stream typed Mode B events for a one-off run.

        Yields ``StreamEvent`` instances so frontends can render each phase
        of the agent loop as it happens::

            async for event in agent.run_streaming("summarise latest news"):
                if event.type == "text_delta":
                    print(event.delta, end="", flush=True)
                elif event.type == "tool_call":
                    print(f"\\n[→ {event.name}]")
                elif event.type == "tool_result":
                    print(f"[← {event.name}: {event.content[:80]}]")
                elif event.type == "done":
                    print(f"\\n\\nDone in {event.iterations} steps.")

        Yields:
            ``ThinkingDelta``, ``TextDelta``, ``ToolCallEvent``,
            ``ToolResultEvent``, ``DoneEvent``, or ``ErrorEvent``.
        """
        async for event in self.session().run_streaming(prompt, context=context):
            yield event

    async def signal(
        self,
        signal: RuntimeSignal | str,
        *,
        source: str = "custom",
        type: str = "event",
        urgency: str = "normal",
        payload: dict[str, Any] | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        dedupe_key: str | None = None,
    ) -> SignalDecision:
        """Ingest a runtime signal from any producer."""
        normalized = coerce_signal(
            signal,
            source=source,
            type=type,
            urgency=urgency,  # type: ignore[arg-type]
            payload=payload,
            session_id=session_id,
            run_id=run_id,
            dedupe_key=dedupe_key,
        )
        if session_id:
            return await self.session(SessionConfig(id=session_id)).signal(normalized)

        engine = self._last_engine
        if engine is not None:
            return cast("SignalDecision", engine.ingest_signal(normalized))

        with self._pending_signals_lock:
            self._pending_signals.append(normalized)
        return AttentionPolicy().decide(normalized)

    async def receive(
        self,
        event: Any,
        *,
        adapter: RuntimeSignalAdapter | None = None,
        gateway: str | Gateway | RuntimeSignalAdapter | None = None,
        source: str | None = None,
        type: str | None = None,
        urgency: str | None = None,
        payload: dict[str, Any] | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        dedupe_key: str | None = None,
    ) -> SignalDecision:
        """Receive an external event through an optional signal adapter."""
        if adapter is None and gateway is not None:
            adapter = _resolve_gateway_adapter(gateway, self._gateways)
        normalized = adapt_signal(
            event,
            adapter=adapter,
            source=source,
            type=type,
            urgency=urgency,  # type: ignore[arg-type]
            payload=payload,
            session_id=session_id,
            run_id=run_id,
            dedupe_key=dedupe_key,
        )
        target_session_id = session_id or normalized.session_id
        return await self.signal(normalized, session_id=target_session_id)

    def on(self, event_name: str, handler: Callable[..., None]) -> None:
        """Subscribe to user-facing agent runtime events."""
        if not callable(handler):
            raise TypeError(f"handler must be callable, got {type(handler).__name__}")
        with self._event_handlers_lock:
            self._event_handlers.setdefault(event_name, []).append(handler)
        runtime_events = {
            "before_llm",
            "after_llm",
            "before_tool",
            "tool_result",
            "after_tool",
            "on_context_compact",
            "context_renewed",
            "signal_received",
            "signal_decided",
            "signal_dispatched",
            "*",
        }
        if event_name in runtime_events and self._last_engine is not None:
            self._configure_runtime_events(self._last_engine)

    def off(self, event_name: str, handler: Callable[..., None]) -> None:
        """Unsubscribe a previously registered runtime event handler."""
        with self._event_handlers_lock:
            handlers = self._event_handlers.get(event_name)
            if not handlers:
                return
            self._event_handlers[event_name] = [h for h in handlers if h is not handler]

    def _emit(self, event_name: str, **payload: Any) -> int:
        with self._event_handlers_lock:
            handlers = list(self._event_handlers.get(event_name, ()))
            handlers.extend(self._event_handlers.get("*", ()))
        for handler in handlers:
            try:
                handler(event_name=event_name, **payload)
            except Exception as exc:
                logger.warning("Agent event handler failed for %s: %s", event_name, exc)
        return len(handlers)

    def _attach_pending_signals(self, engine: AgentEngine) -> None:
        with self._pending_signals_lock:
            signals = self._pending_signals
            self._pending_signals = []
        for signal in signals:
            engine.ingest_signal(signal)

    def session(
        self,
        config: SessionConfig | None = None,
    ) -> Session:
        """Get or create a stateful session."""
        if config is None:
            return Session(self)
        if not isinstance(config, SessionConfig):
            raise TypeError(f"session config must be SessionConfig, got {type(config).__name__}")

        self._evict_old_sessions()
        with self._sessions_lock:
            if config.id is not None and config.id in self._sessions:
                session = self._sessions[config.id]
                metadata = config.to_metadata()
                if metadata:
                    session.metadata.update(metadata)
                    session._save_store_record()
                return session

            session = Session(self, config=config)
            self._sessions[session.id] = session
        return session

    def gateway(self, name: str) -> RuntimeSignalAdapter:
        """Return a configured gateway signal adapter by name."""
        try:
            return self._gateways[name]
        except KeyError as exc:
            raise KeyError(f"unknown gateway {name!r}") from exc

    def _evict_old_sessions(self, ttl_hours: float | None = None) -> int:
        """Evict sessions older than TTL to prevent unbounded growth."""
        hours = ttl_hours if ttl_hours is not None else self._session_ttl_hours
        if hours <= 0:
            return 0

        cutoff = datetime.now() - timedelta(hours=hours)
        evicted = 0

        with self._sessions_lock:
            expired_ids = [
                session_id
                for session_id, session in self._sessions.items()
                if session.created_at < cutoff
            ]
            for session_id in expired_ids:
                session = self._sessions.pop(session_id, None)
                if session is None:
                    continue
                session.expire()
                evicted += 1

        if evicted:
            logger.debug(
                "Evicted %s expired session(s) older than %.2f hours",
                evicted,
                hours,
            )
        return evicted

    def start_scheduler(self, *, interval_seconds: float = 1.0) -> Any:
        """Start the explicit in-process scheduler for configured jobs."""
        from ..runtime.cron import JobRegistry, ScheduleTicker

        if not self.config.schedule:
            raise ValueError("Agent.start_scheduler() requires at least one scheduled job")

        if self._schedule_ticker is not None and self._schedule_ticker.running:
            return self._schedule_ticker

        registry = JobRegistry()
        for job in self.config.schedule:
            registry.add(job)

        ticker = ScheduleTicker(registry, interval_seconds=interval_seconds)
        ticker.start(self._dispatch_scheduled_job)
        self._schedule_registry = registry
        self._schedule_ticker = ticker
        return ticker

    def stop_scheduler(self) -> None:
        """Stop the explicit in-process scheduler if it is running."""
        if self._schedule_ticker is not None:
            self._schedule_ticker.stop()

    def _dispatch_scheduled_job(self, job: ScheduledJob) -> None:
        next_run = job.next_run_at.isoformat() if job.next_run_at else ""
        session_id = f"scheduled:{job.id}"
        session = self.session(
            SessionConfig(
                id=session_id,
                metadata={"scheduled_job_id": job.id, **dict(job.metadata)},
            )
        )
        signal = RuntimeSignal.create(
            job.prompt,
            source="cron",
            type="scheduled_job",
            urgency="normal",
            payload={
                "job_id": job.id,
                "job_name": job.name,
                "prompt": job.prompt,
                "metadata": dict(job.metadata),
            },
            session_id=session_id,
            dedupe_key=f"cron:{job.id}:{next_run}",
        )

        async def _run_job() -> None:
            decision = await session.signal(signal)
            if decision.action != "run":
                return
            await session.run(job.prompt)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_run_job())
        else:
            loop.create_task(_run_job())

    def schedule(
        self,
        id: str,
        *,
        prompt: str,
        every: ScheduleConfig,
        name: str = "",
        enabled: bool = True,
        repeat: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledJob:
        """Append a scheduled prompt to this agent."""
        if not isinstance(every, ScheduleConfig):
            raise TypeError(f"every must be ScheduleConfig, got {type(every).__name__}")
        job = ScheduledJob(
            id=id,
            prompt=prompt,
            schedule=every,
            name=name,
            enabled=enabled,
            repeat=repeat,
            metadata=dict(metadata or {}),
        )
        self.config.schedule.append(job)
        if self._schedule_ticker is not None and self._schedule_ticker.running:
            self._schedule_registry.add(job)
        return job

    def every(
        self,
        *,
        id: str,
        prompt: str,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
        name: str = "",
        enabled: bool = True,
        repeat: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledJob:
        """Append an interval scheduled prompt to this agent."""
        return self.schedule(
            id,
            prompt=prompt,
            every=ScheduleConfig.interval(minutes=minutes, hours=hours, days=days),
            name=name,
            enabled=enabled,
            repeat=repeat,
            metadata=metadata,
        )

    def once(
        self,
        run_at: str | datetime,
        *,
        id: str,
        prompt: str,
        name: str = "",
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledJob:
        """Append a one-shot scheduled prompt to this agent."""
        return self.schedule(
            id,
            prompt=prompt,
            every=ScheduleConfig.once(run_at),
            name=name,
            enabled=enabled,
            repeat=1,
            metadata=metadata,
        )

    async def _execute(
        self,
        prompt: str,
        context: RunContext | None = None,
        *,
        session_id: str | None,
        run_id: str,
        engine: AgentEngine | None = None,
        token_callback: Any | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        self._emit(
            "before_run",
            run_id=run_id,
            session_id=session_id,
            prompt=prompt,
            context=context,
        )
        result: dict[str, Any]
        provider = self._get_provider()
        try:
            if provider is not None and not await self._ensure_provider_ready(provider):
                provider = None
            if provider is None:
                fallback = (
                    self.config.runtime.features.fallback
                    if self.config.runtime
                    else RuntimeFallback()
                )
                if fallback.mode == RuntimeFallbackMode.ERROR:
                    result = {
                        "status": "provider_unavailable",
                        "output": "",
                        "events": [
                            {
                                "type": "run.failed.provider_unavailable",
                                "run_id": run_id,
                            }
                        ],
                        "artifacts": [],
                    }
                else:
                    result = {
                        "status": "success",
                        "output": self._local_output(prompt, context),
                        "events": [
                            {
                                "type": "run.fallback",
                                "mode": "local_summary",
                                "run_id": run_id,
                            }
                        ],
                        "artifacts": [],
                    }
                self._emit(
                    "after_run",
                    run_id=run_id,
                    session_id=session_id,
                    prompt=prompt,
                    result=result,
                )
                self._record_runtime_feedback(
                    "after_run",
                    run_id=run_id,
                    session_id=session_id,
                    prompt=prompt,
                    result=result,
                    success=result.get("status") == "success",
                )
                return result

            if engine is None:
                engine = self._build_engine(provider)

            merged_context = context.to_payload() if context is not None else {}
            if self.config.knowledge:
                merged_context.setdefault(
                    "knowledge_sources",
                    [source.to_context_payload() for source in self.config.knowledge],
                )

            result = await engine.execute(
                goal=prompt,
                instructions=self.config.instructions,
                context=merged_context,
                session_id=session_id
                if self.config.memory and self.config.memory.enabled
                else None,
                token_callback=token_callback,
                history=history,
            )
        except Exception as exc:
            self._emit(
                "run_error",
                run_id=run_id,
                session_id=session_id,
                prompt=prompt,
                error=exc,
            )
            self._record_runtime_feedback(
                "run_error",
                run_id=run_id,
                session_id=session_id,
                prompt=prompt,
                error=exc,
                success=False,
            )
            raise

        self._emit(
            "after_run",
            run_id=run_id,
            session_id=session_id,
            prompt=prompt,
            result=result,
        )
        self._record_runtime_feedback(
            "after_run",
            run_id=run_id,
            session_id=session_id,
            prompt=prompt,
            result=result,
            success=result.get("status") == "success",
        )
        return result

    def _record_runtime_feedback(
        self,
        event_type: str,
        *,
        run_id: str | None,
        session_id: str | None,
        success: bool | None,
        **payload: Any,
    ) -> None:
        policy = self.config.runtime.feedback if self.config.runtime else None
        record = getattr(policy, "record", None)
        if not callable(record):
            return
        record(
            FeedbackEvent(
                type=event_type,
                payload=payload,
                run_id=run_id,
                session_id=session_id,
                success=success,
            )
        )


def _coerce_model(model: Model | str) -> Model:
    if isinstance(model, Model):
        return model
    if not isinstance(model, str):
        raise TypeError(
            f"model must be Model or provider:model string, got {type(model).__name__}"
        )

    provider, separator, name = model.partition(":")
    if not separator or not provider or not name:
        raise ValueError("model string must use 'provider:model-name' format")
    return Model(provider=provider, name=name)


def _coerce_instructions(instructions: str | Instructions) -> str:
    if isinstance(instructions, Instructions):
        return instructions.render()
    if isinstance(instructions, str):
        return instructions
    raise TypeError(
        f"instructions must be str or Instructions, got {type(instructions).__name__}"
    )


def _coerce_tool_entries(
    tools: list[ToolSpec | Toolset] | Toolset | None,
) -> list[ToolSpec | Toolset]:
    if tools is None:
        return []
    if isinstance(tools, Toolset):
        return [tools]
    if not isinstance(tools, list):
        raise TypeError(
            f"tools must be list[ToolSpec | Toolset] or Toolset, got {type(tools).__name__}"
        )
    return list(tools)


def _coerce_capability_entries(capabilities: list[Any] | Any | None) -> list[Any]:
    if capabilities is None:
        return []
    if isinstance(capabilities, list):
        return list(capabilities)
    return [capabilities]


def _coerce_memory_config(memory: MemoryConfig | bool | None) -> MemoryConfig | None:
    if isinstance(memory, MemoryConfig) or memory is None:
        return memory
    if isinstance(memory, bool):
        return MemoryConfig(enabled=memory) if memory else None
    raise TypeError(f"memory must be MemoryConfig, bool, or None, got {type(memory).__name__}")


def _coerce_knowledge_entries(
    knowledge: list[KnowledgeSource] | KnowledgeSource | Knowledge | None,
) -> list[KnowledgeSource]:
    if knowledge is None:
        return []
    if isinstance(knowledge, Knowledge):
        return knowledge.to_sources()
    if isinstance(knowledge, KnowledgeSource):
        return [knowledge]
    if not isinstance(knowledge, list):
        raise TypeError(
            "knowledge must be Knowledge, KnowledgeSource, list[KnowledgeSource], or None, "
            f"got {type(knowledge).__name__}"
        )
    return list(knowledge)


def _coerce_gateway_entries(gateways: list[Any] | Any | None) -> list[Any]:
    if gateways is None:
        return []
    if isinstance(gateways, list):
        return list(gateways)
    return [gateways]


def _index_gateways(gateways: list[Any]) -> dict[str, RuntimeSignalAdapter]:
    indexed: dict[str, RuntimeSignalAdapter] = {}
    for gateway in gateways:
        if isinstance(gateway, Gateway):
            indexed[gateway.name] = gateway.adapter
            continue
        if isinstance(gateway, SignalAdapter):
            indexed[gateway.source] = gateway
            continue
        adapt = getattr(gateway, "adapt", None)
        name = getattr(gateway, "name", None)
        if callable(adapt) and isinstance(name, str):
            indexed[name] = cast("RuntimeSignalAdapter", gateway)
            continue
        raise TypeError(
            "gateways entries must be Gateway or RuntimeSignalAdapter with a name, "
            f"got {type(gateway).__name__}"
        )
    return indexed


def _resolve_gateway_adapter(
    gateway: str | Gateway | RuntimeSignalAdapter,
    gateways: dict[str, RuntimeSignalAdapter],
) -> RuntimeSignalAdapter:
    if isinstance(gateway, str):
        try:
            return gateways[gateway]
        except KeyError as exc:
            raise KeyError(f"unknown gateway {gateway!r}") from exc
    if isinstance(gateway, Gateway):
        return gateway.adapter
    adapt = getattr(gateway, "adapt", None)
    if callable(adapt):
        return gateway
    raise TypeError("gateway must be str, Gateway, or RuntimeSignalAdapter")


def _coerce_runtime_policies(
    runtime: RuntimeConfig | None,
    *,
    harness: Any | None = None,
    quality: Any | None = None,
    governance: Any | None = None,
    delegation: Any | None = None,
    feedback: Any | None = None,
) -> RuntimeConfig | None:
    if not any(
        value is not None for value in (harness, quality, governance, delegation, feedback)
    ):
        return runtime
    resolved = runtime or RuntimeConfig.sdk()
    return replace(
        resolved,
        harness=harness if harness is not None else resolved.harness,
        quality=quality if quality is not None else resolved.quality,
        governance=governance if governance is not None else resolved.governance,
        delegation=delegation if delegation is not None else resolved.delegation,
        feedback=feedback if feedback is not None else resolved.feedback,
    )


def _coerce_orchestration_config(
    orchestration: bool | OrchestrationConfig | None,
) -> OrchestrationConfig | None:
    if orchestration is None or orchestration is False:
        return None
    if orchestration is True:
        return OrchestrationConfig.default()
    if isinstance(orchestration, OrchestrationConfig):
        return orchestration
    raise TypeError(
        "orchestration must be bool, OrchestrationConfig, or None, "
        f"got {type(orchestration).__name__}"
    )


def _coerce_orchestration_to_runtime(
    orchestration: bool | OrchestrationConfig | None,
) -> RuntimeConfig | None:
    config = _coerce_orchestration_config(orchestration)
    if config is None:
        return None
    return RuntimeConfig.orchestrated(
        max_depth=config.max_depth,
        planner=config.planner,
        gen_eval=config.gen_eval,
        delegation=config.delegation,
    )


def _normalize_schedule_jobs(jobs: list[ScheduledJob]) -> list[ScheduledJob]:
    normalized: list[ScheduledJob] = []
    for index, job in enumerate(jobs):
        if not isinstance(job, ScheduledJob):
            raise TypeError(f"schedule entries must be ScheduledJob, got {type(job).__name__}")
        if not isinstance(job.schedule, ScheduleConfig):
            raise TypeError(
                f"schedule[{index}].schedule must be ScheduleConfig, "
                f"got {type(job.schedule).__name__}"
            )
        normalized.append(job)
    return normalized
