"""
Unit tests for AgentEvent system (Loom 2.0)
"""

import pytest
import asyncio
from typing import AsyncGenerator

from loom.core.events import (
    AgentEvent,
    AgentEventType,
    ToolCall,
    ToolResult,
    EventCollector
)
from loom.interfaces.event_producer import (
    EventProducer,
    merge_event_streams,
    collect_events
)


# ===== Test AgentEvent Creation =====

class TestAgentEventCreation:
    """Test AgentEvent instantiation and convenience constructors"""

    def test_basic_event_creation(self):
        """Test creating a basic event"""
        event = AgentEvent(type=AgentEventType.PHASE_START, phase="test")

        assert event.type == AgentEventType.PHASE_START
        assert event.phase == "test"
        assert event.timestamp > 0
        assert event.turn_id is not None

    def test_phase_start_constructor(self):
        """Test AgentEvent.phase_start() convenience method"""
        event = AgentEvent.phase_start("context_assembly", tokens=1000)

        assert event.type == AgentEventType.PHASE_START
        assert event.phase == "context_assembly"
        assert event.metadata["tokens"] == 1000

    def test_llm_delta_constructor(self):
        """Test AgentEvent.llm_delta() convenience method"""
        event = AgentEvent.llm_delta("Hello, ", model="gpt-4")

        assert event.type == AgentEventType.LLM_DELTA
        assert event.content == "Hello, "
        assert event.metadata["model"] == "gpt-4"

    def test_tool_progress_constructor(self):
        """Test AgentEvent.tool_progress() convenience method"""
        event = AgentEvent.tool_progress(
            "GrepTool",
            "Searching files...",
            files_searched=10
        )

        assert event.type == AgentEventType.TOOL_PROGRESS
        assert event.metadata["tool_name"] == "GrepTool"
        assert event.metadata["status"] == "Searching files..."
        assert event.metadata["files_searched"] == 10

    def test_tool_result_constructor(self):
        """Test AgentEvent.tool_result() convenience method"""
        tool_result = ToolResult(
            tool_call_id="call_123",
            tool_name="ReadTool",
            content="file contents",
            execution_time_ms=45.2
        )

        event = AgentEvent.tool_result(tool_result)

        assert event.type == AgentEventType.TOOL_RESULT
        assert event.tool_result == tool_result
        assert event.tool_result.execution_time_ms == 45.2

    def test_agent_finish_constructor(self):
        """Test AgentEvent.agent_finish() convenience method"""
        event = AgentEvent.agent_finish(
            "Task completed successfully",
            tokens_used=2500
        )

        assert event.type == AgentEventType.AGENT_FINISH
        assert event.content == "Task completed successfully"
        assert event.metadata["tokens_used"] == 2500

    def test_error_constructor(self):
        """Test AgentEvent.error() convenience method"""
        error = ValueError("Invalid input")
        event = AgentEvent.error(error, recoverable=True)

        assert event.type == AgentEventType.ERROR
        assert event.error == error
        assert event.metadata["recoverable"] is True


# ===== Test ToolCall and ToolResult =====

class TestToolModels:
    """Test ToolCall and ToolResult dataclasses"""

    def test_tool_call_creation(self):
        """Test creating a ToolCall"""
        tool_call = ToolCall(
            id="call_abc",
            name="ReadTool",
            arguments={"file_path": "/path/to/file.py"}
        )

        assert tool_call.id == "call_abc"
        assert tool_call.name == "ReadTool"
        assert tool_call.arguments["file_path"] == "/path/to/file.py"

    def test_tool_call_auto_id(self):
        """Test ToolCall auto-generates ID if not provided"""
        tool_call = ToolCall(
            id="",
            name="GrepTool",
            arguments={"pattern": "TODO"}
        )

        assert tool_call.id.startswith("call_")
        assert len(tool_call.id) > 5

    def test_tool_result_success(self):
        """Test successful ToolResult"""
        result = ToolResult(
            tool_call_id="call_123",
            tool_name="ReadTool",
            content="File content here",
            is_error=False,
            execution_time_ms=23.5
        )

        assert result.is_error is False
        assert result.content == "File content here"
        assert result.execution_time_ms == 23.5

    def test_tool_result_error(self):
        """Test error ToolResult"""
        result = ToolResult(
            tool_call_id="call_456",
            tool_name="EditTool",
            content="Error: File not found",
            is_error=True
        )

        assert result.is_error is True
        assert "Error" in result.content


# ===== Test AgentEvent Utility Methods =====

class TestAgentEventUtils:
    """Test AgentEvent utility methods"""

    def test_is_terminal_finish(self):
        """Test is_terminal() for AGENT_FINISH"""
        event = AgentEvent.agent_finish("Done")
        assert event.is_terminal() is True

    def test_is_terminal_error(self):
        """Test is_terminal() for ERROR"""
        event = AgentEvent.error(ValueError("test"))
        assert event.is_terminal() is True

    def test_is_terminal_normal_event(self):
        """Test is_terminal() for normal events"""
        event = AgentEvent.llm_delta("text")
        assert event.is_terminal() is False

    def test_is_llm_content_delta(self):
        """Test is_llm_content() for LLM_DELTA"""
        event = AgentEvent.llm_delta("text")
        assert event.is_llm_content() is True

    def test_is_llm_content_finish(self):
        """Test is_llm_content() for AGENT_FINISH"""
        event = AgentEvent.agent_finish("Done")
        assert event.is_llm_content() is True

    def test_is_tool_event(self):
        """Test is_tool_event() for tool events"""
        events = [
            AgentEvent(type=AgentEventType.TOOL_PROGRESS),
            AgentEvent(type=AgentEventType.TOOL_RESULT),
            AgentEvent(type=AgentEventType.TOOL_ERROR),
        ]

        for event in events:
            assert event.is_tool_event() is True

    def test_is_not_tool_event(self):
        """Test is_tool_event() for non-tool events"""
        event = AgentEvent.llm_delta("text")
        assert event.is_tool_event() is False

    def test_repr_format(self):
        """Test __repr__ produces readable output"""
        event = AgentEvent.llm_delta("Hello world", model="gpt-4")
        repr_str = repr(event)

        assert "llm_delta" in repr_str
        assert "Hello world" in repr_str


# ===== Test EventCollector =====

class TestEventCollector:
    """Test EventCollector helper class"""

    def test_add_and_filter(self):
        """Test adding and filtering events"""
        collector = EventCollector()

        collector.add(AgentEvent.llm_delta("Hello "))
        collector.add(AgentEvent.llm_delta("world"))
        collector.add(AgentEvent.phase_start("test"))

        llm_events = collector.filter(AgentEventType.LLM_DELTA)
        assert len(llm_events) == 2

        phase_events = collector.filter(AgentEventType.PHASE_START)
        assert len(phase_events) == 1

    def test_get_llm_content(self):
        """Test reconstructing LLM content from deltas"""
        collector = EventCollector()

        collector.add(AgentEvent.llm_delta("Hello "))
        collector.add(AgentEvent.llm_delta("world"))
        collector.add(AgentEvent.llm_delta("!"))

        content = collector.get_llm_content()
        assert content == "Hello world!"

    def test_get_tool_results(self):
        """Test extracting tool results"""
        collector = EventCollector()

        result1 = ToolResult("call_1", "ReadTool", "content1")
        result2 = ToolResult("call_2", "GrepTool", "content2")

        collector.add(AgentEvent.tool_result(result1))
        collector.add(AgentEvent.tool_result(result2))
        collector.add(AgentEvent.llm_delta("text"))

        results = collector.get_tool_results()
        assert len(results) == 2
        assert results[0].tool_name == "ReadTool"
        assert results[1].tool_name == "GrepTool"

    def test_get_errors(self):
        """Test extracting errors"""
        collector = EventCollector()

        error1 = ValueError("error 1")
        error2 = RuntimeError("error 2")

        collector.add(AgentEvent.error(error1))
        collector.add(AgentEvent.llm_delta("text"))
        collector.add(AgentEvent.error(error2))

        errors = collector.get_errors()
        assert len(errors) == 2
        assert isinstance(errors[0], ValueError)
        assert isinstance(errors[1], RuntimeError)

    def test_get_final_response(self):
        """Test extracting final response"""
        collector = EventCollector()

        collector.add(AgentEvent.llm_delta("partial"))
        collector.add(AgentEvent.agent_finish("Final response"))

        final = collector.get_final_response()
        assert final == "Final response"

    def test_get_final_response_none(self):
        """Test get_final_response when no finish event"""
        collector = EventCollector()
        collector.add(AgentEvent.llm_delta("text"))

        final = collector.get_final_response()
        assert final is None


# ===== Test EventProducer Protocol =====

class TestEventProducerProtocol:
    """Test EventProducer protocol and helpers"""

    @pytest.mark.asyncio
    async def test_simple_producer(self):
        """Test a simple EventProducer implementation"""

        class SimpleProducer:
            async def produce_events(self) -> AsyncGenerator[AgentEvent, None]:
                yield AgentEvent.phase_start("test")
                yield AgentEvent.llm_delta("Hello")
                yield AgentEvent.phase_end("test")

        producer = SimpleProducer()
        events = await collect_events(producer)

        assert len(events) == 3
        assert events[0].type == AgentEventType.PHASE_START
        assert events[1].type == AgentEventType.LLM_DELTA
        assert events[2].type == AgentEventType.PHASE_END

    @pytest.mark.asyncio
    async def test_collect_events(self):
        """Test collect_events helper"""

        class TestProducer:
            async def produce_events(self):
                for i in range(5):
                    yield AgentEvent.llm_delta(f"chunk{i}")

        producer = TestProducer()
        events = await collect_events(producer)

        assert len(events) == 5
        assert all(e.type == AgentEventType.LLM_DELTA for e in events)

    @pytest.mark.asyncio
    async def test_event_iteration(self):
        """Test iterating over event stream"""

        class TestProducer:
            async def produce_events(self):
                yield AgentEvent.phase_start("test")
                yield AgentEvent.llm_delta("content")
                yield AgentEvent.phase_end("test")

        producer = TestProducer()
        event_types = []

        async for event in producer.produce_events():
            event_types.append(event.type)

        assert len(event_types) == 3
        assert event_types[0] == AgentEventType.PHASE_START
        assert event_types[1] == AgentEventType.LLM_DELTA
        assert event_types[2] == AgentEventType.PHASE_END


# ===== Test Event Streaming Patterns =====

class TestEventStreaming:
    """Test realistic event streaming patterns"""

    @pytest.mark.asyncio
    async def test_llm_streaming_pattern(self):
        """Test typical LLM streaming pattern"""

        class MockLLMProducer:
            async def produce_events(self):
                yield AgentEvent(type=AgentEventType.LLM_START)

                # Stream tokens
                for token in ["Hello", " ", "world", "!"]:
                    yield AgentEvent.llm_delta(token)
                    await asyncio.sleep(0.01)  # Simulate streaming delay

                yield AgentEvent(type=AgentEventType.LLM_COMPLETE)

        producer = MockLLMProducer()
        collector = EventCollector()

        async for event in producer.produce_events():
            collector.add(event)

        # Verify all events collected
        assert len(collector.events) == 6  # START + 4 deltas + COMPLETE

        # Verify reconstructed content
        content = collector.get_llm_content()
        assert content == "Hello world!"

    @pytest.mark.asyncio
    async def test_tool_execution_pattern(self):
        """Test typical tool execution pattern"""

        class MockToolProducer:
            async def produce_events(self):
                tool_call = ToolCall(
                    id="call_123",
                    name="GrepTool",
                    arguments={"pattern": "TODO"}
                )

                yield AgentEvent(
                    type=AgentEventType.TOOL_EXECUTION_START,
                    tool_call=tool_call
                )

                # Progress updates
                yield AgentEvent.tool_progress("GrepTool", "Searching files...")
                await asyncio.sleep(0.01)

                yield AgentEvent.tool_progress("GrepTool", "Found 5 matches")
                await asyncio.sleep(0.01)

                # Final result
                result = ToolResult(
                    tool_call_id="call_123",
                    tool_name="GrepTool",
                    content="Match results here",
                    execution_time_ms=25.3
                )
                yield AgentEvent.tool_result(result)

        producer = MockToolProducer()
        events = await collect_events(producer)

        assert len(events) == 4
        assert events[0].type == AgentEventType.TOOL_EXECUTION_START
        assert events[1].type == AgentEventType.TOOL_PROGRESS
        assert events[2].type == AgentEventType.TOOL_PROGRESS
        assert events[3].type == AgentEventType.TOOL_RESULT

    @pytest.mark.asyncio
    async def test_full_agent_execution_pattern(self):
        """Test complete agent execution event flow"""

        class MockAgentProducer:
            async def produce_events(self):
                # Phase 1: Context
                yield AgentEvent.phase_start("context_assembly")
                yield AgentEvent.phase_end("context_assembly", tokens=1500)

                # Phase 2: RAG
                yield AgentEvent(type=AgentEventType.RETRIEVAL_START)
                yield AgentEvent(
                    type=AgentEventType.RETRIEVAL_PROGRESS,
                    metadata={"docs_found": 3}
                )
                yield AgentEvent(type=AgentEventType.RETRIEVAL_COMPLETE)

                # Phase 3: LLM
                yield AgentEvent(type=AgentEventType.LLM_START)
                yield AgentEvent.llm_delta("Based on ")
                yield AgentEvent.llm_delta("the docs, ")
                yield AgentEvent(type=AgentEventType.LLM_COMPLETE)

                # Phase 4: Finish
                yield AgentEvent.agent_finish("Based on the docs, ...")

        producer = MockAgentProducer()
        collector = EventCollector()

        async for event in producer.produce_events():
            collector.add(event)

        # Verify phases
        phase_starts = collector.filter(AgentEventType.PHASE_START)
        assert len(phase_starts) == 1

        # Verify RAG
        retrieval_events = collector.filter(AgentEventType.RETRIEVAL_PROGRESS)
        assert len(retrieval_events) == 1

        # Verify LLM content
        llm_content = collector.get_llm_content()
        assert llm_content == "Based on the docs, "

        # Verify completion
        final = collector.get_final_response()
        assert final == "Based on the docs, ..."


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
