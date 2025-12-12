from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

from loom.core.agent_executor import AgentExecutor
from loom.core.types import Message
from loom.core.events import AgentEvent, AgentEventType
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
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
    """
    High-level Agent component for AI task execution.

    **Unified Entry Points**:
    - :meth:`execute`: Core streaming method (returns AsyncGenerator[AgentEvent])
    - :meth:`run`: Convenience method (returns final string result)

    All execution flows through the recursive tt() control loop, providing:
    - Event sourcing for crash recovery
    - Lifecycle hooks for HITL and custom logic
    - Context management with compression
    - Tool calling with intelligent orchestration

    **Execution Architecture**::

        User Input → Agent.execute() → AgentExecutor.tt()
                                            ↓
                                        Recursive Loop:
                                        1. Context Assembly
                                        2. LLM Call (streaming)
                                        3. Tool Execution
                                        4. tt() recurses if needed
                                            ↓
                                        Final Result

    **Basic Usage**::

        # Non-streaming (simple)
        agent = Agent(llm=llm, tools=tools)
        result = await agent.run("Analyze this code")
        print(result)

        # Streaming (real-time events)
        async for event in agent.execute("Analyze this code"):
            if event.type == AgentEventType.LLM_DELTA:
                print(event.content, end="", flush=True)
            elif event.type == AgentEventType.TOOL_RESULT:
                print(f"\\nTool: {event.tool_result.tool_name}")

    **Production Setup**::

        from loom.core.lifecycle_hooks import HITLHook
        from loom.core import EventJournal
        from pathlib import Path

        agent = Agent(
            llm=llm,
            tools=tools,
            hooks=[HITLHook(dangerous_tools=["bash", "write_file"])],
            event_journal=EventJournal(Path("./logs")),
            thread_id="user-123",
            max_iterations=50
        )

        # Execute with crash recovery support
        async for event in agent.execute("Complex task"):
            yield event

        # Later: Resume from crash
        async for event in agent.executor.resume(thread_id="user-123"):
            yield event

    Args:
        llm: LLM instance for generation
        tools: List of tool instances
        memory: Optional memory store for conversation history
        compressor: Optional context compressor (auto-created if None)
        max_iterations: Maximum recursion depth (default: 50)
        max_context_tokens: Maximum context size (default: 16000)
        hooks: Lifecycle hooks for HITL, logging, etc.
        event_journal: Event journal for crash recovery
        thread_id: Unique session identifier
        system_instructions: System prompt for the agent
        callbacks: Callback handlers for events
        steering_control: Control system for dynamic behavior
        metrics: Metrics collector
        enable_steering: Enable steering control (default: True)
        context_debugger: Context debugger for troubleshooting

    See Also:
        - :class:`loom.core.agent_executor.AgentExecutor`: Core execution engine
        - :class:`loom.core.events.AgentEvent`: Event types
        - :class:`loom.core.lifecycle_hooks.LifecycleHook`: Hook system
    """

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
        enable_steering: bool = True,  # v0.1.1: Enable steering by default
        # 🆕 New Architecture Parameters (loom-agent 2.0)
        hooks: Optional[List[LifecycleHook]] = None,
        event_journal: Optional[EventJournal] = None,
        context_debugger: Optional[ContextDebugger] = None,
        thread_id: Optional[str] = None,
    ) -> None:
        # Validate LLM implements Protocol
        from loom.interfaces.llm import validate_llm
        validate_llm(llm, name="llm")

        # v0.1.1: Auto-instantiate CompressionManager (always enabled)
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
        cancel_token: Optional[asyncio.Event] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        Execute agent and return final response (convenience method).

        This is a convenience wrapper around :meth:`execute` that collects all
        streaming events and returns only the final response text. Use this when
        you don't need real-time event streaming.

        **When to use**:
        - Simple queries that don't need progress updates
        - Scripts where streaming output isn't necessary
        - Testing and prototyping

        **When NOT to use**:
        - Production UIs that need real-time feedback
        - Long-running tasks where users need progress updates
        - When you need access to tool results or intermediate events

        Args:
            input: User input text
            cancel_token: Optional cancellation event for abort support
            correlation_id: Optional correlation ID for distributed tracing

        Returns:
            str: Final response text from the agent

        Example::

            agent = Agent(llm=llm, tools=tools)
            result = await agent.run("What's the weather in Tokyo?")
            print(result)  # "The weather in Tokyo is..."

        Note:
            This method internally streams all events but only returns the final
            result. For streaming output, use :meth:`execute` instead.
        """
        final_content = ""

        async for event in self.execute(input):
            # Accumulate LLM deltas
            if event.type == AgentEventType.LLM_DELTA:
                # 类型安全的内容累积
                if event.content:
                    if isinstance(event.content, str):
                        final_content += event.content
                    else:
                        # 如果不是字符串，转换为字符串
                        final_content += str(event.content)

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
        Execute agent with real-time event streaming (CORE METHOD).

        This is the **primary execution method** for loom-agent. It streams
        AgentEvent instances in real-time, providing complete visibility into
        the agent's execution. All execution flows through the recursive tt()
        control loop.

        **Event Stream**:
        The method yields events as execution progresses:

        - ``ITERATION_START`` - New recursion iteration begins
        - ``PHASE_START/END`` - Execution phases (context assembly, LLM call, etc.)
        - ``LLM_DELTA`` - Streaming text chunks from LLM
        - ``LLM_COMPLETE`` - LLM generation finished
        - ``TOOL_EXECUTION_START`` - Tool execution begins
        - ``TOOL_RESULT`` - Tool execution completed
        - ``RECURSION`` - Recursive call initiated
        - ``AGENT_FINISH`` - Task completed successfully
        - ``ERROR`` - Error occurred

        **Use Cases**:

        1. **Real-time UI Updates**::

            async for event in agent.execute(input):
                if event.type == AgentEventType.LLM_DELTA:
                    ui.append_text(event.content)
                elif event.type == AgentEventType.TOOL_RESULT:
                    ui.show_tool_result(event.tool_result)

        2. **Progress Tracking**::

            async for event in agent.execute(input):
                if event.type == AgentEventType.ITERATION_START:
                    print(f"Iteration {event.iteration}/{max_iterations}")
                elif event.type == AgentEventType.TOOL_EXECUTION_START:
                    print(f"Running tool: {event.metadata['tool_name']}")

        3. **Event Collection for Analysis**::

            from loom.core.events import EventCollector

            collector = EventCollector()
            async for event in agent.execute(input):
                collector.add(event)

            # Analyze after completion
            print(collector.get_llm_content())
            print(collector.get_tool_results())

        4. **Crash Recovery** (with EventJournal)::

            # All events are auto-recorded to journal
            agent = Agent(
                llm=llm,
                event_journal=EventJournal(Path("./logs")),
                thread_id="user-123"
            )

            async for event in agent.execute(input):
                yield event  # Events recorded automatically

            # After crash - resume from checkpoint
            async for event in agent.executor.resume(thread_id="user-123"):
                yield event

        Args:
            input: User input text
            cancel_token: Optional event to signal cancellation. Set this event
                to abort execution gracefully.
            correlation_id: Optional correlation ID for distributed tracing
                and log correlation.
            working_dir: Optional working directory for tool execution context.

        Yields:
            AgentEvent: Real-time events representing execution progress.
                See :class:`loom.core.events.AgentEvent` for event types.

        Raises:
            Exception: If an unhandled error occurs (also emitted as ERROR event)

        Note:
            - This method uses the recursive tt() control loop
            - All LLM calls use streaming (even for tools)
            - Events are recorded to EventJournal if configured
            - Lifecycle hooks are triggered at appropriate points
            - For simple use cases, use :meth:`run` instead

        See Also:
            - :meth:`run`: Convenience method that returns final result only
            - :class:`loom.core.events.AgentEvent`: Event type documentation
            - :class:`loom.core.agent_executor.AgentExecutor`: Core execution engine
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

    # LangChain 风格的别名，便于迁移/调用
    async def ainvoke(
        self,
        input: str,
        cancel_token: Optional[asyncio.Event] = None,
        correlation_id: Optional[str] = None,
    ) -> str:
        """
        LangChain-style alias for run() method.

        Args:
            input: User input text
            cancel_token: Optional cancellation event
            correlation_id: Optional correlation ID

        Returns:
            str: Final response text
        """
        return await self.run(input, cancel_token=cancel_token, correlation_id=correlation_id)

    def get_metrics(self) -> Dict:
        """返回当前指标摘要。"""
        return self.executor.metrics.summary()

