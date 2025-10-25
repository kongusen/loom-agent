"""
Agent Events Demo - Loom 2.0

This demo shows how to use the new AgentEvent system.
Run this to see the event system in action.

Note: This is a demonstration using mock components. In the full implementation,
these events will be produced by the actual Agent executor.
"""

import asyncio
from loom.core.events import (
    AgentEvent,
    AgentEventType,
    ToolCall,
    ToolResult,
    EventCollector
)


# ===== Demo 1: Basic Event Streaming =====

async def demo_basic_streaming():
    """Demo 1: Basic event streaming pattern"""
    print("\n" + "="*60)
    print("DEMO 1: Basic Event Streaming")
    print("="*60 + "\n")

    async def mock_agent_execution():
        """Mock agent that produces events"""
        # Phase 1: Context assembly
        yield AgentEvent.phase_start("context_assembly", tokens_budget=16000)
        await asyncio.sleep(0.1)
        yield AgentEvent.phase_end("context_assembly", tokens_used=1500)

        # Phase 2: LLM streaming
        yield AgentEvent(type=AgentEventType.LLM_START)

        for chunk in ["Based ", "on ", "the ", "code, ", "I ", "found ", "5 ", "TODO ", "items."]:
            yield AgentEvent.llm_delta(chunk)
            await asyncio.sleep(0.05)  # Simulate streaming delay

        yield AgentEvent(type=AgentEventType.LLM_COMPLETE)

        # Phase 3: Finish
        yield AgentEvent.agent_finish("Based on the code, I found 5 TODO items.")

    # Consume events
    print("Streaming LLM output:")
    print("-" * 40)

    async for event in mock_agent_execution():
        if event.type == AgentEventType.LLM_DELTA:
            # Print LLM tokens in real-time
            print(event.content, end="", flush=True)

        elif event.type == AgentEventType.PHASE_START:
            print(f"[Phase: {event.phase}]")

        elif event.type == AgentEventType.AGENT_FINISH:
            print("\n" + "-" * 40)
            print(f"✓ Completed: {event.content}")


# ===== Demo 2: Tool Execution Events =====

async def demo_tool_execution():
    """Demo 2: Tool execution with progress events"""
    print("\n" + "="*60)
    print("DEMO 2: Tool Execution Events")
    print("="*60 + "\n")

    async def mock_tool_execution():
        """Mock tool execution with progress"""
        # Start execution
        tool_call = ToolCall(
            id="call_123",
            name="GrepTool",
            arguments={"pattern": "TODO", "path": "."}
        )

        yield AgentEvent(
            type=AgentEventType.TOOL_EXECUTION_START,
            tool_call=tool_call
        )

        # Progress updates
        yield AgentEvent.tool_progress(
            "GrepTool",
            "Searching files...",
            files_searched=0
        )
        await asyncio.sleep(0.2)

        yield AgentEvent.tool_progress(
            "GrepTool",
            "Found matches in src/",
            files_searched=10
        )
        await asyncio.sleep(0.2)

        yield AgentEvent.tool_progress(
            "GrepTool",
            "Found matches in tests/",
            files_searched=25
        )
        await asyncio.sleep(0.2)

        # Final result
        result = ToolResult(
            tool_call_id="call_123",
            tool_name="GrepTool",
            content="Found 5 TODO items:\n- src/main.py:45\n- src/utils.py:102\n...",
            is_error=False,
            execution_time_ms=587.3
        )

        yield AgentEvent.tool_result(result)

    # Consume events with progress display
    async for event in mock_tool_execution():
        if event.type == AgentEventType.TOOL_EXECUTION_START:
            tool_name = event.tool_call.name
            print(f"▶ Running {tool_name}...")

        elif event.type == AgentEventType.TOOL_PROGRESS:
            status = event.metadata['status']
            files = event.metadata.get('files_searched', 0)
            print(f"  {status} ({files} files)")

        elif event.type == AgentEventType.TOOL_RESULT:
            result = event.tool_result
            print(f"✓ Completed in {result.execution_time_ms:.1f}ms")
            print(f"\nResult:\n{result.content}")


# ===== Demo 3: Event Collection and Analysis =====

async def demo_event_collection():
    """Demo 3: Collecting and analyzing events"""
    print("\n" + "="*60)
    print("DEMO 3: Event Collection and Analysis")
    print("="*60 + "\n")

    async def mock_full_agent_run():
        """Mock complete agent execution"""
        # RAG retrieval
        yield AgentEvent(type=AgentEventType.RETRIEVAL_START)
        yield AgentEvent(
            type=AgentEventType.RETRIEVAL_PROGRESS,
            metadata={"doc_title": "README.md", "relevance_score": 0.95}
        )
        yield AgentEvent(
            type=AgentEventType.RETRIEVAL_PROGRESS,
            metadata={"doc_title": "CONTRIBUTING.md", "relevance_score": 0.82}
        )
        yield AgentEvent(type=AgentEventType.RETRIEVAL_COMPLETE)

        # LLM generation
        yield AgentEvent(type=AgentEventType.LLM_START)
        for token in ["The ", "project ", "uses ", "Python ", "3.11+"]:
            yield AgentEvent.llm_delta(token)
        yield AgentEvent(type=AgentEventType.LLM_COMPLETE)

        # Tool execution
        tool_result = ToolResult(
            tool_call_id="call_1",
            tool_name="ReadTool",
            content="File contents here...",
            execution_time_ms=45.2
        )
        yield AgentEvent.tool_result(tool_result)

        # Finish
        yield AgentEvent.agent_finish("The project uses Python 3.11+")

    # Collect all events
    collector = EventCollector()

    print("Collecting events...")
    async for event in mock_full_agent_run():
        collector.add(event)

    # Analyze
    print("\n" + "-" * 40)
    print("Event Analysis:")
    print("-" * 40)
    print(f"Total events: {len(collector.events)}")

    # Event breakdown
    llm_events = collector.filter(AgentEventType.LLM_DELTA)
    tool_events = [e for e in collector.events if e.is_tool_event()]
    rag_events = [
        e for e in collector.events
        if "retrieval" in e.type.value
    ]

    print(f"LLM deltas: {len(llm_events)}")
    print(f"Tool events: {len(tool_events)}")
    print(f"RAG events: {len(rag_events)}")

    # Reconstructed output
    print("\n" + "-" * 40)
    print("Reconstructed LLM Output:")
    print("-" * 40)
    print(collector.get_llm_content())

    # Tool results
    print("\n" + "-" * 40)
    print("Tool Results:")
    print("-" * 40)
    for result in collector.get_tool_results():
        print(f"- {result.tool_name}: {result.execution_time_ms:.1f}ms")

    # Final response
    print("\n" + "-" * 40)
    print("Final Response:")
    print("-" * 40)
    print(collector.get_final_response())


# ===== Demo 4: Error Handling =====

async def demo_error_handling():
    """Demo 4: Error events and recovery"""
    print("\n" + "="*60)
    print("DEMO 4: Error Handling")
    print("="*60 + "\n")

    async def mock_agent_with_error():
        """Mock agent that encounters an error and recovers"""
        # Start normally
        yield AgentEvent.phase_start("tool_execution")

        # Error occurs
        error = ValueError("Invalid file path")
        yield AgentEvent.error(error, recoverable=True)

        # Attempt recovery
        yield AgentEvent(
            type=AgentEventType.RECOVERY_ATTEMPT,
            metadata={"strategy": "retry_with_fallback"}
        )
        await asyncio.sleep(0.3)

        # Recovery succeeds
        yield AgentEvent(
            type=AgentEventType.RECOVERY_SUCCESS,
            metadata={"attempts": 1}
        )

        # Continue execution
        yield AgentEvent.agent_finish("Task completed after recovery")

    # Handle errors
    async for event in mock_agent_with_error():
        if event.type == AgentEventType.ERROR:
            error = event.error
            recoverable = event.metadata.get('recoverable', False)
            print(f"✗ Error: {type(error).__name__}: {str(error)}")
            if recoverable:
                print("  (Recoverable)")

        elif event.type == AgentEventType.RECOVERY_ATTEMPT:
            strategy = event.metadata['strategy']
            print(f"⟳ Attempting recovery: {strategy}")

        elif event.type == AgentEventType.RECOVERY_SUCCESS:
            attempts = event.metadata['attempts']
            print(f"✓ Recovered after {attempts} attempt(s)")

        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n✓ {event.content}")


# ===== Main =====

async def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("Loom 2.0 AgentEvent System Demo")
    print("="*60)

    await demo_basic_streaming()
    await demo_tool_execution()
    await demo_event_collection()
    await demo_error_handling()

    print("\n" + "="*60)
    print("All demos completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
