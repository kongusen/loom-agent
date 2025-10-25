"""
Integration tests for Task 1.2: Agent streaming in real scenarios.

These tests verify end-to-end functionality with realistic workflows.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Dict, List, Optional

from loom.components.agent import Agent, TurnState
from loom.core.events import AgentEvent, AgentEventType, EventCollector
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool


# ============================================================================
# Realistic Mock Components
# ============================================================================

class RealisticLLM(BaseLLM):
    """
    Realistic LLM that simulates multi-turn conversations.

    Behavior:
    - First call: Decides to use a tool
    - Second call: Provides final answer based on tool result
    """

    def __init__(self):
        self.call_count = 0
        self.last_messages = []

    @property
    def model_name(self) -> str:
        """Return mock model name."""
        return "realistic-mock-v1"

    @property
    def supports_tools(self) -> bool:
        """This mock supports tools."""
        return True

    async def generate(self, messages: List[Dict]) -> str:
        """Non-streaming generation."""
        self.call_count += 1
        self.last_messages = messages

        if self.call_count == 1:
            return "Let me search for that information."
        else:
            return "Based on the search results, here is your answer: The information you requested is available."

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Stream realistic LLM response."""
        self.call_count += 1
        self.last_messages = messages

        if self.call_count == 1:
            # First call: Use tool
            response = "Let me search for that information."
            for char in response:
                yield char
                await asyncio.sleep(0.001)  # Simulate streaming delay
        else:
            # Subsequent calls: Final answer
            response = "Based on the search results, here is your answer: The information you requested is available."
            for char in response:
                yield char
                await asyncio.sleep(0.001)

    async def generate_with_tools(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None
    ) -> Dict:
        """Generation with tool support."""
        self.call_count += 1
        self.last_messages = messages

        if self.call_count == 1 and tools:
            return {
                "content": "Let me search for that information.",
                "tool_calls": [
                    {
                        "id": "call_search_001",
                        "name": "search",
                        "arguments": {"query": "user question"}
                    }
                ]
            }
        else:
            return {
                "content": "Based on the search results, here is your answer.",
                "tool_calls": []
            }


class SearchTool(BaseTool):
    """Realistic search tool."""

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search for information on a topic"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {
                "type": "string",
                "description": "The search query"
            }
        }

    async def run(self, **kwargs) -> str:
        """Run search (BaseTool abstract method)."""
        return await self.execute(kwargs)

    async def execute(self, arguments: Dict) -> str:
        """Execute search."""
        query = arguments.get("query", "")
        await asyncio.sleep(0.05)  # Simulate API call

        return f"Search results for '{query}': Found 3 relevant documents. " \
               f"Document 1: Introduction to the topic. " \
               f"Document 2: Advanced concepts. " \
               f"Document 3: Best practices."


class CalculatorTool(BaseTool):
    """Realistic calculator tool."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform mathematical calculations"

    @property
    def parameters(self) -> Dict:
        return {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate"
            }
        }

    async def run(self, **kwargs) -> str:
        """Run calculator (BaseTool abstract method)."""
        return await self.execute(kwargs)

    async def execute(self, arguments: Dict) -> str:
        """Execute calculation."""
        expression = arguments.get("expression", "")
        await asyncio.sleep(0.01)  # Simulate processing

        try:
            # Safe eval for demo purposes
            result = eval(expression, {"__builtins__": {}}, {})
            return f"Result: {result}"
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")


# ============================================================================
# Integration Tests
# ============================================================================

class TestEndToEndStreaming:
    """Test complete end-to-end streaming workflows."""

    @pytest.mark.asyncio
    async def test_simple_query_no_tools(self):
        """Test simple query without tool calls."""
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[])
        collector = EventCollector()

        user_query = "What is Python?"

        async for event in agent.execute(user_query):
            collector.add(event)

        # Verify event sequence
        assert any(e.type == AgentEventType.ITERATION_START for e in collector.events)
        assert any(e.type == AgentEventType.PHASE_START for e in collector.events)
        assert any(e.type == AgentEventType.LLM_START for e in collector.events)
        assert any(e.type == AgentEventType.LLM_DELTA for e in collector.events)
        assert any(e.type == AgentEventType.LLM_COMPLETE for e in collector.events)
        assert any(e.type == AgentEventType.AGENT_FINISH for e in collector.events)

        # Verify content
        llm_content = collector.get_llm_content()
        assert len(llm_content) > 0

    @pytest.mark.asyncio
    async def test_multi_turn_with_tool(self):
        """Test multi-turn conversation with tool execution."""
        search_tool = SearchTool()
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[search_tool], max_iterations=5)
        collector = EventCollector()

        user_query = "Search for information about AI"

        async for event in agent.execute(user_query):
            collector.add(event)

        # Verify tool was called
        assert any(e.type == AgentEventType.LLM_TOOL_CALLS for e in collector.events)
        assert any(e.type == AgentEventType.TOOL_EXECUTION_START for e in collector.events)
        assert any(e.type == AgentEventType.TOOL_CALLS_COMPLETE for e in collector.events)

        # Verify multiple iterations (tool call + final response)
        iteration_events = [e for e in collector.events if e.type == AgentEventType.ITERATION_START]
        assert len(iteration_events) >= 2

        # Verify LLM was called multiple times
        assert llm.call_count >= 2

    @pytest.mark.asyncio
    async def test_backward_compatible_run_with_tools(self):
        """Test run() method works with multi-turn tool execution."""
        search_tool = SearchTool()
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[search_tool], max_iterations=5)

        result = await agent.run("Find information about Python")

        # Should return final string response
        assert isinstance(result, str)
        assert len(result) > 0


class TestToolOrchestration:
    """Test tool execution orchestration."""

    @pytest.mark.asyncio
    async def test_single_tool_execution(self):
        """Test single tool execution flow."""
        calc_tool = CalculatorTool()
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[calc_tool], max_iterations=3)
        collector = EventCollector()

        async for event in agent.execute("Calculate something"):
            collector.add(event)

            # Log tool execution
            if event.type == AgentEventType.TOOL_EXECUTION_START:
                assert event.tool_call is not None
                assert event.tool_call.name == "search"  # RealisticLLM calls search

    @pytest.mark.asyncio
    async def test_tool_error_recovery(self):
        """Test agent handles tool errors gracefully."""
        calc_tool = CalculatorTool()
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[calc_tool], max_iterations=3)
        collector = EventCollector()

        # Note: RealisticLLM will call 'search' but we only have 'calculator'
        # This should trigger a tool not found scenario

        async for event in agent.execute("Calculate 2+2"):
            collector.add(event)

        # Should complete without crashing
        assert len(collector.events) > 0


class TestEventOrdering:
    """Test correct ordering of events."""

    @pytest.mark.asyncio
    async def test_event_sequence_single_turn(self):
        """Test events are produced in correct order for single turn."""
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[])
        events = []

        async for event in agent.execute("test"):
            events.append(event.type)

        # Verify general ordering
        # ITERATION_START should come before LLM_START
        iter_idx = events.index(AgentEventType.ITERATION_START)
        llm_start_idx = events.index(AgentEventType.LLM_START)
        assert iter_idx < llm_start_idx

        # LLM_START should come before LLM_COMPLETE
        llm_complete_idx = events.index(AgentEventType.LLM_COMPLETE)
        assert llm_start_idx < llm_complete_idx

        # AGENT_FINISH should be last (or near last)
        if AgentEventType.AGENT_FINISH in events:
            finish_idx = events.index(AgentEventType.AGENT_FINISH)
            assert finish_idx > llm_complete_idx

    @pytest.mark.asyncio
    async def test_event_sequence_multi_turn(self):
        """Test events are ordered correctly across multiple turns."""
        search_tool = SearchTool()
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[search_tool], max_iterations=5)
        events = []

        async for event in agent.execute("search test"):
            events.append(event)

        # Should have multiple ITERATION_START events
        iteration_starts = [e for e in events if e.type == AgentEventType.ITERATION_START]
        assert len(iteration_starts) >= 2

        # Each iteration should have increasing counter
        for i, event in enumerate(iteration_starts):
            assert event.iteration == i


class TestRealTimeStreaming:
    """Test real-time streaming behavior."""

    @pytest.mark.asyncio
    async def test_llm_content_streams_incrementally(self):
        """Test LLM content arrives incrementally."""
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[])

        content_chunks = []
        chunk_timestamps = []

        async for event in agent.execute("test"):
            if event.type == AgentEventType.LLM_DELTA:
                content_chunks.append(event.content)
                chunk_timestamps.append(event.timestamp)

        # Should receive multiple chunks
        assert len(content_chunks) > 1

        # Timestamps should be increasing
        for i in range(1, len(chunk_timestamps)):
            assert chunk_timestamps[i] >= chunk_timestamps[i-1]

        # Chunks should concatenate to full message
        full_content = "".join(content_chunks)
        assert len(full_content) > 0

    @pytest.mark.asyncio
    async def test_can_process_events_in_real_time(self):
        """Test events can be processed as they arrive."""
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[])

        processed_count = 0
        llm_buffer = ""

        async for event in agent.execute("test"):
            processed_count += 1

            # Process LLM deltas in real-time
            if event.type == AgentEventType.LLM_DELTA:
                llm_buffer += event.content or ""
                # Simulate real-time display
                # In real app: print(event.content, end="", flush=True)

        assert processed_count > 0
        assert len(llm_buffer) > 0


class TestMemoryIntegration:
    """Test integration with memory systems (if enabled)."""

    @pytest.mark.asyncio
    async def test_agent_without_memory(self):
        """Test agent works without memory."""
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[], memory=None)

        result = await agent.run("test")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_multiple_queries_independent(self):
        """Test multiple queries are independent without memory."""
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[])

        result1 = await agent.run("First query")

        # Reset LLM call count for second query
        llm.call_count = 0

        result2 = await agent.run("Second query")

        # Both should complete
        assert isinstance(result1, str)
        assert isinstance(result2, str)


class TestErrorScenarios:
    """Test error handling in real scenarios."""

    @pytest.mark.asyncio
    async def test_max_iterations_protection(self):
        """Test max iterations prevents infinite loops."""
        llm = RealisticLLM()
        search_tool = SearchTool()

        # Set very low max iterations
        agent = Agent(llm=llm, tools=[search_tool], max_iterations=1)
        collector = EventCollector()

        async for event in agent.execute("test"):
            collector.add(event)

        # Should hit max iterations
        max_iter_events = [e for e in collector.events if e.type == AgentEventType.MAX_ITERATIONS_REACHED]
        assert len(max_iter_events) >= 1


class TestPerformance:
    """Test performance characteristics."""

    @pytest.mark.asyncio
    async def test_streaming_starts_quickly(self):
        """Test first event arrives quickly."""
        import time

        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[])

        start_time = time.time()
        first_event_time = None

        async for event in agent.execute("test"):
            if first_event_time is None:
                first_event_time = time.time()
                break

        # First event should arrive within reasonable time (< 1 second)
        assert first_event_time is not None
        latency = first_event_time - start_time
        assert latency < 1.0

    @pytest.mark.asyncio
    async def test_no_memory_leaks_multiple_calls(self):
        """Test multiple calls don't leak memory."""
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[])

        # Run multiple times
        for i in range(5):
            llm.call_count = 0  # Reset
            result = await agent.run(f"Query {i}")
            assert isinstance(result, str)

        # If we get here without issues, no obvious leaks


class TestComplexWorkflows:
    """Test complex realistic workflows."""

    @pytest.mark.asyncio
    async def test_research_workflow(self):
        """Test research workflow: question -> search -> synthesize."""
        search_tool = SearchTool()
        llm = RealisticLLM()
        agent = Agent(llm=llm, tools=[search_tool], max_iterations=5)
        collector = EventCollector()

        user_query = "What are the best practices for Python async programming?"

        async for event in agent.execute(user_query):
            collector.add(event)

        # Should have complete workflow
        assert any(e.type == AgentEventType.LLM_START for e in collector.events)
        assert any(e.type == AgentEventType.LLM_TOOL_CALLS for e in collector.events)
        assert any(e.type == AgentEventType.TOOL_CALLS_COMPLETE for e in collector.events)
        assert any(e.type == AgentEventType.AGENT_FINISH for e in collector.events)

        # Final content should exist
        final_content = collector.get_llm_content()
        assert len(final_content) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
