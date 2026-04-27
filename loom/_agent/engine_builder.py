"""AgentEngine construction and wiring helpers."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from ..config import (
    AgentConfig,
    PolicyConfig,
    ToolAccessPolicy,
    ToolPolicy,
    ToolRateLimitPolicy,
)
from ..providers.base import LLMProvider
from ..runtime.engine import AgentEngine, EngineConfig
from ..runtime.heartbeat import Heartbeat, WatchSource
from ..runtime.heartbeat import HeartbeatConfig as RuntimeHeartbeatConfig
from ..tools.base import Tool
from ..tools.governance import GovernanceConfig
from .normalization import _resolve_compression_policy

if TYPE_CHECKING:
    from ..tools.schema import Tool as ToolSchema


class EngineBuilderMixin:
    if TYPE_CHECKING:
        config: AgentConfig
        _compiled_tools: list[Tool]
        _hook_manager: Any
        _ecosystem: Any
        _evolution_engine: Any
        _last_engine: Any
        _emit: Any
        _attach_pending_signals: Any

    def _build_engine(self, provider: LLMProvider) -> AgentEngine:
        engine = AgentEngine(
            provider=provider,
            config=EngineConfig(
                max_iterations=self.config.runtime.limits.max_iterations if self.config.runtime else 100,
                max_tokens=(
                    self.config.runtime.limits.max_context_tokens
                    if self.config.runtime and self.config.runtime.limits.max_context_tokens
                    else 200000
                ),
                model=self.config.model.name,
                temperature=self.config.generation.temperature,
                completion_max_tokens=self.config.generation.max_output_tokens or 4096,
                compression_policy=_resolve_compression_policy(self.config.runtime),
                enable_heartbeat=self.config.heartbeat is not None,
                enable_safety=self.config.runtime.features.enable_safety if self.config.runtime else True,
                enable_memory=bool(self.config.memory and self.config.memory.enabled),
                extensions=dict(self.config.generation.extensions),
                stream_output=bool(self.config.generation.extensions.get("stream", False)),
                continuity_policy=self.config.runtime.continuity if self.config.runtime else None,
                context_protocol=self.config.runtime.context if self.config.runtime else None,
                harness=self.config.runtime.harness if self.config.runtime else None,
                quality_gate=self.config.runtime.quality if self.config.runtime else None,
                delegation_policy=self.config.runtime.delegation if self.config.runtime else None,
                governance_policy=self.config.runtime.governance if self.config.runtime else None,
                feedback_policy=self.config.runtime.feedback if self.config.runtime else None,
                skill_injection_policy=(
                    self.config.runtime.skill_injection if self.config.runtime else None
                ),
            ),
            tools=[self._convert_tool_to_schema(tool) for tool in self._compiled_tools],
            memory_providers=(
                list(self.config.memory.providers)
                if self.config.memory and self.config.memory.enabled
                else []
            ),
        )

        self._configure_governance(engine)
        self._configure_heartbeat(engine)
        self._configure_safety(engine)
        self._configure_hooks(engine)
        self._configure_runtime_events(engine)
        self._configure_ecosystem(engine)
        self._configure_evolution(engine)
        self._attach_pending_signals(engine)
        self._last_engine = engine
        return engine

    def _configure_governance(self, engine: AgentEngine) -> None:
        policy = self.config.policy or PolicyConfig()
        tool_policy = policy.tools or ToolPolicy()
        access = tool_policy.access or ToolAccessPolicy()
        rate_limits = tool_policy.rate_limits or ToolRateLimitPolicy()

        engine.tool_governance.config = GovernanceConfig(
            allow_tools=set(access.allow),
            deny_tools=set(access.deny),
            allow_destructive=access.allow_destructive,
            read_only_only=access.read_only_only,
            max_calls_per_minute=rate_limits.max_calls_per_minute,
            current_context=policy.context.name,
        )

    def _configure_heartbeat(self, engine: AgentEngine) -> None:
        if not self.config.heartbeat:
            return

        hb_config = RuntimeHeartbeatConfig(
            T_hb=self.config.heartbeat.interval,
            delta_hb=self.config.heartbeat.min_entropy_delta,
            watch_sources=[
                WatchSource(type=source.kind.value, config=source.to_runtime_config())
                for source in self.config.heartbeat.watch_sources
            ],
            interrupt_policy=self.config.heartbeat.interrupt_policy.to_runtime_config(),
        )
        engine.heartbeat = Heartbeat(hb_config)

    def _configure_safety(self, engine: AgentEngine) -> None:
        if not self.config.safety_rules or engine.veto_authority is None:
            return

        from ..safety.veto import VetoRule

        for rule in self.config.safety_rules:
            engine.veto_authority.add_rule(
                VetoRule(
                    name=rule.name,
                    predicate=rule.matches,
                    reason=rule.reason,
                )
            )

    def _configure_hooks(self, engine: AgentEngine) -> None:
        """Wire hooks into the engine's HookManager.

        Two sources are merged in order:
        1. ``SafetyEvaluator`` callbacks declared in the agent policy config.
        2. Hooks previously registered on ``agent.hook_manager`` (the persistent
           agent-level HookManager used by PluginLoader and external callers).
        """
        policy = self.config.policy or PolicyConfig()
        for evaluator in getattr(policy, "evaluators", []) or []:
            if callable(getattr(evaluator, "evaluate", None)):
                engine.hook_manager.register("before_tool_call", evaluator.evaluate)

        # Merge agent-level hooks (registered via agent.hook_manager or PluginLoader)
        if self._hook_manager is not None:
            for event, handlers in self._hook_manager.hooks.items():
                for handler in handlers:
                    engine.hook_manager.register(event, handler)

    def _configure_runtime_events(self, engine: AgentEngine) -> None:
        """Forward selected engine events to the public Agent event API."""
        handlers = getattr(self, "_event_handlers", {})
        event_names = {
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
        }
        if not any(name in handlers for name in (*event_names, "*")):
            return
        forwarded: set[str] = getattr(
            engine,
            "_loom_agent_runtime_events_forwarded_names",
            set(),
        )

        def _forward_tool_result(**payload: Any) -> None:
            self._emit("tool_result", **payload)
            self._emit("after_tool", **payload)

        def _forward_event(event_name: str):
            def _handler(**payload: Any) -> None:
                self._emit(event_name, **payload)

            return _handler

        for event_name in sorted(event_names - {"tool_result", "after_tool"}):
            if (event_name in handlers or "*" in handlers) and event_name not in forwarded:
                engine.on(event_name, _forward_event(event_name))
                forwarded.add(event_name)

        if (
            any(name in handlers for name in ("tool_result", "after_tool", "*"))
            and "tool_result" not in forwarded
        ):
            engine.on("tool_result", _forward_tool_result)
            forwarded.add("tool_result")
        engine._loom_agent_runtime_events_forwarded_names = forwarded
        engine._loom_agent_runtime_events_forwarded = bool(forwarded)

    def _configure_ecosystem(self, engine: AgentEngine) -> None:
        """Wire the EcosystemManager into the engine if one has been initialised.

        Only activates when ``agent.ecosystem`` has been touched (lazy-created)
        or when the agent's mcp_bridge has servers registered.  MCP server
        instructions are injected into the system prompt inside
        ``engine.execute()``, and connected server tools are registered in
        the ToolRegistry at engine construction time via
        ``engine._register_mcp_tools()``.
        """
        if self._ecosystem is None:
            return
        engine.ecosystem_manager = self._ecosystem
        engine._register_mcp_tools(self._ecosystem)

    def _configure_evolution(self, engine: AgentEngine) -> None:
        """Subscribe the EvolutionEngine to the AgentEngine's event bus.

        Once subscribed, every ``tool_result`` event emitted by the engine
        is automatically collected into the FeedbackLoop, so evolution
        strategies receive real execution data when ``agent.evolution.evolve()``
        is called.
        """
        if self._evolution_engine is None:
            return
        self._evolution_engine.subscribe_to_engine(engine)

    def _convert_tool_to_schema(self, tool: Tool) -> ToolSchema:
        from ..tools.schema import Tool as ToolSchema
        from ..tools.schema import ToolDefinition, ToolParameter

        input_schema = tool.input_schema()
        properties = input_schema.get("properties", {})
        required = set(input_schema.get("required", []))

        definition = ToolDefinition(
            name=tool.metadata.name,
            description=tool.metadata.description,
            parameters=[
                ToolParameter(
                    name=parameter_name,
                    type=str(parameter_schema.get("type", "string")),
                    description=str(parameter_schema.get("description", "")),
                    required=parameter_name in required,
                    default=parameter_schema.get("default"),
                )
                for parameter_name, parameter_schema in properties.items()
            ],
            is_read_only=tool.metadata.is_read_only,
            is_destructive=tool.metadata.is_destructive,
            is_concurrency_safe=tool.metadata.is_concurrency_safe,
        )

        async def handler(**kwargs: Any) -> Any:
            result = tool.call(**kwargs)
            payload = result.get("result", result)
            if inspect.isawaitable(payload):
                return await payload
            return payload

        return ToolSchema(definition=definition, handler=handler)
