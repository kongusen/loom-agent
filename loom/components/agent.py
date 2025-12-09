from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

from loom.core.agent_executor import AgentExecutor
from loom.core.types import StreamEvent, Message
from loom.core.events import AgentEvent, AgentEventType  # 🆕 Loom 2.0
from loom.core.turn_state import TurnState  # 🆕 Loom 2.0 tt mode
from loom.core.execution_context import ExecutionContext  # 🆕 Loom 2.0 tt mode
from loom.interfaces.llm import BaseLLM
from loom.interfaces.memory import BaseMemory
from loom.interfaces.tool import BaseTool
from loom.interfaces.compressor import BaseCompressor
from loom.callbacks.base import BaseCallback
from loom.callbacks.metrics import MetricsCollector
from loom.core.steering_control import SteeringControl
# 🆕 New Architecture Imports
from loom.core.lifecycle_hooks import LifecycleHook
from loom.core.event_journal import EventJournal
from loom.core.context_debugger import ContextDebugger


class Agent:
    """高层 Agent 组件：对外暴露 run/stream，内部委托 AgentExecutor。"""

    def __init__(
        self,
        llm: BaseLLM,
        tools: List[BaseTool] | None = None,
        memory: Optional[BaseMemory] = None,
        compressor: Optional[BaseCompressor] = None,
        max_iterations: int = 50,
        max_context_tokens: int = 16000,
        permission_policy: Optional[Dict[str, str]] = None,
        ask_handler=None,
        safe_mode: bool = False,
        permission_store=None,
        # Advanced options
        context_retriever=None,
        system_instructions: Optional[str] = None,
        callbacks: Optional[List[BaseCallback]] = None,
        steering_control: Optional[SteeringControl] = None,
        metrics: Optional[MetricsCollector] = None,
        enable_steering: bool = True,  # v4.0.0: Enable steering by default
        # 🆕 New Architecture Parameters (loom-agent 2.0)
        hooks: Optional[List[LifecycleHook]] = None,
        event_journal: Optional[EventJournal] = None,
        context_debugger: Optional[ContextDebugger] = None,
        thread_id: Optional[str] = None,
    ) -> None:
        # v4.0.0: Auto-instantiate CompressionManager (always enabled)
        if compressor is None:
            from loom.core.compression_manager import CompressionManager
            compressor = CompressionManager(
                llm=llm,
                max_retries=3,
                compression_threshold=0.92,
                target_reduction=0.75,
                sliding_window_size=20,
            )

        tools_map = {t.name: t for t in (tools or [])}
        self.executor = AgentExecutor(
            llm=llm,
            tools=tools_map,
            memory=memory,
            compressor=compressor,
            context_retriever=context_retriever,
            steering_control=steering_control,
            max_iterations=max_iterations,
            max_context_tokens=max_context_tokens,
            metrics=metrics,
            permission_manager=None,
            system_instructions=system_instructions,
            callbacks=callbacks,
            enable_steering=enable_steering,
            # 🆕 Pass new architecture parameters
            hooks=hooks,
            event_journal=event_journal,
            context_debugger=context_debugger,
            thread_id=thread_id,
        )

        # 始终构造 PermissionManager（以便支持 safe_mode/持久化）；保持默认语义
        from loom.core.permissions import PermissionManager

        pm = PermissionManager(
            policy=permission_policy or {},
            default="allow",  # 保持默认放行语义
            ask_handler=ask_handler,
            safe_mode=safe_mode,
            permission_store=permission_store,
        )
        self.executor.permission_manager = pm
        self.executor.tool_pipeline.permission_manager = pm

    async def run(
        self,
        input: str,
        cancel_token: Optional[asyncio.Event] = None,  # 🆕 US1
        correlation_id: Optional[str] = None,  # 🆕 US1
    ) -> str:
        """
        Execute agent and return final response (backward compatible).

        This method wraps the new execute() streaming API and extracts
        the final response for backward compatibility.

        Args:
            input: User input
            cancel_token: Optional cancellation event
            correlation_id: Optional correlation ID for tracing

        Returns:
            Final response text
        """
        final_content = ""

        async for event in self.execute(input):
            # Accumulate LLM deltas
            if event.type == AgentEventType.LLM_DELTA:
                final_content += event.content or ""

            # Return on finish
            elif event.type == AgentEventType.AGENT_FINISH:
                return event.content or final_content

            # Raise on error
            elif event.type == AgentEventType.ERROR:
                if event.error:
                    raise event.error

        return final_content

    async def execute(
        self,
        input: str,
        cancel_token: Optional[asyncio.Event] = None,
        correlation_id: Optional[str] = None,
        working_dir: Optional[Path] = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute agent with streaming events using tt recursive mode (Loom 2.0).

        This is the new unified streaming interface that produces AgentEvent
        instances for all execution phases. It uses tt (tail-recursive) control
        loop as the ONLY core execution method.

        Args:
            input: User input
            cancel_token: Optional cancellation event
            correlation_id: Optional correlation ID for tracing
            working_dir: Optional working directory

        Yields:
            AgentEvent: Events representing execution progress

        Example:
            ```python
            async for event in agent.execute("Your prompt"):
                if event.type == AgentEventType.LLM_DELTA:
                    print(event.content, end="", flush=True)
                elif event.type == AgentEventType.TOOL_PROGRESS:
                    print(f"\\n[Tool] {event.metadata['status']}")
                elif event.type == AgentEventType.AGENT_FINISH:
                    print(f"\\n✓ {event.content}")
            ```
        """
        # Initialize immutable turn state
        turn_state = TurnState.initial(max_iterations=self.executor.max_iterations)

        # Create execution context
        context = ExecutionContext.create(
            working_dir=working_dir,
            correlation_id=correlation_id,
            cancel_token=cancel_token,
        )

        # Create initial message
        messages = [Message(role="user", content=input)]

        # Delegate to executor's tt recursive control loop
        async for event in self.executor.tt(messages, turn_state, context):
            yield event

    async def stream(self, input: str) -> AsyncGenerator[StreamEvent, None]:
        """
        Legacy streaming API (backward compatible).

        NOTE: This uses the old StreamEvent type. For new code, use execute()
        which returns AgentEvent instances.

        This method now converts AgentEvent to StreamEvent for backward compatibility.
        """
        # Use tt mode under the hood
        async for agent_event in self.execute(input):
            # Convert AgentEvent to legacy StreamEvent
            if agent_event.type == AgentEventType.LLM_DELTA:
                yield StreamEvent(
                    type="llm_delta",
                    content=agent_event.content or "",
                )
            elif agent_event.type == AgentEventType.AGENT_FINISH:
                yield StreamEvent(
                    type="agent_finish",
                    content=agent_event.content or "",
                )
            elif agent_event.type == AgentEventType.TOOL_RESULT:
                yield StreamEvent(
                    type="tool_result",
                    content=agent_event.tool_result.content if agent_event.tool_result else "",
                )
            elif agent_event.type == AgentEventType.ERROR:
                yield StreamEvent(
                    type="error",
                    content=str(agent_event.error) if agent_event.error else "Unknown error",
                )

    # LangChain 风格的别名，便于迁移/调用
    async def ainvoke(
        self,
        input: str,
        cancel_token: Optional[asyncio.Event] = None,  # 🆕 US1
        correlation_id: Optional[str] = None,  # 🆕 US1
    ) -> str:
        return await self.run(input, cancel_token=cancel_token, correlation_id=correlation_id)

    async def astream(self, input: str) -> AsyncGenerator[StreamEvent, None]:
        async for ev in self.stream(input):
            yield ev

    def get_metrics(self) -> Dict:
        """返回当前指标摘要。"""
        return self.executor.metrics.summary()
