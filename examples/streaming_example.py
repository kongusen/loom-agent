"""
Loom 2.0 Streaming API Example

Demonstrates the new execute() streaming interface that produces AgentEvent
instances for real-time progress tracking.
"""

import asyncio
from loom import Agent
from loom.core.events import AgentEventType, EventCollector


async def example_1_basic_streaming():
    """Example 1: Basic streaming with real-time output."""
    print("=" * 60)
    print("Example 1: Basic Streaming")
    print("=" * 60)

    # Note: You'll need to provide your own LLM and tools
    # from loom.llm.openai import OpenAILLM
    # llm = OpenAILLM(api_key="your-key")
    # agent = Agent(llm=llm, tools=[])

    # For demonstration, using pseudo-code:
    print("""
    # Create agent
    llm = OpenAILLM(api_key="your-key")
    agent = Agent(llm=llm, tools=[])

    # Stream execution with real-time output
    async for event in agent.execute("What is Python?"):
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)
        elif event.type == AgentEventType.AGENT_FINISH:
            print("\\n✓ Complete!")
    """)


async def example_2_tool_execution_tracking():
    """Example 2: Track tool execution progress."""
    print("=" * 60)
    print("Example 2: Tool Execution Tracking")
    print("=" * 60)

    print("""
    # Create agent with tools
    from loom.builtin.tools import Calculator, WebSearch

    llm = OpenAILLM(api_key="your-key")
    agent = Agent(
        llm=llm,
        tools=[Calculator(), WebSearch()]
    )

    # Track execution progress
    async for event in agent.execute("Search for Python and calculate 2+2"):
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

        elif event.type == AgentEventType.TOOL_EXECUTION_START:
            print(f"\\n[Tool] Calling: {event.tool_call.name}")
            print(f"[Tool] Arguments: {event.tool_call.arguments}")

        elif event.type == AgentEventType.TOOL_RESULT:
            print(f"[Tool] Result: {event.tool_result.content[:100]}...")

        elif event.type == AgentEventType.AGENT_FINISH:
            print("\\n✓ Complete!")
    """)


async def example_3_event_collection_and_analysis():
    """Example 3: Collect events for analysis."""
    print("=" * 60)
    print("Example 3: Event Collection & Analysis")
    print("=" * 60)

    print("""
    # Collect all events
    collector = EventCollector()

    async for event in agent.execute("Explain async programming"):
        collector.add(event)

        # Still process in real-time
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

    # Analyze after completion
    print(f"\\nTotal events: {len(collector.events)}")
    print(f"LLM content: {collector.get_llm_content()}")
    print(f"Tool results: {len(collector.get_tool_results())}")
    print(f"Errors: {len(collector.get_errors())}")

    # Filter specific event types
    llm_events = collector.filter(AgentEventType.LLM_DELTA)
    print(f"LLM delta events: {len(llm_events)}")
    """)


async def example_4_backward_compatibility():
    """Example 4: Backward compatible run() method."""
    print("=" * 60)
    print("Example 4: Backward Compatibility")
    print("=" * 60)

    print("""
    # Old API still works (non-streaming)
    result = await agent.run("What is Python?")
    print(result)

    # This is equivalent to:
    final_content = ""
    async for event in agent.execute("What is Python?"):
        if event.type == AgentEventType.LLM_DELTA:
            final_content += event.content
        elif event.type == AgentEventType.AGENT_FINISH:
            print(event.content or final_content)
    """)


async def example_5_error_handling():
    """Example 5: Handle errors in streaming."""
    print("=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)

    print("""
    try:
        async for event in agent.execute("Invalid request"):
            if event.type == AgentEventType.ERROR:
                print(f"Error occurred: {event.error}")
                # Optionally continue or break

            elif event.type == AgentEventType.TOOL_ERROR:
                print(f"Tool error: {event.tool_result.content}")
                # Tool errors are captured but execution continues

            elif event.type == AgentEventType.LLM_DELTA:
                print(event.content, end="", flush=True)

    except Exception as e:
        print(f"Fatal error: {e}")
    """)


async def example_6_iteration_tracking():
    """Example 6: Track multi-turn iterations."""
    print("=" * 60)
    print("Example 6: Iteration Tracking")
    print("=" * 60)

    print("""
    async for event in agent.execute("Research Python best practices"):
        if event.type == AgentEventType.ITERATION_START:
            print(f"\\n--- Iteration {event.iteration} (Turn ID: {event.turn_id}) ---")

        elif event.type == AgentEventType.LLM_TOOL_CALLS:
            print(f"[Agent] Planning to use {event.metadata['tool_count']} tools")

        elif event.type == AgentEventType.MAX_ITERATIONS_REACHED:
            print("[Warning] Max iterations reached!")

        elif event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)
    """)


async def example_7_rag_integration():
    """Example 7: Track RAG retrieval."""
    print("=" * 60)
    print("Example 7: RAG Integration")
    print("=" * 60)

    print("""
    # Agent with RAG enabled
    from loom.rag import VectorStore

    retriever = VectorStore(...)
    agent = Agent(llm=llm, context_retriever=retriever)

    async for event in agent.execute("Query requiring context"):
        if event.type == AgentEventType.RETRIEVAL_START:
            print("[RAG] Starting document retrieval...")

        elif event.type == AgentEventType.RETRIEVAL_PROGRESS:
            doc_title = event.metadata.get('doc_title', 'Unknown')
            score = event.metadata.get('relevance_score', 0.0)
            print(f"[RAG] Found: {doc_title} (score: {score:.2f})")

        elif event.type == AgentEventType.RETRIEVAL_COMPLETE:
            doc_count = event.metadata.get('doc_count', 0)
            print(f"[RAG] Retrieved {doc_count} documents")

        elif event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)
    """)


async def example_8_progress_ui():
    """Example 8: Building a progress UI."""
    print("=" * 60)
    print("Example 8: Progress UI Pattern")
    print("=" * 60)

    print("""
    # Example progress UI tracking
    class ProgressTracker:
        def __init__(self):
            self.current_phase = None
            self.tools_used = []
            self.llm_tokens = 0

        async def track(self, event):
            if event.type == AgentEventType.PHASE_START:
                self.current_phase = event.phase
                print(f"[Phase] Starting: {event.phase}")

            elif event.type == AgentEventType.PHASE_END:
                tokens = event.metadata.get('tokens_used', 0)
                self.llm_tokens += tokens
                print(f"[Phase] Completed: {event.phase} ({tokens} tokens)")

            elif event.type == AgentEventType.TOOL_EXECUTION_START:
                self.tools_used.append(event.tool_call.name)
                print(f"[Progress] Tool {len(self.tools_used)}: {event.tool_call.name}")

            elif event.type == AgentEventType.LLM_DELTA:
                # Update UI with streaming text
                pass

            elif event.type == AgentEventType.AGENT_FINISH:
                print(f"\\n[Summary] Tokens: {self.llm_tokens}, Tools: {len(self.tools_used)}")

    # Use it
    tracker = ProgressTracker()
    async for event in agent.execute("Complex query"):
        await tracker.track(event)
    """)


async def main():
    """Run all examples."""
    print("\\n" + "=" * 60)
    print("Loom 2.0 Streaming API Examples")
    print("=" * 60 + "\\n")

    await example_1_basic_streaming()
    await example_2_tool_execution_tracking()
    await example_3_event_collection_and_analysis()
    await example_4_backward_compatibility()
    await example_5_error_handling()
    await example_6_iteration_tracking()
    await example_7_rag_integration()
    await example_8_progress_ui()

    print("\\n" + "=" * 60)
    print("For more information, see:")
    print("- docs/agent_events_guide.md - Complete AgentEvent documentation")
    print("- tests/unit/test_streaming_api.py - Test examples")
    print("=" * 60 + "\\n")


if __name__ == "__main__":
    asyncio.run(main())
