"""Agent Execution Engine - 整合 L*, C, M, H_b, S, Ψ

这是 Loom 的核心执行引擎，将所有组件整合在一起：
- L* (AgentLoop): Reason → Act → Observe → Δ 循环
- C (ContextManager): 五分区上下文管理
- M (MemoryStore): 会话和工作记忆
- H_b (Heartbeat): 后台感知层
- S (Tools): 工具注册和执行
- Ψ (VetoAuthority): 安全控制层
"""

import logging
import threading
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..context import CompressionPolicy
from ..memory import InMemoryStore, MemoryStore
from ..memory.semantic import SemanticMemory
from ..memory.working import WorkingMemory
from ..providers.base import LLMProvider
from ..runtime.context import ContextPolicy
from ..runtime.context_runtime import ContextRuntime
from ..runtime.feedback import FeedbackPolicy
from ..runtime.governance import GovernancePolicy
from ..runtime.harness_runner import HarnessRunner
from ..runtime.heartbeat import Heartbeat, HeartbeatConfig
from ..runtime.loop_runner import LoopDone, LoopRunner, LoopStreamEvent, RuntimeServices
from ..runtime.mcp_tool_registrar import MCPToolRegistrar
from ..runtime.memory_runtime import MemoryRuntime
from ..runtime.provider_runtime import ProviderRuntime
from ..runtime.run_lifecycle import RunLifecycleRuntime
from ..runtime.signal_runtime import SignalRuntime
from ..runtime.signals import (
    RuntimeSignal,
    SignalDecision,
)
from ..runtime.tool_runtime import ToolRuntime
from ..runtime.wiring import RuntimeWiring
from ..safety.hooks import HookManager
from ..safety.permissions import PermissionManager
from ..safety.veto import VetoAuthority
from ..tools.executor import ToolExecutor
from ..tools.governance import ToolGovernance
from ..tools.registry import ToolRegistry
from ..tools.schema import Tool

if TYPE_CHECKING:
    from ..ecosystem.integration import EcosystemManager

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """Engine configuration"""

    max_iterations: int = 100
    max_tokens: int = 200000
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    completion_max_tokens: int = 4096
    compression_policy: CompressionPolicy | None = None
    enable_heartbeat: bool = False
    enable_safety: bool = True
    enable_memory: bool = True
    extensions: dict = field(default_factory=dict)
    stream_output: bool = False
    continuity_policy: Any | None = None
    harness: Any | None = None
    quality_gate: Any | None = None
    delegation_policy: Any | None = None
    context_protocol: Any | None = None
    governance_policy: Any | None = None
    feedback_policy: Any | None = None
    skill_injection_policy: Any | None = None


class AgentEngine:
    """Agent execution engine integrating all Loom components"""

    def __init__(
        self,
        provider: LLMProvider,
        config: EngineConfig | None = None,
        tools: list[Tool] | None = None,
        permission_manager: PermissionManager | None = None,
        ecosystem_manager: "EcosystemManager | None" = None,
        memory_providers: list[Any] | None = None,
    ):
        self.provider = provider
        self.config = config or EngineConfig()

        # Core components
        self.context_protocol = self.config.context_protocol or ContextPolicy.manager(
            max_tokens=self.config.max_tokens,
            compression_policy=self.config.compression_policy,
            continuity=self.config.continuity_policy,
        )
        self.context_manager = self.context_protocol
        self.memory_store: MemoryStore = InMemoryStore()
        self.memory_providers: list[Any] = list(memory_providers or [])
        self.semantic_memory: SemanticMemory | None = (
            SemanticMemory() if self.config.enable_memory else None
        )
        # WorkingMemory: scratchpad for intermediate state + live dashboard binding
        self.working_memory = WorkingMemory()
        self.working_memory.dashboard = self.context_manager.partitions.working
        self.tool_registry = ToolRegistry()
        self.tool_governance = ToolGovernance()
        self.veto_authority = VetoAuthority() if self.config.enable_safety else None
        # Safety layers: hook → permission → veto → execute
        self.hook_manager = HookManager()
        self.permission_manager: PermissionManager | None = permission_manager
        self.governance_policy = self.config.governance_policy or GovernancePolicy.default(
            tool_governance=self.tool_governance,
            permission_manager=self.permission_manager,
            veto_authority=self.veto_authority,
        )
        self.skill_injection_policy = self.config.skill_injection_policy
        self.tool_executor = ToolExecutor(
            self.tool_registry,
            self.tool_governance,
            governance_policy=self.governance_policy,
        )
        self.tool_runtime = ToolRuntime(
            emit=self.emit,
            current_iteration=lambda: self._current_iteration,
            context_manager=self.context_manager,
            hook_manager=self.hook_manager,
            tool_registry=self.tool_registry,
            tool_executor=self.tool_executor,
            governance_policy=self.governance_policy,
            tool_governance=self.tool_governance,
            permission_manager=self.permission_manager,
            veto_authority=self.veto_authority,
        )
        # Ecosystem: MCP + plugins
        self.ecosystem_manager: "EcosystemManager | None" = ecosystem_manager
        self.heartbeat: Heartbeat | None = None
        self._event_handlers: dict[str, list[Callable[..., None]]] = {}
        self._event_handlers_lock = threading.RLock()
        self._current_iteration: int = 0
        self._loom_agent_runtime_events_forwarded = False
        self._loom_agent_runtime_events_forwarded_names: set[str] = set()
        self.signal_runtime = SignalRuntime(
            context_manager=self.context_manager,
            emit=self.emit,
        )
        self.feedback_policy = self.config.feedback_policy or FeedbackPolicy.none()
        self.feedback_policy.attach(self)
        self.context_runtime = ContextRuntime(
            context_manager=self.context_manager,
            ecosystem_manager=self.ecosystem_manager,
            skill_injection_policy=self.skill_injection_policy,
            emit=self.emit,
        )
        self.memory_runtime = MemoryRuntime(
            context_manager=self.context_manager,
            memory_store=self.memory_store,
            memory_providers=self.memory_providers,
            semantic_memory=self.semantic_memory,
        )
        self.provider_runtime = ProviderRuntime(
            provider=self.provider,
            config=self.config,
            context_manager=self.context_manager,
            emit=self.emit,
            current_iteration=lambda: self._current_iteration,
            build_provider_tools=lambda: self.tool_runtime.build_provider_tools(),
        )
        self.run_lifecycle = self._build_run_lifecycle()
        self.loop_runner = LoopRunner(
            services=self._build_runtime_services(),
        )
        self.harness_runner = HarnessRunner(
            harness=lambda: self.config.harness,
            run_loop=self.loop_runner.run_loop,
        )
        self.runtime_wiring = RuntimeWiring(self)

        # Register tools
        if tools:
            for tool in tools:
                self.tool_registry.register(tool)

        # Register MCP tools from connected ecosystem servers
        if ecosystem_manager:
            MCPToolRegistrar(self.tool_registry).register(ecosystem_manager)

        # Initialize heartbeat if enabled
        if self.config.enable_heartbeat:
            hb_config = HeartbeatConfig(T_hb=5.0)
            self.heartbeat = Heartbeat(hb_config)

    def ingest_signal(
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
        """Accept one runtime signal into the engine."""
        self.signal_runtime.context_manager = self.context_manager
        return self.signal_runtime.ingest_signal(
            signal,
            source=source,
            type=type,
            urgency=urgency,
            payload=payload,
            session_id=session_id,
            run_id=run_id,
            dedupe_key=dedupe_key,
        )

    async def execute(
        self,
        goal: str,
        instructions: str = "",
        context: dict | None = None,
        session_id: str | None = None,
        token_callback: "Callable[[str], Any] | None" = None,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute agent with full L* loop

        Args:
            goal: The goal/prompt to achieve
            instructions: System instructions
            context: Additional context dict
            session_id: Session ID for memory

        Returns:
            Execution result with output, artifacts, events
        """
        self._refresh_runtime_wiring()
        prepared = self.run_lifecycle.prepare(
            goal=goal,
            instructions=instructions,
            context=context,
            session_id=session_id,
            history=history,
        )
        try:
            # Execute through the configured harness strategy.
            result = await self.harness_runner.run(
                goal,
                instructions=prepared.instructions,
                context=context,
                session_id=session_id,
                token_callback=token_callback,
            )

            self._refresh_runtime_wiring()
            self.run_lifecycle.finalize_success(prepared, str(result.get("output", "")))
            return result

        finally:
            self.runtime_wiring.refresh_run_lifecycle()
            self.run_lifecycle.stop()

    async def execute_streaming(
        self,
        goal: str,
        instructions: str = "",
        context: dict | None = None,
        session_id: str | None = None,
        history: list[dict[str, Any]] | None = None,
    ) -> AsyncGenerator[Any, None]:
        """Run the L* loop and yield typed StreamEvents (Mode B).

        Yields one event per token/action so the caller can render
        thinking, tool calls, tool results, and final text independently.

        Args:
            goal: The goal/prompt to achieve.
            instructions: System instructions.
            context: Additional context dict.
            session_id: Session ID for memory persistence.

        Yields:
            ``StreamEvent`` instances — ``TextDelta``, ``ThinkingDelta``,
            ``ToolCallEvent``, ``ToolResultEvent``, ``DoneEvent``, or
            ``ErrorEvent``.
        """
        from ..types.stream import ErrorEvent

        self._refresh_runtime_wiring()
        prepared = self.run_lifecycle.prepare(
            goal=goal,
            instructions=instructions,
            context=context,
            session_id=session_id,
            history=history,
        )
        try:
            final_output = ""
            from ..types.stream import DoneEvent

            async for item in self.loop_runner.run_loop_core(goal, stream=True):
                if isinstance(item, LoopStreamEvent):
                    event = item.event
                    yield event
                    if getattr(event, "type", "") == "done":
                        final_output = str(getattr(event, "output", ""))
                elif isinstance(item, LoopDone):
                    final_output = item.output
                    yield DoneEvent(
                        output=item.output,
                        iterations=item.iterations,
                        status=item.status,
                    )

            self._refresh_runtime_wiring()
            self.run_lifecycle.finalize_success(prepared, final_output)
        except Exception as exc:
            yield ErrorEvent(message=str(exc))
        finally:
            self.runtime_wiring.refresh_run_lifecycle()
            self.run_lifecycle.stop()

    def on(self, event_name: str, handler: Callable[..., None]) -> None:
        """Subscribe handler to runtime events."""
        with self._event_handlers_lock:
            self._event_handlers.setdefault(event_name, []).append(handler)

    def off(self, event_name: str, handler: Callable[..., None]) -> None:
        """Unsubscribe handler from runtime events."""
        with self._event_handlers_lock:
            handlers = self._event_handlers.get(event_name)
            if not handlers:
                return
            self._event_handlers[event_name] = [h for h in handlers if h is not handler]

    def emit(self, event_name: str, *args: Any, **kwargs: Any) -> int:
        """Emit one runtime event to subscribers."""
        with self._event_handlers_lock:
            handlers = list(self._event_handlers.get(event_name, []))

        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception as exc:  # pragma: no cover - defensive path
                logger.error(
                    "Runtime event handler error: event=%s handler=%r err=%s",
                    event_name,
                    handler,
                    exc,
                    exc_info=True,
                )
        return len(handlers)

    def _refresh_runtime_wiring(self) -> None:
        """Refresh extracted runtimes from mutable engine fields (one call site per loop tick)."""
        self.runtime_wiring.refresh()

    def _build_runtime_services(self) -> RuntimeServices:
        """Build the explicit service boundary consumed by LoopRunner."""
        return RuntimeServices(
            context_manager=self.context_manager,
            memory_runtime=self.memory_runtime,
            max_iterations=lambda: self.config.max_iterations,
            set_current_iteration=lambda iteration: setattr(self, "_current_iteration", iteration),
            refresh_runtime_wiring=self._refresh_runtime_wiring,
            build_messages=self.context_runtime.build_messages,
            drain_signals=self.signal_runtime.drain_signals,
            build_completion_request=self.provider_runtime.build_completion_request,
            stream_provider_request=self.provider_runtime.stream_provider_request,
            call_llm=self.provider_runtime.call_llm,
            parse_tool_calls=self.tool_runtime.parse_tool_calls,
            execute_tools=self.tool_runtime.execute_tools,
            emit=self.emit,
        )

    def _build_run_lifecycle(self) -> RunLifecycleRuntime:
        """Build the single lifecycle coordinator used by all run modes."""
        return RunLifecycleRuntime(
            config=self.config,
            context_manager=self.context_manager,
            context_runtime=self.context_runtime,
            ecosystem_manager=self.ecosystem_manager,
            heartbeat=self.heartbeat,
            memory_runtime=self.memory_runtime,
            memory_enabled=lambda: self.config.enable_memory,
            drain_signals=self.signal_runtime.drain_signals,
            heartbeat_handler=self.signal_runtime.handle_heartbeat_event,
        )
