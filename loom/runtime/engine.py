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
from typing import TYPE_CHECKING, Any, cast

from ..config import MemoryProvider
from ..context import CompressionPolicy
from ..memory import InMemoryStore, MemoryStore
from ..memory.semantic import MemoryEntry, SemanticMemory
from ..memory.working import WorkingMemory
from ..providers.base import (
    CompletionParams,
    CompletionRequest,
    LLMProvider,
    ProviderToolParameter,
    ProviderToolSpec,
)
from ..runtime.context import ContextProtocol
from ..runtime.feedback import FeedbackPolicy
from ..runtime.governance import GovernancePolicy
from ..runtime.heartbeat import Heartbeat, HeartbeatConfig
from ..runtime.loop import AgentLoop, LoopConfig
from ..runtime.signals import (
    AttentionPolicy,
    RuntimeSignal,
    SignalDecision,
    SignalQueue,
    coerce_signal,
)
from ..safety.hooks import AgentContext, HookDecision, HookManager
from ..safety.permissions import PermissionManager
from ..safety.veto import VetoAuthority
from ..tools.executor import ToolExecutor
from ..tools.governance import ToolGovernance
from ..tools.registry import ToolRegistry
from ..tools.schema import Tool
from ..types import LoopState, Message, ToolCall, ToolResult

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


@dataclass(slots=True)
class _LoopTrace:
    """Internal trace event collected by non-streaming runs."""

    event: dict[str, Any]


@dataclass(slots=True)
class _LoopStreamEvent:
    """Internal wrapper for user-visible streaming events."""

    event: Any


@dataclass(slots=True)
class _LoopDone:
    """Internal terminal result emitted by the shared loop runner."""

    status: str
    output: str
    iterations: int


class AgentEngine:
    """Agent execution engine integrating all Loom components"""

    def __init__(
        self,
        provider: LLMProvider,
        config: EngineConfig | None = None,
        tools: list[Tool] | None = None,
        permission_manager: PermissionManager | None = None,
        ecosystem_manager: "EcosystemManager | None" = None,
        memory_providers: list[MemoryProvider] | None = None,
    ):
        self.provider = provider
        self.config = config or EngineConfig()

        # Core components
        self.context_protocol = self.config.context_protocol or ContextProtocol.manager(
            max_tokens=self.config.max_tokens,
            compression_policy=self.config.compression_policy,
            continuity=self.config.continuity_policy,
        )
        self.context_manager = self.context_protocol
        self.memory_store: MemoryStore = InMemoryStore()
        self.memory_providers = list(memory_providers or [])
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
        # Ecosystem: MCP + plugins
        self.ecosystem_manager: "EcosystemManager | None" = ecosystem_manager
        self.heartbeat: Heartbeat | None = None
        self._event_handlers: dict[str, list[Callable[..., None]]] = {}
        self._event_handlers_lock = threading.RLock()
        self._current_iteration: int = 0
        self._loom_agent_runtime_events_forwarded = False
        self._loom_agent_runtime_events_forwarded_names: set[str] = set()
        self.attention_policy = AttentionPolicy()
        self.signal_queue = SignalQueue()
        self.feedback_policy = self.config.feedback_policy or FeedbackPolicy.none()
        self.feedback_policy.attach(self)

        # Register tools
        if tools:
            for tool in tools:
                self.tool_registry.register(tool)

        # Register MCP tools from connected ecosystem servers
        if ecosystem_manager:
            self._register_mcp_tools(ecosystem_manager)

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
        normalized = coerce_signal(
            signal,
            source=source,
            type=type,
            urgency=cast("Any", urgency),
            payload=payload,
            session_id=session_id,
            run_id=run_id,
            dedupe_key=dedupe_key,
        )
        self.emit("signal_received", signal=normalized)
        self.signal_queue.push(normalized)
        decision = self.attention_policy.decide(
            normalized,
            state=self.context_manager.dashboard.decision_state(),
        )
        self.emit("signal_decided", signal=normalized, decision=decision)
        return decision

    def _drain_signals(self) -> list[tuple[RuntimeSignal, SignalDecision]]:
        """Drain queued runtime signals into C_working."""
        drained: list[tuple[RuntimeSignal, SignalDecision]] = []
        for signal in self.signal_queue.drain():
            decision = self.attention_policy.decide(
                signal,
                state=self.context_manager.dashboard.decision_state(),
            )
            self.context_manager.ingest_signal(signal, decision)
            self.emit("signal_dispatched", signal=signal, decision=decision)
            drained.append((signal, decision))
        return drained

    @property
    def mcp_bridge(self) -> Any:
        """Return the MCPBridge from the ecosystem manager, or None."""
        if self.ecosystem_manager is not None:
            return self.ecosystem_manager.mcp_bridge
        return None

    def _register_mcp_tools(self, ecosystem_manager: "EcosystemManager") -> None:
        """Register tools from all connected MCP servers into the ToolRegistry."""
        from ..tools.schema import Tool as ToolSchema
        from ..tools.schema import ToolDefinition, ToolParameter

        bridge = ecosystem_manager.mcp_bridge
        for server_name, server in bridge.servers.items():
            if not server.connected or not server.tools:
                continue
            for tool_spec in server.tools:
                name = tool_spec.get("name", "")
                if not name:
                    continue
                scoped_name = f"mcp__{server_name}__{name}".replace(":", "__")

                # Build parameters from JSON Schema properties
                input_schema = tool_spec.get("inputSchema") or tool_spec.get("parameters") or {}
                props = input_schema.get("properties", {})
                required_set = set(input_schema.get("required", []))
                parameters = [
                    ToolParameter(
                        name=param_name,
                        type=param_info.get("type", "string"),
                        description=param_info.get("description", ""),
                        required=param_name in required_set,
                    )
                    for param_name, param_info in props.items()
                ]

                # Capture loop vars for closure
                _server_name = server_name
                _tool_name = name

                async def _handler(_sn=_server_name, _tn=_tool_name, **kwargs: Any) -> Any:
                    return bridge.execute_tool(_sn, _tn, **kwargs)

                schema_tool = ToolSchema(
                    definition=ToolDefinition(
                        name=scoped_name,
                        description=tool_spec.get("description", ""),
                        parameters=parameters,
                        is_read_only=_mcp_tool_bool(
                            tool_spec,
                            "is_read_only",
                            "readOnly",
                            "readOnlyHint",
                        ),
                        is_destructive=_mcp_tool_bool(
                            tool_spec,
                            "is_destructive",
                            "destructive",
                            "destructiveHint",
                        ),
                        is_concurrency_safe=_mcp_tool_bool(
                            tool_spec,
                            "is_concurrency_safe",
                            "concurrencySafe",
                            "concurrencySafeHint",
                        ),
                    ),
                    handler=_handler,
                )
                self.tool_registry.register(schema_tool)

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
        # Merge MCP server instructions into the system prompt
        if self.ecosystem_manager:
            mcp_additions = self.ecosystem_manager.get_system_prompt_additions()
            if mcp_additions:
                instructions = f"{instructions}\n\n{mcp_additions}".strip() if instructions else mcp_additions
        provider_prompt = self._memory_provider_system_prompt()
        if provider_prompt:
            instructions = f"{instructions}\n\n{provider_prompt}".strip()

        # Initialize context
        self.context_manager.current_goal = goal
        self._initialize_context(goal, instructions, context)
        self._inject_session_history(history)
        self._drain_signals()

        # Load session memory if available
        if session_id and self.config.enable_memory:
            self._load_session_memory(session_id)

        # Inject semantically relevant memories from previous runs
        if self.semantic_memory:
            self._inject_semantic_memories(goal)
        self._inject_provider_memories(goal, session_id)

        # Start heartbeat if enabled
        if self.heartbeat:
            self.heartbeat.start(self._on_heartbeat_event)

        try:
            # Execute L* loop
            result = await self._run_loop(goal, token_callback=token_callback)

            # Save session memory
            if session_id and self.config.enable_memory:
                self._save_session_memory(session_id)
            self._sync_memory_providers(goal, str(result.get("output", "")), session_id)

            return result

        finally:
            # Stop heartbeat
            if self.heartbeat:
                self.heartbeat.stop()

    async def _run_loop(
        self,
        goal: str,
        token_callback: "Callable[[str], Any] | None" = None,
    ) -> dict[str, Any]:
        """Run the L* execution loop and materialize a result dict."""
        events: list[dict[str, Any]] = []

        async for item in self._run_loop_core(
            goal,
            stream=False,
            token_callback=token_callback,
        ):
            if isinstance(item, _LoopTrace):
                events.append(item.event)
            elif isinstance(item, _LoopDone):
                return {
                    "status": item.status,
                    "output": item.output,
                    "events": events,
                    "iterations": item.iterations,
                }

        return {
            "status": "max_iterations",
            "output": "Max iterations reached",
            "events": events,
            "iterations": self._current_iteration,
        }

    async def _run_loop_core(
        self,
        goal: str,
        *,
        stream: bool,
        token_callback: "Callable[[str], Any] | None" = None,
    ) -> AsyncGenerator[_LoopTrace | _LoopStreamEvent | _LoopDone, None]:
        """Shared L* loop for batch and streaming execution."""
        loop = AgentLoop(LoopConfig(
            max_iterations=self.config.max_iterations,
            rho_threshold=1.0,
        ))

        iteration = 0
        messages: list[Message] = self._build_messages(goal)

        def _append(msg: Message) -> None:
            messages.append(msg)
            self.context_manager.partitions.history.append(msg)

        while iteration < self.config.max_iterations:
            iteration += 1
            self._current_iteration = iteration
            logger.debug(f"Loop iteration {iteration}, state: {loop.state}")

            if self._drain_signals():
                messages = self._build_messages(goal)
                yield _LoopTrace({"type": "signals.ingested", "iteration": iteration})

            # Sync dashboard pressure before each iteration
            rho = self.context_manager.rho
            self.context_manager.dashboard.update_rho(rho)

            # Check context pressure and compress if needed
            if self.context_manager.should_renew():
                logger.info("Context pressure ρ=1.0, renewing context")
                self.context_manager.renew()
                messages = self._build_messages(goal)
                self.emit("context_renewed", iteration=iteration)
                yield _LoopTrace({"type": "context.renewed", "iteration": iteration})

            elif strategy := self.context_manager.should_compress():
                logger.info(f"Compressing context with strategy: {strategy}")
                self.context_manager.compress(strategy)
                messages = self._build_messages(goal)
                self.emit(
                    "on_context_compact",
                    strategy=strategy,
                    iteration=iteration,
                    rho=self.context_manager.rho,
                )
                yield _LoopTrace({
                    "type": "context.compressed",
                    "strategy": strategy,
                    "iteration": iteration,
                })

            if loop.state == LoopState.REASON:
                if stream:
                    from ..types.stream import ErrorEvent, TextDelta, ToolCallEvent

                    if self._drain_signals():
                        messages = self._build_messages(goal)
                    request = self._build_completion_request(messages)
                    text_parts: list[str] = []
                    tool_calls_seen: list[ToolCall] = []

                    try:
                        self.emit(
                            "before_llm",
                            request=request,
                            iteration=iteration,
                            stream=True,
                        )
                        async for event in self._stream_provider_request(request):
                            yield _LoopStreamEvent(event)
                            if isinstance(event, TextDelta):
                                text_parts.append(event.delta)
                            elif isinstance(event, ToolCallEvent):
                                tool_calls_seen.append(
                                    ToolCall(
                                        id=event.id,
                                        name=event.name,
                                        arguments=event.arguments,
                                    )
                                )
                    except Exception as exc:
                        yield _LoopStreamEvent(ErrorEvent(message=str(exc)))
                        self.emit(
                            "after_llm",
                            request=request,
                            response=None,
                            iteration=iteration,
                            stream=True,
                            error=exc,
                        )
                        return

                    response = {
                        "content": "".join(text_parts),
                        "tool_calls": tool_calls_seen,
                    }
                    self.emit(
                        "after_llm",
                        request=request,
                        response=response,
                        iteration=iteration,
                        stream=True,
                        error=None,
                    )
                else:
                    if self._drain_signals():
                        messages = self._build_messages(goal)
                    response = await self._call_llm(messages, token_callback=token_callback)

                tool_calls = self._parse_tool_calls(response)

                if tool_calls:
                    content = str(response.get("content", "")).strip()
                    loop.state = LoopState.ACT
                    _append(Message(
                        role="assistant",
                        content=content,
                        tool_calls=tool_calls,
                    ))
                    yield _LoopTrace({
                        "type": "tools.requested",
                        "count": len(tool_calls),
                        "iteration": iteration,
                    })
                else:
                    output = str(response.get("content", "")).strip()
                    _append(Message(role="assistant", content=output))
                    if output.lower().startswith("error:"):
                        yield _LoopDone(
                            status="provider_error",
                            output=output,
                            iterations=iteration,
                        )
                        return
                    yield _LoopDone(status="success", output=output, iterations=iteration)
                    return

            elif loop.state == LoopState.ACT:
                last_message = messages[-1]
                tool_results = await self._execute_tools(last_message.tool_calls)
                if self._drain_signals():
                    messages = self._build_messages(goal)
                tool_names = {
                    tool_call.id: tool_call.name
                    for tool_call in last_message.tool_calls
                }

                error_count = 0
                for result in tool_results:
                    name = tool_names.get(result.tool_call_id)
                    if stream:
                        from ..types.stream import ToolResultEvent

                        content_str = (
                            result.content
                            if isinstance(result.content, str)
                            else str(result.content)
                        )
                        yield _LoopStreamEvent(ToolResultEvent(
                            tool_call_id=result.tool_call_id,
                            name=name or "",
                            content=content_str,
                            is_error=result.is_error,
                        ))

                    _append(Message(
                        role="tool",
                        content=result.content,
                        tool_call_id=result.tool_call_id,
                        name=name,
                    ))
                    if result.is_error:
                        error_count += 1
                    elif self.semantic_memory and isinstance(result.content, str) and result.content:
                        self.semantic_memory.add(MemoryEntry(
                            content=result.content,
                            metadata={
                                "tool": name,
                                "iteration": iteration,
                                "goal": self.context_manager.current_goal or "",
                            },
                        ))

                if error_count:
                    for _ in range(error_count):
                        self.context_manager.dashboard.increment_errors()

                yield _LoopTrace({
                    "type": "tools.executed",
                    "count": len(tool_results),
                    "iteration": iteration,
                })

                loop.state = LoopState.OBSERVE

            elif loop.state == LoopState.OBSERVE:
                loop.state = LoopState.DELTA

            elif loop.state == LoopState.DELTA:
                if self.context_manager.rho >= 0.9:
                    self.context_manager.renew()
                    messages = self._build_messages(goal)
                    self.emit("context_renewed", iteration=iteration)
                    yield _LoopTrace({"type": "context.renewed", "iteration": iteration})
                loop.state = LoopState.REASON

        output = self._message_text(messages[-1].content) if messages else "Max iterations reached"
        yield _LoopDone(status="max_iterations", output=output, iterations=iteration)

    def _initialize_context(self, goal: str, instructions: str, context: dict | None):
        """Initialize context partitions"""
        partitions = self.context_manager.partitions

        # System partition - instructions
        if instructions:
            partitions.system.append(Message(role="system", content=instructions))

        # Working partition - update dashboard with goal
        partitions.working.goal_progress = f"Goal: {goal}"
        partitions.working.scratchpad = goal

        # Memory partition - add context as memory
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            partitions.memory.append(Message(role="system", content=f"Context:\n{context_str}"))
        self._inject_runtime_skills(goal, context)

    def _inject_runtime_skills(self, goal: str, context: dict | None) -> None:
        """Refresh the C_skill partition for the current run."""
        self.context_manager.partitions.skill = []
        if self.ecosystem_manager is None:
            return

        from ..runtime.skills import SkillInjectionPolicy

        policy = self.skill_injection_policy or SkillInjectionPolicy.matching()
        selected = policy.select(
            self.ecosystem_manager.skill_registry,
            goal=goal,
            context=context,
        )
        rendered = policy.render(selected)
        self.context_manager.partitions.skill.extend(rendered)
        if rendered:
            self.emit(
                "skills_injected",
                skills=[skill.name for skill in selected],
                count=len(rendered),
            )

    def _inject_session_history(self, history: list[dict[str, Any]] | None) -> None:
        """Restore prior user/assistant turns into the history partition."""
        if not history:
            return
        for entry in history:
            role = entry.get("role")
            if role not in {"system", "user", "assistant"}:
                continue
            content = entry.get("content", "")
            self.context_manager.partitions.history.append(
                Message(
                    role=cast("Any", role),
                    content=content if isinstance(content, str) else str(content),
                )
            )

    def _build_messages(self, goal: str) -> list[Message]:
        """Build message list from context partitions"""
        render = getattr(self.context_manager, "render", None)
        if callable(render):
            return cast("list[Message]", render(goal))

        # Get all messages from partitions (includes dashboard)
        messages = self.context_manager.partitions.get_all_messages()

        # Add user goal as the latest message if not already present
        if not messages or messages[-1].role != "user":
            messages.append(Message(role="user", content=goal))

        return messages

    def _to_provider_messages(self, messages: list[Message]) -> list[dict]:
        """Convert internal Message list to provider-native dicts."""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.name,
                        "arguments": tc.arguments,
                    }
                    for tc in msg.tool_calls
                ],
                "tool_call_id": msg.tool_call_id,
                "name": msg.name,
            }
            for msg in messages
        ]

    async def _call_llm(
        self,
        messages: list[Message],
        token_callback: "Callable[[str], Any] | None" = None,
    ) -> dict[str, Any]:
        """Call LLM provider (batch or streaming)."""
        request = self._build_completion_request(messages)
        self.emit(
            "before_llm",
            request=request,
            iteration=self._current_iteration,
            stream=token_callback is not None,
        )

        try:
            if token_callback is not None:
                response = await self._complete_provider_request_streaming(request, token_callback)
            else:
                response = await self._complete_provider_request(request)
            self.emit(
                "after_llm",
                request=request,
                response=response,
                iteration=self._current_iteration,
                stream=token_callback is not None,
                error=None,
            )
            return {
                "content": response.content,
                "tool_calls": response.tool_calls,
                "usage": response.usage,
            }
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            self.emit(
                "after_llm",
                request=request,
                response=None,
                iteration=self._current_iteration,
                stream=token_callback is not None,
                error=e,
            )
            return {"content": f"Error: {e}"}

    async def _complete_provider_request(
        self,
        request: CompletionRequest,
    ) -> Any:
        if isinstance(self.provider, LLMProvider):
            return await self.provider.complete_request(request)
        return await self.provider.complete_response(request.messages, request.params)

    async def _complete_provider_request_streaming(
        self,
        request: CompletionRequest,
        token_callback: "Callable[[str], Any]",
    ) -> Any:
        if isinstance(self.provider, LLMProvider):
            return await self.provider.complete_request_streaming(request, token_callback)
        return await self.provider.complete_streaming(
            request.messages,
            request.params,
            token_callback,
        )

    async def _stream_provider_request(
        self,
        request: CompletionRequest,
    ) -> AsyncGenerator[Any, None]:
        if isinstance(self.provider, LLMProvider):
            async for event in self.provider.stream_request_events(request):
                yield event
            return
        async for event in self.provider.stream_events(request.messages, request.params):
            yield event

    def _build_completion_params(self) -> CompletionParams:
        """Build provider completion parameters for one model step."""
        return CompletionParams(
            model=self.config.model,
            max_tokens=self.config.completion_max_tokens,
            temperature=self.config.temperature,
            tools=self._build_provider_tools(),
            extensions=dict(self.config.extensions),
        )

    def _build_completion_request(self, messages: list[Message]) -> CompletionRequest:
        """Build the stable provider request object for one model step."""
        provider_messages = self._to_provider_messages(messages)
        params = self._build_completion_params()
        return CompletionRequest.create(
            provider_messages,
            params,
            metadata={
                "goal": self.context_manager.current_goal,
                "iteration": self._current_iteration,
                "tool_count": len(params.tools),
            },
        )

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

        # Merge MCP server instructions
        if self.ecosystem_manager:
            mcp_additions = self.ecosystem_manager.get_system_prompt_additions()
            if mcp_additions:
                instructions = f"{instructions}\n\n{mcp_additions}".strip() if instructions else mcp_additions
        provider_prompt = self._memory_provider_system_prompt()
        if provider_prompt:
            instructions = f"{instructions}\n\n{provider_prompt}".strip()

        self.context_manager.current_goal = goal
        self._initialize_context(goal, instructions, context)
        self._inject_session_history(history)
        self._drain_signals()

        if session_id and self.config.enable_memory:
            self._load_session_memory(session_id)

        if self.semantic_memory:
            self._inject_semantic_memories(goal)
        self._inject_provider_memories(goal, session_id)

        if self.heartbeat:
            self.heartbeat.start(self._on_heartbeat_event)

        try:
            final_output = ""
            async for event in self._run_loop_streaming(goal):
                if getattr(event, "type", "") == "done":
                    final_output = str(getattr(event, "output", ""))
                yield event

            if session_id and self.config.enable_memory:
                self._save_session_memory(session_id)
            self._sync_memory_providers(goal, final_output, session_id)
        except Exception as exc:
            yield ErrorEvent(message=str(exc))
        finally:
            if self.heartbeat:
                self.heartbeat.stop()

    async def _run_loop_streaming(self, goal: str) -> AsyncGenerator[Any, None]:
        """Inner L* loop that yields user-visible StreamEvents."""
        from ..types.stream import DoneEvent

        async for item in self._run_loop_core(goal, stream=True):
            if isinstance(item, _LoopStreamEvent):
                yield item.event
            elif isinstance(item, _LoopDone):
                yield DoneEvent(
                    output=item.output,
                    iterations=item.iterations,
                    status=item.status,
                )

    def _parse_tool_calls(self, response: dict) -> list[ToolCall]:
        """Parse tool calls from LLM response"""
        tool_calls = response.get("tool_calls", [])
        return [call for call in tool_calls if isinstance(call, ToolCall)]

    def _build_provider_tools(self) -> list[dict[str, Any] | ProviderToolSpec]:
        """Convert registered tool schemas into provider-native function specs."""
        return [tool.to_dict() for tool in self._build_provider_tool_specs()]

    def _build_provider_tool_specs(self) -> list[ProviderToolSpec]:
        """Convert registered tool schemas into typed provider tool specs."""
        provider_tools: list[ProviderToolSpec] = []
        for tool in self.tool_registry.list():
            provider_tools.append(
                ProviderToolSpec(
                    name=tool.definition.name,
                    description=tool.definition.description,
                    parameters=tuple(
                        ProviderToolParameter(
                            name=parameter.name,
                            type=parameter.type,
                            description=parameter.description,
                            required=parameter.required,
                            default=parameter.default,
                        )
                        for parameter in tool.definition.parameters
                    ),
                )
            )
        return provider_tools

    async def _execute_tools(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute tool calls through the safety pipeline: hook → permission → veto → execute"""
        results: list[ToolResult] = []

        for call in tool_calls:
            self.emit(
                "before_tool",
                tool_name=call.name,
                arguments=call.arguments,
                tool_call_id=call.id,
                iteration=self._current_iteration,
            )
            # 1. Hook check
            hook_decision: HookDecision | None = None
            agent_ctx = AgentContext(
                goal=self.context_manager.current_goal or "",
                step_count=self._current_iteration,
                tool_name=call.name,
                tool_arguments=call.arguments,
            )
            hook_outcome = self.hook_manager.evaluate(
                "before_tool_call",
                {"tool": call.name, "arguments": call.arguments},
                agent_ctx,
            )
            hook_decision = hook_outcome.decision
            if hook_decision == HookDecision.DENY:
                result = ToolResult(
                    tool_call_id=call.id,
                    content=f"Hook denied: {hook_outcome.message}",
                    is_error=True,
                )
                results.append(result)
                self.emit(
                    "tool_result",
                    tool_name=call.name,
                    result=result.content,
                    success=False,
                    tool_call_id=call.id,
                )
                continue

            # 2. Execute via tool executor; RuntimeGovernancePolicy unifies
            # permissions, veto, tool governance, and rate limits.
            self._sync_governance_policy()
            result = await self.tool_executor.execute(call, hook_decision=hook_decision)
            results.append(result)
            self.emit(
                "tool_result",
                tool_name=call.name,
                result=result.content,
                success=not result.is_error,
                tool_call_id=call.id,
            )

        return results

    def _sync_governance_policy(self) -> None:
        """Keep the default governance adapter aligned with mutable engine hooks."""
        if (
            hasattr(self.governance_policy, "tool_governance")
            and not getattr(
                self.governance_policy,
                "_uses_external_tool_governance",
                False,
            )
        ):
            self.governance_policy.tool_governance = self.tool_governance
        if (
            hasattr(self.governance_policy, "permission_manager")
            and not getattr(
                self.governance_policy,
                "_uses_external_permission_manager",
                False,
            )
        ):
            self.governance_policy.permission_manager = self.permission_manager
        if (
            hasattr(self.governance_policy, "veto_authority")
            and not getattr(
                self.governance_policy,
                "_uses_external_veto_authority",
                False,
            )
        ):
            self.governance_policy.veto_authority = self.veto_authority

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

    def _load_session_memory(self, session_id: str):
        """Load session memory into context"""
        memory_data = self.memory_store.load(session_id)
        if memory_data and "memory" in memory_data:
            for msg_dict in memory_data["memory"]:
                self.context_manager.partitions.memory.append(Message(**msg_dict))

    def _save_session_memory(self, session_id: str):
        """Save session memory"""
        memory_data = {
            "memory": [
                {"role": msg.role, "content": msg.content}
                for msg in self.context_manager.partitions.memory
            ]
        }
        self.memory_store.save(session_id, memory_data)

    def _inject_semantic_memories(self, goal: str) -> None:
        """Search semantic memory for goal-relevant entries and inject into memory partition.

        Injects up to 5 most relevant past tool results so the LLM can reference
        previous knowledge without those full messages occupying history space.
        """
        if not self.semantic_memory:
            return
        relevant = self.semantic_memory.search(goal, top_k=5)
        for entry in relevant:
            self.context_manager.partitions.memory.append(
                Message(role="system", content=f"[recalled] {entry.content}")
            )

    def _memory_provider_system_prompt(self) -> str:
        blocks: list[str] = []
        for provider in self.memory_providers:
            if not self._is_memory_provider_available(provider):
                continue
            try:
                block = provider.system_prompt()
            except Exception as exc:
                self._log_memory_provider_error(provider, "system_prompt", exc)
                continue
            if block.strip():
                blocks.append(block.strip())
        return "\n\n".join(blocks)

    def _inject_provider_memories(self, goal: str, session_id: str | None) -> None:
        for provider in self.memory_providers:
            if not self._is_memory_provider_available(provider):
                continue
            try:
                recalled = provider.prefetch(goal, session_id=session_id)
            except Exception as exc:
                self._log_memory_provider_error(provider, "prefetch", exc)
                continue
            if recalled.strip():
                self.context_manager.partitions.memory.append(
                    Message(
                        role="system",
                        content=f"[memory:{self._memory_provider_name(provider)}] {recalled}",
                    )
                )

    def _sync_memory_providers(
        self,
        user_content: str,
        assistant_content: str,
        session_id: str | None,
    ) -> None:
        if not assistant_content:
            return
        for provider in self.memory_providers:
            if not self._is_memory_provider_available(provider):
                continue
            try:
                provider.sync_turn(
                    user_content,
                    assistant_content,
                    session_id=session_id,
                )
            except Exception as exc:
                self._log_memory_provider_error(provider, "sync_turn", exc)

    def _is_memory_provider_available(self, provider: MemoryProvider) -> bool:
        try:
            return provider.is_available()
        except Exception as exc:
            self._log_memory_provider_error(provider, "is_available", exc)
            return False

    def _log_memory_provider_error(
        self,
        provider: MemoryProvider,
        operation: str,
        exc: Exception,
    ) -> None:
        logger.warning(
            "Memory provider %s failed during %s: %s",
            self._memory_provider_name(provider),
            operation,
            exc,
        )

    def _memory_provider_name(self, provider: MemoryProvider) -> str:
        try:
            return str(getattr(provider, "name", type(provider).__name__))
        except Exception:
            return type(provider).__name__

    def _on_heartbeat_event(self, event: dict, urgency: str):
        """Handle heartbeat events as normalized runtime signals."""
        logger.info(f"Heartbeat event ({urgency}): {event}")
        summary = str(event.get("summary") or event.get("type") or "Heartbeat event")
        signal = RuntimeSignal.create(
            summary,
            source=str(event.get("source") or "heartbeat"),
            type=str(event.get("type") or "event"),
            urgency=cast("Any", urgency),
            payload=dict(event),
            dedupe_key=event.get("event_id"),
        )
        self.ingest_signal(signal)

    def _message_text(self, content: str | list[Any]) -> str:
        """Normalize message content for terminal outputs."""
        if isinstance(content, str):
            return content
        return str(content)


def _mcp_tool_bool(
    tool_spec: dict[str, Any],
    direct_key: str,
    camel_key: str,
    annotation_key: str,
) -> bool:
    """Read common MCP tool metadata boolean shapes."""
    annotations = tool_spec.get("annotations")
    if not isinstance(annotations, dict):
        annotations = {}
    for value in (
        tool_spec.get(direct_key),
        tool_spec.get(camel_key),
        annotations.get(annotation_key),
    ):
        if value is not None:
            return bool(value)
    return False
