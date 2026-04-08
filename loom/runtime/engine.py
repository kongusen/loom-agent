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
from dataclasses import dataclass
from typing import Any

from ..context import ContextManager
from ..memory import InMemoryStore, MemoryStore
from ..providers.base import CompletionParams, LLMProvider
from ..runtime.heartbeat import Heartbeat, HeartbeatConfig
from ..runtime.loop import AgentLoop, LoopConfig
from ..safety.veto import VetoAuthority
from ..tools.executor import ToolExecutor
from ..tools.governance import ToolGovernance
from ..tools.registry import ToolRegistry
from ..tools.schema import Tool
from ..types import LoopState, Message, ToolCall, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """Engine configuration"""
    max_iterations: int = 100
    max_tokens: int = 200000
    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    completion_max_tokens: int = 4096
    enable_heartbeat: bool = False
    enable_safety: bool = True
    enable_memory: bool = True


class AgentEngine:
    """Agent execution engine integrating all Loom components"""

    def __init__(
        self,
        provider: LLMProvider,
        config: EngineConfig | None = None,
        tools: list[Tool] | None = None,
    ):
        self.provider = provider
        self.config = config or EngineConfig()

        # Core components
        self.context_manager = ContextManager(max_tokens=self.config.max_tokens)
        self.memory_store: MemoryStore = InMemoryStore()
        self.tool_registry = ToolRegistry()
        self.tool_governance = ToolGovernance()
        self.tool_executor = ToolExecutor(self.tool_registry, self.tool_governance)
        self.veto_authority = VetoAuthority() if self.config.enable_safety else None
        self.heartbeat: Heartbeat | None = None

        # Register tools
        if tools:
            for tool in tools:
                self.tool_registry.register(tool)

        # Initialize heartbeat if enabled
        if self.config.enable_heartbeat:
            hb_config = HeartbeatConfig(T_hb=5.0)
            self.heartbeat = Heartbeat(hb_config)

    async def execute(
        self,
        goal: str,
        instructions: str = "",
        context: dict | None = None,
        session_id: str | None = None,
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
        # Initialize context
        self.context_manager.current_goal = goal
        self._initialize_context(goal, instructions, context)

        # Load session memory if available
        if session_id and self.config.enable_memory:
            self._load_session_memory(session_id)

        # Start heartbeat if enabled
        if self.heartbeat:
            self.heartbeat.start(self._on_heartbeat_event)

        try:
            # Execute L* loop
            result = await self._run_loop(goal)

            # Save session memory
            if session_id and self.config.enable_memory:
                self._save_session_memory(session_id)

            return result

        finally:
            # Stop heartbeat
            if self.heartbeat:
                self.heartbeat.stop()

    async def _run_loop(self, goal: str) -> dict[str, Any]:
        """Run the L* execution loop"""
        loop = AgentLoop(LoopConfig(
            max_iterations=self.config.max_iterations,
            rho_threshold=1.0,
        ))

        iteration = 0
        messages: list[Message] = self._build_messages(goal)
        events: list[dict] = []

        while iteration < self.config.max_iterations:
            iteration += 1
            logger.debug(f"Loop iteration {iteration}, state: {loop.state}")

            # Check context pressure and compress if needed
            if self.context_manager.should_renew():
                logger.info("Context pressure ρ=1.0, renewing context")
                self.context_manager.renew()
                events.append({"type": "context.renewed", "iteration": iteration})

            elif strategy := self.context_manager.should_compress():
                logger.info(f"Compressing context with strategy: {strategy}")
                self.context_manager.compress(strategy)
                events.append({"type": "context.compressed", "strategy": strategy})

            # Execute loop state
            if loop.state == LoopState.REASON:
                # Reason: continue the current transcript and get the next model step
                response = await self._call_llm(messages)

                # Parse response for tool calls
                tool_calls = self._parse_tool_calls(response)

                if tool_calls:
                    content = str(response.get("content", "")).strip()
                    loop.state = LoopState.ACT
                    messages.append(Message(
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
                    # For plain assistant responses, one no-tool answer is the terminal result.
                    # Requiring special completion phrases here causes normal provider outputs
                    # to spin until max_iterations even though the model already answered.
                    output = str(response.get("content", "")).strip()
                    messages.append(Message(role="assistant", content=output))
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

                # Add tool results to messages
                for result in tool_results:
                    messages.append(Message(
                        role="tool",
                        content=result.content,
                        tool_call_id=result.tool_call_id,
                        name=tool_names.get(result.tool_call_id),
                    ))

                events.append({
                    "type": "tools.executed",
                    "count": len(tool_results),
                    "iteration": iteration,
                })

                loop.state = LoopState.OBSERVE

            elif loop.state == LoopState.OBSERVE:
                # Observe: Update context with tool results
                # Context is already updated via messages
                loop.state = LoopState.DELTA

            elif loop.state == LoopState.DELTA:
                # Δ: Decide next action
                if messages and messages[-1].role == "tool":
                    if self.context_manager.rho >= 0.9:
                        self.context_manager.renew()
                        loop.state = LoopState.REASON
                    else:
                        loop.state = LoopState.REASON
                    continue

                decision = await self._decide_next_action(messages, goal)

                if decision == "goal_reached":
                    output = self._message_text(messages[-1].content) if messages else ""
                    return {
                        "status": "success",
                        "output": output,
                        "events": events,
                        "iterations": iteration,
                    }
                elif decision == "continue":
                    loop.state = LoopState.REASON
                elif decision == "renew":
                    self.context_manager.renew()
                    loop.state = LoopState.REASON
                else:
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

    async def _call_llm(self, messages: list[Message]) -> dict[str, Any]:
        """Call LLM provider"""
        # Convert Message objects to provider format
        provider_messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                    }
                    for tool_call in msg.tool_calls
                ],
                "tool_call_id": msg.tool_call_id,
                "name": msg.name,
            }
            for msg in messages
        ]

        params = CompletionParams(
            model=self.config.model,
            max_tokens=self.config.completion_max_tokens,
            temperature=self.config.temperature,
            tools=self._build_provider_tools(),
        )

        try:
            response = await self.provider.complete_response(provider_messages, params)
            return {
                "content": response.content,
                "tool_calls": response.tool_calls,
                "usage": response.usage,
            }
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"content": f"Error: {e}"}

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
        """Execute tool calls with safety checks"""
        results: list[ToolResult] = []

        for call in tool_calls:
            # Safety check via veto authority
            if self.veto_authority:
                vetoed, reason = self.veto_authority.check_tool(call.name, call.arguments)
                if vetoed:
                    results.append(ToolResult(
                        tool_call_id=call.id,
                        content=f"Vetoed: {reason}",
                        is_error=True,
                    ))
                    continue

            # Execute via tool executor (includes governance)
            result = await self.tool_executor.execute(call)
            results.append(result)

        return results

    async def _decide_next_action(self, messages: list[Message], _goal: str) -> str:
        """Decide next action based on current state"""
        # Simple heuristic: check if last message looks like completion
        if not messages:
            return "continue"

        last_content = messages[-1].content
        if isinstance(last_content, str) and any(
            phrase in last_content.lower()
            for phrase in ["completed", "finished", "done", "success"]
        ):
            return "goal_reached"

        # Check context pressure
        if self.context_manager.rho >= 0.9:
            return "renew"

        return "continue"

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

    def _on_heartbeat_event(self, event: dict, urgency: str):
        """Handle heartbeat events"""
        logger.info(f"Heartbeat event ({urgency}): {event}")
        # TODO: Inject into context or trigger interrupt based on urgency

    def _message_text(self, content: str | list[Any]) -> str:
        """Normalize message content for terminal outputs."""
        if isinstance(content, str):
            return content
        return str(content)
