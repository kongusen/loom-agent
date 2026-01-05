"""
Tests for LLM Base Handler
"""

import pytest
import asyncio

from loom.llm.providers.base_handler import ToolCallAggregator, BaseResponseHandler
from loom.llm.interface import StreamChunk


class TestToolCallAggregator:
    """Test ToolCallAggregator functionality."""

    def test_initialization(self):
        """Test aggregator initialization."""
        aggregator = ToolCallAggregator()
        assert aggregator.buffer == {}
        assert aggregator.started == {}

    def test_add_chunk_creates_new_entry(self):
        """Test adding chunk creates new buffer entry."""
        aggregator = ToolCallAggregator()

        result = aggregator.add_chunk(index=0, tool_id="call_123", name="test_tool")

        # Should have created buffer entry
        assert 0 in aggregator.buffer
        assert aggregator.buffer[0]["id"] == "call_123"
        assert aggregator.buffer[0]["name"] == "test_tool"
        assert aggregator.started[0] is True

    def test_add_chunk_returns_start_event(self):
        """Test that first chunk returns tool_call_start event."""
        aggregator = ToolCallAggregator()

        result = aggregator.add_chunk(index=0, name="test_tool")

        assert result is not None
        assert result.type == "tool_call_start"
        assert result.content["name"] == "test_tool"
        assert result.content["index"] == 0

    def test_add_chunk_returns_none_after_first(self):
        """Test that subsequent chunks return None."""
        aggregator = ToolCallAggregator()

        # First chunk returns start event
        aggregator.add_chunk(index=0, name="test_tool")

        # Subsequent chunks return None
        result = aggregator.add_chunk(index=0, arguments='{"key":')
        assert result is None

    def test_add_chunk_aggregates_id(self):
        """Test that tool_id is aggregated."""
        aggregator = ToolCallAggregator()

        aggregator.add_chunk(index=0, tool_id="call_123")
        aggregator.add_chunk(index=0, name="tool")

        assert aggregator.buffer[0]["id"] == "call_123"

    def test_add_chunk_aggregates_name(self):
        """Test that name is aggregated."""
        aggregator = ToolCallAggregator()

        aggregator.add_chunk(index=0, name="tool")

        assert aggregator.buffer[0]["name"] == "tool"

    def test_add_chunk_aggregates_arguments(self):
        """Test that arguments are concatenated."""
        aggregator = ToolCallAggregator()

        aggregator.add_chunk(index=0, name="tool")
        aggregator.add_chunk(index=0, arguments='{"key":')
        aggregator.add_chunk(index=0, arguments=' "value"}')

        assert aggregator.buffer[0]["arguments"] == '{"key": "value"}'

    def test_add_chunk_multiple_indices(self):
        """Test handling multiple tool call indices."""
        aggregator = ToolCallAggregator()

        aggregator.add_chunk(index=0, name="tool_a")
        aggregator.add_chunk(index=1, name="tool_b")

        assert 0 in aggregator.buffer
        assert 1 in aggregator.buffer
        assert aggregator.buffer[0]["name"] == "tool_a"
        assert aggregator.buffer[1]["name"] == "tool_b"

    def test_get_complete_calls_valid_json(self):
        """Test get_complete_calls with valid JSON arguments."""
        aggregator = ToolCallAggregator()

        aggregator.add_chunk(index=0, tool_id="call_123", name="test_tool")
        aggregator.add_chunk(index=0, arguments='{"key": "value"}')

        complete_calls = list(aggregator.get_complete_calls())

        assert len(complete_calls) == 1
        assert complete_calls[0].type == "tool_call_complete"
        assert complete_calls[0].content["name"] == "test_tool"
        assert complete_calls[0].content["arguments"] == '{"key": "value"}'

    def test_get_complete_calls_invalid_json(self):
        """Test get_complete_calls with invalid JSON arguments."""
        aggregator = ToolCallAggregator()

        aggregator.add_chunk(index=0, tool_id="call_123", name="test_tool")
        aggregator.add_chunk(index=0, arguments='{"invalid": json}')

        complete_calls = list(aggregator.get_complete_calls())

        assert len(complete_calls) == 1
        assert complete_calls[0].type == "error"
        assert complete_calls[0].content["error"] == "invalid_tool_arguments"

    def test_get_complete_calls_skips_incomplete(self):
        """Test get_complete_calls skips incomplete tool calls."""
        aggregator = ToolCallAggregator()

        # Add tool call with no name
        aggregator.add_chunk(index=0, tool_id="call_123")

        complete_calls = list(aggregator.get_complete_calls())

        assert len(complete_calls) == 0

    def test_get_complete_calls_multiple_tools(self):
        """Test get_complete_calls with multiple tool calls."""
        aggregator = ToolCallAggregator()

        aggregator.add_chunk(index=0, tool_id="call_1", name="tool_a")
        aggregator.add_chunk(index=0, arguments='{"a": 1}')
        aggregator.add_chunk(index=1, tool_id="call_2", name="tool_b")
        aggregator.add_chunk(index=1, arguments='{"b": 2}')

        complete_calls = list(aggregator.get_complete_calls())

        assert len(complete_calls) == 2
        assert complete_calls[0].content["name"] == "tool_a"
        assert complete_calls[1].content["name"] == "tool_b"

    def test_clear(self):
        """Test clearing the aggregator."""
        aggregator = ToolCallAggregator()

        aggregator.add_chunk(index=0, name="test_tool")
        aggregator.add_chunk(index=1, name="another_tool")

        aggregator.clear()

        assert aggregator.buffer == {}
        assert aggregator.started == {}


class TestBaseResponseHandler:
    """Test BaseResponseHandler functionality."""

    def test_initialization(self):
        """Test handler initialization creates aggregator."""
        # BaseResponseHandler is abstract, so we create a concrete subclass
        class ConcreteHandler(BaseResponseHandler):
            async def handle_stream_chunk(self, chunk):
                yield StreamChunk(type="text", content="test", metadata={})

        handler = ConcreteHandler()
        assert handler.aggregator is not None
        assert isinstance(handler.aggregator, ToolCallAggregator)

    def test_create_error_chunk_basic(self):
        """Test creating basic error chunk."""
        class ConcreteHandler(BaseResponseHandler):
            async def handle_stream_chunk(self, chunk):
                yield StreamChunk(type="text", content="test", metadata={})

        handler = ConcreteHandler()
        error = ValueError("Test error")

        chunk = handler.create_error_chunk(error)

        assert chunk.type == "error"
        assert chunk.content["error"] == "stream_error"
        assert "Test error" in chunk.content["message"]
        assert chunk.content["type"] == "ValueError"

    def test_create_error_chunk_with_context(self):
        """Test creating error chunk with context."""
        class ConcreteHandler(BaseResponseHandler):
            async def handle_stream_chunk(self, chunk):
                yield StreamChunk(type="text", content="test", metadata={})

        handler = ConcreteHandler()
        error = RuntimeError("Test error")
        context = {"additional": "info"}

        chunk = handler.create_error_chunk(error, context=context)

        assert chunk.type == "error"
        assert chunk.content["context"] == context

    def test_create_done_chunk_basic(self):
        """Test creating basic done chunk."""
        class ConcreteHandler(BaseResponseHandler):
            async def handle_stream_chunk(self, chunk):
                yield StreamChunk(type="text", content="test", metadata={})

        handler = ConcreteHandler()

        chunk = handler.create_done_chunk("stop")

        assert chunk.type == "done"
        assert chunk.content == ""
        assert chunk.metadata["finish_reason"] == "stop"

    def test_create_done_chunk_with_token_usage(self):
        """Test creating done chunk with token usage."""
        class ConcreteHandler(BaseResponseHandler):
            async def handle_stream_chunk(self, chunk):
                yield StreamChunk(type="text", content="test", metadata={})

        handler = ConcreteHandler()
        token_usage = {"prompt_tokens": 10, "completion_tokens": 20}

        chunk = handler.create_done_chunk("stop", token_usage=token_usage)

        assert chunk.type == "done"
        assert chunk.metadata["token_usage"] == token_usage

    def test_handle_stream_chunk_is_abstract(self):
        """Test that handle_stream_chunk must be implemented."""
        # Can't instantiate abstract class directly
        with pytest.raises(TypeError):
            handler = BaseResponseHandler()
