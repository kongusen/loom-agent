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

from ..context import CompressionPolicy, ContextManager
from ..memory import InMemoryStore, MemoryStore
from ..memory.semantic import MemoryEntry, SemanticMemory
from ..memory.working import WorkingMemory
from ..providers.base import CompletionParams, LLMProvider
from ..runtime.heartbeat import Heartbeat, HeartbeatConfig
from ..runtime.loop import AgentLoop, LoopConfig
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


class AgentEngine:
    """Agent execution engine integrating all Loom components"""

    def __init__(
        self,
        provider: LLMProvider,
        config: EngineConfig | None = None,
        tools: list[Tool] | None = None,
        permission_manager: PermissionManager | None = None,
        ecosystem_manager: "EcosystemManager | None" = None,
    ):
        self.provider = provider
        self.config = config or EngineConfig()

        # Core components
        self.context_manager = ContextManager(
            max_tokens=self.config.max_tokens,
            compression_policy=self.config.compression_policy,
        )
        self.memory_store: MemoryStore = InMemoryStore()
        self.semantic_memory: SemanticMemory | None = (
            SemanticMemory() if self.config.enable_memory else None
        )
        # WorkingMemory: scratchpad for intermediate state + live dashboard binding
        self.working_memory = WorkingMemory()
        self.working_memory.dashboard = self.context_manager.partitions.working
        self.tool_registry = ToolRegistry()
        self.tool_governance = ToolGovernance()
        self.tool_executor = ToolExecutor(self.tool_registry, self.tool_governance)
        self.veto_authority = VetoAuthority() if self.config.enable_safety else None
        # Safety layers: hook → permission → veto → execute
        self.hook_manager = HookManager()
        self.permission_manager: PermissionManager | None = permission_manager
        # Ecosystem: MCP + plugins
        self.ecosystem_manager: "EcosystemManager | None" = ecosystem_manager
        self.heartbeat: Heartbeat | None = None
        self._event_handlers: dict[str, list[Callable[..., None]]] = {}
        self._event_handlers_lock = threading.RLock()
        self._current_iteration: int = 0

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

    @property
    def mcp_bridge(self) -> Any:
        """Return the MCPBridge from the ecosystem manager, or None."""
        if self.ecosystem_manager is not None:
            return self.ecosystem_manager.mcp_bridge
        return None

    def _register_mcp_tools(self, ecosystem_manager: "EcosystemManager") -> None:
        """Register tools from all connected MCP servers into the ToolRegistry."""
        from ..tools.schema import Tool as ToolSchema, ToolDefinition, ToolParameter

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

        # Initialize context
        self.context_manager.current_goal = goal
        self._initialize_context(goal, instructions, context)

        # Load session memory if available
        if session_id and self.config.enable_memory:
            self._load_session_memory(session_id)

        # Inject semantically relevant memories from previous runs
        if self.semantic_memory:
            self._inject_semantic_memories(goal)

        # Start heartbeat if enabled
        if self.heartbeat:
            self.heartbeat.start(self._on_heartbeat_event)

        try:
            # Execute L* loop
            result = await self._run_loop(goal, token_callback=token_callback)

            # Save session memory
            if session_id and self.config.enable_memory:
                self._save_session_memory(session_id)

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
        """Run the L* execution loop"""
        loop = AgentLoop(LoopConfig(
            max_iterations=self.config.max_iterations,
            rho_threshold=1.0,
        ))

        iteration = 0
        # Seed from partitions; new messages are tracked here AND written back to history
        messages: list[Message] = self._build_messages(goal)
        # Watermark: only messages beyond this index are "new" (need to be written to history)
        _history_watermark = len(messages)
        events: list[dict] = []

        def _append(msg: Message) -> None:
            """Append a message to the local transcript AND to partitions.history."""
            messages.append(msg)
            self.context_manager.partitions.history.append(msg)

        while iteration < self.config.max_iterations:
            iteration += 1
            self._current_iteration = iteration
            logger.debug(f"Loop iteration {iteration}, state: {loop.state}")

            # Sync dashboard pressure before each iteration
            rho = self.context_manager.rho
            self.context_manager.dashboard.update_rho(rho)

            # Check context pressure and compress if needed
            if self.context_manager.should_renew():
                logger.info("Context pressure ρ=1.0, renewing context")
                self.context_manager.renew()
                # Rebuild message list from renewed partitions
                messages = self._build_messages(goal)
                _history_watermark = len(messages)
                events.append({"type": "context.renewed", "iteration": iteration})

            elif strategy := self.context_manager.should_compress():
                logger.info(f"Compressing context with strategy: {strategy}")
                self.context_manager.compress(strategy)
                # Rebuild to reflect compressed history
                messages = self._build_messages(goal)
                _history_watermark = len(messages)
                events.append({"type": "context.compressed", "strategy": strategy})

            # Execute loop state
            if loop.state == LoopState.REASON:
                # Reason: call LLM to get the next model step
                response = await self._call_llm(messages, token_callback=token_callback)

                # Parse response for tool calls
                tool_calls = self._parse_tool_calls(response)

                if tool_calls:
                    content = str(response.get("content", "")).strip()
                    loop.state = LoopState.ACT
                    _append(Message(
                        role="assistant",
                        content=content,
                        tool_calls=tool_calls,
                    ))
                    events.append({
                        "type": "tools.requested",
                        "count": len(tool_calls),
                        "iteration": iteration,
                    })
                else:
                    # No tool calls → terminal answer; LLM is done
                    output = str(response.get("content", "")).strip()
                    _append(Message(role="assistant", content=output))
                    if output.lower().startswith("error:"):
                        return {
                            "status": "provider_error",
                            "output": output,
                            "events": events,
                            "iterations": iteration,
                        }
                    return {
                        "status": "success",
                        "output": output,
                        "events": events,
                        "iterations": iteration,
                    }

            elif loop.state == LoopState.ACT:
                # Act: Execute tool calls
                last_message = messages[-1]
                tool_results = await self._execute_tools(last_message.tool_calls)
                tool_names = {
                    tool_call.id: tool_call.name
                    for tool_call in last_message.tool_calls
                }

                error_count = 0
                for result in tool_results:
                    _append(Message(
                        role="tool",
                        content=result.content,
                        tool_call_id=result.tool_call_id,
                        name=tool_names.get(result.tool_call_id),
                    ))
                    if result.is_error:
                        error_count += 1
                    elif self.semantic_memory and isinstance(result.content, str) and result.content:
                        # Save successful tool results to semantic memory for future recall
                        self.semantic_memory.add(MemoryEntry(
                            content=result.content,
                            metadata={
                                "tool": tool_names.get(result.tool_call_id),
                                "iteration": iteration,
                                "goal": self.context_manager.current_goal or "",
                            },
                        ))

                if error_count:
                    for _ in range(error_count):
                        self.context_manager.dashboard.increment_errors()

                events.append({
                    "type": "tools.executed",
                    "count": len(tool_results),
                    "iteration": iteration,
                })

                loop.state = LoopState.OBSERVE

            elif loop.state == LoopState.OBSERVE:
                # Observe: context is already updated via _append(); go to Δ
                loop.state = LoopState.DELTA

            elif loop.state == LoopState.DELTA:
                # Δ: The last message is always a tool result here.
                # Context pressure check before returning to REASON.
                if self.context_manager.rho >= 0.9:
                    self.context_manager.renew()
                    messages = self._build_messages(goal)
                    _history_watermark = len(messages)
                    events.append({"type": "context.renewed", "iteration": iteration})
                loop.state = LoopState.REASON

        # Max iterations reached
        output = self._message_text(messages[-1].content) if messages else "Max iterations reached"
        return {
            "status": "max_iterations",
            "output": output,
            "events": events,
            "iterations": iteration,
        }

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

    def _build_messages(self, goal: str) -> list[Message]:
        """Build message list from context partitions"""
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
        provider_messages = self._to_provider_messages(messages)

        params = CompletionParams(
            model=self.config.model,
            max_tokens=self.config.completion_max_tokens,
            temperature=self.config.temperature,
            tools=self._build_provider_tools(),
            extensions=dict(self.config.extensions),
        )

        try:
            if token_callback is not None:
                response = await self.provider.complete_streaming(
                    provider_messages, params, token_callback
                )
            else:
                response = await self.provider.complete_response(provider_messages, params)
            return {
                "content": response.content,
                "tool_calls": response.tool_calls,
                "usage": response.usage,
            }
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"content": f"Error: {e}"}

    async def execute_streaming(
        self,
        goal: str,
        instructions: str = "",
        context: dict | None = None,
        session_id: str | None = None,
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

        self.context_manager.current_goal = goal
        self._initialize_context(goal, instructions, context)

        if session_id and self.config.enable_memory:
            self._load_session_memory(session_id)

        if self.semantic_memory:
            self._inject_semantic_memories(goal)

        if self.heartbeat:
            self.heartbeat.start(self._on_heartbeat_event)

        try:
            async for event in self._run_loop_streaming(goal):
                yield event

            if session_id and self.config.enable_memory:
                self._save_session_memory(session_id)
        except Exception as exc:
            yield ErrorEvent(message=str(exc))
        finally:
            if self.heartbeat:
                self.heartbeat.stop()

    async def _run_loop_streaming(self, goal: str) -> AsyncGenerator[Any, None]:
        """Inner L* loop that yields StreamEvents."""
        from ..types.stream import (
            DoneEvent,
            ErrorEvent,
            TextDelta,
            ToolCallEvent,
            ToolResultEvent,
        )

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

            rho = self.context_manager.rho
            self.context_manager.dashboard.update_rho(rho)

            if self.context_manager.should_renew():
                self.context_manager.renew()
                messages = self._build_messages(goal)
            elif strategy := self.context_manager.should_compress():
                self.context_manager.compress(strategy)
                messages = self._build_messages(goal)

            # ── REASON: stream LLM tokens ──────────────────────────────────
            if loop.state == LoopState.REASON:
                provider_messages = self._to_provider_messages(messages)
                params = CompletionParams(
                    model=self.config.model,
                    max_tokens=self.config.completion_max_tokens,
                    temperature=self.config.temperature,
                    tools=self._build_provider_tools(),
                    extensions=dict(self.config.extensions),
                )

                text_parts: list[str] = []
                tool_calls_seen: list[ToolCall] = []

                try:
                    async for ev in self.provider.stream_events(provider_messages, params):
                        yield ev
                        if isinstance(ev, TextDelta):
                            text_parts.append(ev.delta)
                        elif isinstance(ev, ToolCallEvent):
                            tool_calls_seen.append(
                                ToolCall(id=ev.id, name=ev.name, arguments=ev.arguments)
                            )
                except Exception as exc:
                    yield ErrorEvent(message=str(exc))
                    return

                content = "".join(text_parts)

                if tool_calls_seen:
                    _append(Message(
                        role="assistant",
                        content=content,
                        tool_calls=tool_calls_seen,
                    ))
                    loop.state = LoopState.ACT
                else:
                    _append(Message(role="assistant", content=content))
                    yield DoneEvent(output=content, iterations=iteration, status="success")
                    return

            # ── ACT: execute tools, yield results ──────────────────────────
            elif loop.state == LoopState.ACT:
                last_message = messages[-1]
                tool_results = await self._execute_tools(last_message.tool_calls)
                tool_names = {tc.id: tc.name for tc in last_message.tool_calls}

                for result in tool_results:
                    name = tool_names.get(result.tool_call_id, "")
                    content_str = (
                        result.content
                        if isinstance(result.content, str)
                        else str(result.content)
                    )
                    yield ToolResultEvent(
                        tool_call_id=result.tool_call_id,
                        name=name,
                        content=content_str,
                        is_error=result.is_error,
                    )
                    _append(Message(
                        role="tool",
                        content=result.content,
                        tool_call_id=result.tool_call_id,
                        name=name,
                    ))
                    if result.is_error:
                        self.context_manager.dashboard.increment_errors()
                    elif self.semantic_memory and isinstance(result.content, str) and result.content:
                        self.semantic_memory.add(MemoryEntry(
                            content=result.content,
                            metadata={
                                "tool": name,
                                "iteration": iteration,
                                "goal": self.context_manager.current_goal or "",
                            },
                        ))

                loop.state = LoopState.OBSERVE

            elif loop.state == LoopState.OBSERVE:
                loop.state = LoopState.DELTA

            elif loop.state == LoopState.DELTA:
                if self.context_manager.rho >= 0.9:
                    self.context_manager.renew()
                    messages = self._build_messages(goal)
                loop.state = LoopState.REASON

        last_output = self._message_text(messages[-1].content) if messages else ""
        yield DoneEvent(output=last_output, iterations=iteration, status="max_iterations")

    def _parse_tool_calls(self, response: dict) -> list[ToolCall]:
        """Parse tool calls from LLM response"""
        tool_calls = response.get("tool_calls", [])
        return [call for call in tool_calls if isinstance(call, ToolCall)]

    def _build_provider_tools(self) -> list[dict[str, Any]]:
        """Convert registered tool schemas into provider-native function specs."""
        provider_tools: list[dict[str, Any]] = []
        for tool in self.tool_registry.list():
            provider_tools.append(
                {
                    "name": tool.definition.name,
                    "description": tool.definition.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            parameter.name: {
                                "type": parameter.type,
                                **(
                                    {"description": parameter.description}
                                    if parameter.description else {}
                                ),
                                **(
                                    {"default": parameter.default}
                                    if parameter.default is not None else {}
                                ),
                            }
                            for parameter in tool.definition.parameters
                        },
                        "required": [
                            parameter.name
                            for parameter in tool.definition.parameters
                            if parameter.required
                        ],
                    },
                }
            )
        return provider_tools

    async def _execute_tools(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """Execute tool calls through the safety pipeline: hook → permission → veto → execute"""
        results: list[ToolResult] = []

        for call in tool_calls:
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

            # 2. Permission check
            if self.permission_manager:
                perm = self.permission_manager.evaluate(
                    call.name, "execute",
                    context={"arguments": call.arguments},
                    hook_decision=hook_decision,
                )
                if not perm.allowed:
                    result = ToolResult(
                        tool_call_id=call.id,
                        content=f"Permission denied: {perm.reason}",
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

            # 3. Veto check
            if self.veto_authority:
                vetoed, reason = self.veto_authority.check_tool(call.name, call.arguments)
                if vetoed:
                    result = ToolResult(
                        tool_call_id=call.id,
                        content=f"Vetoed: {reason}",
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

            # 4. Execute via tool executor (includes governance)
            result = await self.tool_executor.execute(call)
            results.append(result)
            self.emit(
                "tool_result",
                tool_name=call.name,
                result=result.content,
                success=not result.is_error,
                tool_call_id=call.id,
            )

        return results

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

    def _on_heartbeat_event(self, event: dict, urgency: str):
        """Handle heartbeat events — project into dashboard."""
        logger.info(f"Heartbeat event ({urgency}): {event}")
        self.context_manager.dashboard.ingest_heartbeat_event(event, urgency)

    def _message_text(self, content: str | list[Any]) -> str:
        """Normalize message content for terminal outputs."""
        if isinstance(content, str):
            return content
        return str(content)
