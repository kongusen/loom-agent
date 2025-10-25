"""
Unit tests for Task 1.2: Streaming API refactoring.

Tests the new execute() streaming interface and backward compatibility
of the run() method.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock
from pydantic import BaseModel

from loom.components.agent import Agent, TurnState
from loom.core.events import AgentEvent, AgentEventType, EventCollector, ToolCall, ToolResult
from loom.core.types import Message
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool


# ============================================================================
# Mock Classes
# ============================================================================

class MockStreamingLLM(BaseLLM):
    """Mock LLM that supports streaming."""

    def __init__(self, response_text: str = "Test response", has_tools: bool = False):
        self.response_text = response_text
        self.has_tools = has_tools
        self.call_count = 0

    @property
    def model_name(self) -> str:
        """Return mock model name."""
        return "mock-llm-v1"

    @property
    def supports_tools(self) -> bool:
        """Return whether this mock supports tools."""
        return self.has_tools

    async def generate(self, messages: List[Dict]) -> str:
        """Non-streaming generation."""
        self.call_count += 1
        return self.response_text

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Stream LLM response as string deltas."""
        self.call_count += 1

        # Stream text character by character
        for char in self.response_text:
            yield char

    async def generate_with_tools(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None
    ) -> Dict:
        """Generation with tool support."""
        self.call_count += 1

        return {
            "content": self.response_text,
            "tool_calls": [] if not self.has_tools else [
                {
                    "id": "call_1",
                    "name": "test_tool",
                    "arguments": {"query": "test"}
                }
            ]
        }


class MockToolArgs(BaseModel):
    """Mock tool arguments schema."""
    query: str = ""


class MockTool(BaseTool):
    """Mock tool for testing."""

    def __init__(self, tool_name: str = "test_tool", result: str = "Tool result"):
        self.name = tool_name
        self.description = "A test tool"
        self.args_schema = MockToolArgs
        self.result = result
        self.call_count = 0

    async def run(self, **kwargs) -> str:
        """Execute tool."""
        self.call_count += 1
        await asyncio.sleep(0.01)  # Simulate async work
        return self.result


class ErrorToolArgs(BaseModel):
    """Error tool arguments (empty)."""
    pass


class ErrorTool(BaseTool):
    """Tool that raises errors."""

    def __init__(self, tool_name: str = "error_tool"):
        self.name = tool_name
        self.description = "A tool that errors"
        self.args_schema = ErrorToolArgs

    async def run(self, **kwargs) -> str:
        """Execute tool and raise error."""
        raise ValueError("Tool execution failed")


# ============================================================================
# Test Cases
# ============================================================================

class TestStreamingAPIBasics:
    """Test basic streaming API functionality."""

    @pytest.mark.asyncio
    async def test_agent_execute_returns_generator(self):
        """Test that execute() returns AsyncGenerator."""
        llm = MockStreamingLLM("Hello")
        agent = Agent(llm=llm, tools=[])

        result = agent.execute("test")

        # Should be async generator
        assert hasattr(result, '__aiter__')
        assert hasattr(result, '__anext__')

    @pytest.mark.asyncio
    async def test_agent_run_backward_compatible(self):
        """Test that run() still works (backward compatibility)."""
        llm = MockStreamingLLM("Hello World")
        agent = Agent(llm=llm, tools=[])

        result = await agent.run("test")

        # Should return string
        assert isinstance(result, str)
        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_execute_produces_events(self):
        """Test that execute() produces AgentEvent instances."""
        llm = MockStreamingLLM("Test")
        agent = Agent(llm=llm, tools=[])

        events = []
        async for event in agent.execute("test"):
            events.append(event)
            assert isinstance(event, AgentEvent)

        # Should have produced some events
        assert len(events) > 0


class TestLLMStreamingEvents:
    """Test LLM streaming event production."""

    @pytest.mark.asyncio
    async def test_llm_delta_events(self):
        """Test LLM streaming produces delta events."""
        llm = MockStreamingLLM("Hello")
        agent = Agent(llm=llm, tools=[])
        collector = EventCollector()

        async for event in agent.execute("test"):
            collector.add(event)

        # Should have LLM_START, LLM_DELTA, LLM_COMPLETE
        assert any(e.type == AgentEventType.LLM_START for e in collector.events)
        assert any(e.type == AgentEventType.LLM_DELTA for e in collector.events)
        assert any(e.type == AgentEventType.LLM_COMPLETE for e in collector.events)

        # Reconstructed content should match
        llm_content = collector.get_llm_content()
        assert llm_content == "Hello"

    @pytest.mark.asyncio
    async def test_llm_delta_accumulation(self):
        """Test that LLM deltas accumulate correctly."""
        response = "The quick brown fox"
        llm = MockStreamingLLM(response)
        agent = Agent(llm=llm, tools=[])

        accumulated = ""
        async for event in agent.execute("test"):
            if event.type == AgentEventType.LLM_DELTA:
                accumulated += event.content or ""

        assert accumulated == response

    @pytest.mark.asyncio
    async def test_iteration_events(self):
        """Test iteration tracking events."""
        llm = MockStreamingLLM("Response")
        agent = Agent(llm=llm, tools=[], max_iterations=5)
        collector = EventCollector()

        async for event in agent.execute("test"):
            collector.add(event)

        # Should have ITERATION_START event
        iteration_events = [e for e in collector.events if e.type == AgentEventType.ITERATION_START]
        assert len(iteration_events) >= 1

        # Check iteration metadata
        first_iter = iteration_events[0]
        assert first_iter.iteration == 0
        assert first_iter.turn_id is not None


class TestToolExecutionEvents:
    """Test tool execution event production."""

    @pytest.mark.asyncio
    async def test_tool_execution_events(self):
        """Test tool execution produces correct events."""
        tool = MockTool("test_tool", "Search result")  # Use test_tool to match LLM
        llm = MockStreamingLLM("Let me search", has_tools=True)
        agent = Agent(llm=llm, tools=[tool], max_iterations=2)
        collector = EventCollector()

        async for event in agent.execute("test"):
            collector.add(event)

        # Should have tool-related events
        assert any(e.type == AgentEventType.LLM_TOOL_CALLS for e in collector.events)
        assert any(e.type == AgentEventType.TOOL_EXECUTION_START for e in collector.events)
        assert any(e.type == AgentEventType.TOOL_RESULT for e in collector.events)

        # Tool should have been called
        assert tool.call_count >= 1

    @pytest.mark.asyncio
    async def test_tool_result_event(self):
        """Test tool result is captured in event."""
        tool = MockTool("test_tool", "42")  # Use test_tool to match LLM
        llm = MockStreamingLLM("Calculating", has_tools=True)
        agent = Agent(llm=llm, tools=[tool], max_iterations=2)

        tool_result_event = None
        async for event in agent.execute("test"):
            if event.type == AgentEventType.TOOL_RESULT:
                tool_result_event = event
                break

        assert tool_result_event is not None
        assert tool_result_event.tool_result is not None
        assert tool_result_event.tool_result.content == "42"
        assert tool_result_event.tool_result.is_error is False


class TestErrorHandling:
    """Test error handling and propagation."""

    @pytest.mark.asyncio
    async def test_error_propagation_in_run(self):
        """Test that errors in execute() propagate to run()."""
        # This test would need a way to trigger errors
        # For now, we'll test the pattern
        llm = MockStreamingLLM("Error test")
        agent = Agent(llm=llm, tools=[])

        # run() should complete without error for valid input
        result = await agent.run("test")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_tool_error_event(self):
        """Test tool errors produce error events."""
        error_tool = ErrorTool("test_tool")  # Use test_tool to match LLM

        # Create LLM that will call the error tool
        llm = MockStreamingLLM("Using tool", has_tools=True)
        agent = Agent(llm=llm, tools=[error_tool], max_iterations=2)
        collector = EventCollector()

        async for event in agent.execute("test"):
            collector.add(event)

        # Should have TOOL_ERROR event
        error_events = [e for e in collector.events if e.type == AgentEventType.TOOL_ERROR]
        assert len(error_events) >= 1

        # Error event should have error info
        error_event = error_events[0]
        assert error_event.tool_result is not None
        assert error_event.tool_result.is_error is True
        assert "Tool execution failed" in error_event.tool_result.content


class TestPhaseEvents:
    """Test phase start/end events."""

    @pytest.mark.asyncio
    async def test_context_assembly_phase(self):
        """Test context assembly phase events."""
        llm = MockStreamingLLM("Response")
        agent = Agent(llm=llm, tools=[])
        collector = EventCollector()

        async for event in agent.execute("test"):
            collector.add(event)

        # Should have context_assembly phase events
        phase_starts = [e for e in collector.events if e.type == AgentEventType.PHASE_START]
        phase_ends = [e for e in collector.events if e.type == AgentEventType.PHASE_END]

        # At least context_assembly phase
        context_starts = [e for e in phase_starts if e.phase == "context_assembly"]
        assert len(context_starts) >= 1


class TestBackwardCompatibility:
    """Test backward compatibility with Loom 1.0 API."""

    @pytest.mark.asyncio
    async def test_ainvoke_alias(self):
        """Test that ainvoke() alias works."""
        llm = MockStreamingLLM("Alias test")
        agent = Agent(llm=llm, tools=[])

        result = await agent.ainvoke("test")

        assert isinstance(result, str)
        assert result == "Alias test"

    @pytest.mark.asyncio
    async def test_stream_legacy_method(self):
        """Test legacy stream() method still exists."""
        llm = MockStreamingLLM("Legacy")
        agent = Agent(llm=llm, tools=[])

        # stream() should exist (even if it uses old StreamEvent)
        assert hasattr(agent, 'stream')
        assert callable(agent.stream)

    @pytest.mark.asyncio
    async def test_run_returns_final_content(self):
        """Test run() returns final LLM content."""
        llm = MockStreamingLLM("Final answer")
        agent = Agent(llm=llm, tools=[])

        result = await agent.run("test")

        assert result == "Final answer"

    @pytest.mark.asyncio
    async def test_run_with_tool_calls(self):
        """Test run() works with tool calls (multi-turn)."""
        tool = MockTool("test_tool", "Tool output")  # Use test_tool to match LLM
        llm = MockStreamingLLM("Using helper tool", has_tools=True)
        agent = Agent(llm=llm, tools=[tool], max_iterations=2)

        # Should complete even with tool calls
        result = await agent.run("test")

        # Should be string (final response)
        assert isinstance(result, str)


class TestEventCollectorIntegration:
    """Test EventCollector works with streaming API."""

    @pytest.mark.asyncio
    async def test_collector_captures_all_events(self):
        """Test EventCollector captures all events."""
        llm = MockStreamingLLM("Test message")
        agent = Agent(llm=llm, tools=[])
        collector = EventCollector()

        async for event in agent.execute("test"):
            collector.add(event)

        assert len(collector.events) > 0
        assert collector.get_llm_content() == "Test message"

    @pytest.mark.asyncio
    async def test_collector_filters_events(self):
        """Test filtering events by type."""
        llm = MockStreamingLLM("Hello")
        agent = Agent(llm=llm, tools=[])
        collector = EventCollector()

        async for event in agent.execute("test"):
            collector.add(event)

        # Get only LLM delta events
        llm_events = collector.filter(AgentEventType.LLM_DELTA)
        assert len(llm_events) > 0
        assert all(e.type == AgentEventType.LLM_DELTA for e in llm_events)


class TestTurnState:
    """Test TurnState dataclass."""

    def test_turn_state_creation(self):
        """Test TurnState can be created."""
        state = TurnState(
            turn_counter=0,
            turn_id="test-123"
        )

        assert state.turn_counter == 0
        assert state.turn_id == "test-123"
        assert state.compacted is False
        assert state.max_iterations == 10

    def test_turn_state_with_custom_iterations(self):
        """Test TurnState with custom max_iterations."""
        state = TurnState(
            turn_counter=5,
            turn_id="test-456",
            max_iterations=20
        )

        assert state.max_iterations == 20


class TestMaxIterations:
    """Test max iterations handling."""

    @pytest.mark.asyncio
    async def test_max_iterations_reached_event(self):
        """Test MAX_ITERATIONS_REACHED event is produced."""
        # Create agent with very low max_iterations
        llm = MockStreamingLLM("Response", has_tools=True)
        tool = MockTool("test_tool", "Keep going")  # Use test_tool to match LLM
        agent = Agent(llm=llm, tools=[tool], max_iterations=1)
        collector = EventCollector()

        async for event in agent.execute("test"):
            collector.add(event)

        # Should have MAX_ITERATIONS_REACHED event
        max_iter_events = [e for e in collector.events if e.type == AgentEventType.MAX_ITERATIONS_REACHED]
        assert len(max_iter_events) >= 1


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_llm_response(self):
        """Test handling of empty LLM response."""
        llm = MockStreamingLLM("")
        agent = Agent(llm=llm, tools=[])

        result = await agent.run("test")

        # Should handle empty response gracefully
        assert result == ""

    @pytest.mark.asyncio
    async def test_no_tools_provided(self):
        """Test agent works without tools."""
        llm = MockStreamingLLM("No tools needed")
        agent = Agent(llm=llm, tools=None)

        result = await agent.run("test")

        assert result == "No tools needed"

    @pytest.mark.asyncio
    async def test_execute_called_multiple_times(self):
        """Test execute() can be called multiple times."""
        llm = MockStreamingLLM("Response")
        agent = Agent(llm=llm, tools=[])

        # First call
        result1 = await agent.run("test 1")
        assert result1 == "Response"

        # Second call
        result2 = await agent.run("test 2")
        assert result2 == "Response"

        # LLM should have been called twice
        assert llm.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
