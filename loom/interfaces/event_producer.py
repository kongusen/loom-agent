"""
Event Producer Protocol for Loom 2.0

Defines the interface that all event-producing components must implement.
This enables type-safe composition of streaming agents.
"""

from typing import Protocol, AsyncGenerator, runtime_checkable
from loom.core.events import AgentEvent


@runtime_checkable
class EventProducer(Protocol):
    """
    Protocol for components that produce AgentEvent streams.

    Any component that participates in the agent execution pipeline
    and produces events should implement this protocol.

    Example:
        ```python
        class MyCustomExecutor(EventProducer):
            async def produce_events(self) -> AsyncGenerator[AgentEvent, None]:
                yield AgentEvent.phase_start("custom_phase")
                # ... do work
                yield AgentEvent.phase_end("custom_phase")
        ```
    """

    async def produce_events(self) -> AsyncGenerator[AgentEvent, None]:
        """
        Produce a stream of agent events.

        Yields:
            AgentEvent: Events representing execution progress

        Example:
            ```python
            async for event in producer.produce_events():
                if event.type == AgentEventType.LLM_DELTA:
                    print(event.content, end="")
            ```
        """
        ...


@runtime_checkable
class ToolExecutor(Protocol):
    """
    Protocol for tool execution components that produce events.

    This is a specialized EventProducer for tool execution.
    """

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute a tool and yield progress events.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Yields:
            AgentEvent: Tool execution events (TOOL_EXECUTION_START,
                        TOOL_PROGRESS, TOOL_RESULT, or TOOL_ERROR)
        """
        ...


@runtime_checkable
class LLMEventProducer(Protocol):
    """
    Protocol for LLM components that produce streaming events.

    This enables streaming LLM calls with real-time token generation.
    """

    async def stream_with_events(
        self,
        messages: list,
        tools: list = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Stream LLM generation as AgentEvents.

        Args:
            messages: Conversation messages
            tools: Optional tool definitions

        Yields:
            AgentEvent: LLM events (LLM_START, LLM_DELTA, LLM_COMPLETE,
                        LLM_TOOL_CALLS)
        """
        ...


# ===== Helper Functions =====

async def merge_event_streams(
    *producers: EventProducer
) -> AsyncGenerator[AgentEvent, None]:
    """
    Merge multiple event streams into a single stream.

    This is useful for parallel execution where multiple components
    produce events concurrently.

    Args:
        *producers: EventProducer instances to merge

    Yields:
        AgentEvent: Events from all producers in arrival order

    Example:
        ```python
        async for event in merge_event_streams(executor1, executor2):
            print(event)
        ```
    """
    import asyncio

    # Create tasks for all producers
    tasks = [
        asyncio.create_task(_consume_producer(producer))
        for producer in producers
    ]

    # Yield events as they arrive
    pending = set(tasks)
    while pending:
        done, pending = await asyncio.wait(
            pending,
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in done:
            events = task.result()
            for event in events:
                yield event


async def _consume_producer(producer: EventProducer) -> list:
    """Helper to consume a producer into a list"""
    events = []
    async for event in producer.produce_events():
        events.append(event)
    return events


async def collect_events(
    producer: EventProducer
) -> list:
    """
    Collect all events from a producer into a list.

    Args:
        producer: EventProducer to consume

    Returns:
        List of all events produced

    Example:
        ```python
        events = await collect_events(my_executor)
        print(f"Generated {len(events)} events")
        ```
    """
    return await _consume_producer(producer)
