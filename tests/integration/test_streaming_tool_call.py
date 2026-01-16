"""
Unit test for streaming tool call aggregation in OpenAI provider.

This test verifies the fix for the issue where tool_calls chunks in streaming
mode had null IDs, causing "Invalid type for 'messages[2].tool_calls[1].id':
expected a string, but got null instead." error.
"""

from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from loom.config import LLMConfig
from loom.llm import OpenAIProvider, StreamChunk

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def set_dummy_api_key(monkeypatch):
    """Set dummy API key for all tests in this module."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key")


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()
    return client


@pytest.fixture
def provider(mock_openai_client):
    """Create an OpenAIProvider with mocked client."""
    provider = OpenAIProvider(config=LLMConfig())
    provider.client = mock_openai_client
    return provider


@dataclass
class MockToolCall:
    """Mock OpenAI tool call chunk."""
    index: int
    id: str | None = None
    name: str | None = None
    arguments: str | None = None

    def to_mock(self):
        """Convert to unittest.mock.Mock object."""
        mock_tc = Mock()
        mock_tc.index = self.index
        mock_tc.id = self.id
        mock_tc.function = Mock()
        mock_tc.function.name = self.name
        mock_tc.function.arguments = self.arguments
        return mock_tc


@dataclass
class MockOpenAIChunk:
    """Mock OpenAI stream chunk."""
    content: str | None = None
    tool_calls: list[MockToolCall] = field(default_factory=list)
    finish_reason: str | None = None

    def to_mock(self):
        """Convert to unittest.mock.Mock object."""
        mock_chunk = Mock()
        mock_chunk.choices = [Mock()]
        mock_chunk.choices[0].delta = Mock()
        mock_chunk.choices[0].delta.content = self.content
        mock_chunk.choices[0].delta.tool_calls = [
            tc.to_mock() for tc in self.tool_calls
        ]
        mock_chunk.choices[0].finish_reason = self.finish_reason
        return mock_chunk


def create_mock_stream(chunks: list[MockOpenAIChunk], mock_client: MagicMock):
    """
    Configure a mock client to return the specified chunks.

    Args:
        chunks: List of MockOpenAIChunk objects to yield
        mock_client: The mock OpenAI client to configure
    """
    mock_response = MagicMock()

    async def mock_iter():
        for chunk in chunks:
            yield chunk.to_mock()

    mock_response.__aiter__ = lambda self: mock_iter()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)


# =============================================================================
# Helper Functions for Assertions
# =============================================================================

def assert_tool_call_equal(
    actual_chunk: StreamChunk,
    expected_id: str,
    expected_name: str,
    expected_arguments: str,
    msg: str = ""
):
    """Assert that a tool_call StreamChunk has the expected values."""
    assert actual_chunk.type == "tool_call", f"{msg}: Expected type 'tool_call', got '{actual_chunk.type}'"
    assert actual_chunk.content["id"] == expected_id, f"{msg}: Expected id '{expected_id}', got '{actual_chunk.content.get('id')}'"
    assert actual_chunk.content["name"] == expected_name, f"{msg}: Expected name '{expected_name}', got '{actual_chunk.content.get('name')}'"
    assert actual_chunk.content["arguments"] == expected_arguments, f"{msg}: Expected arguments '{expected_arguments}', got '{actual_chunk.content.get('arguments')}'"


def assert_text_chunk(actual_chunk: StreamChunk, expected_content: str, msg: str = ""):
    """Assert that a text StreamChunk has the expected content."""
    assert actual_chunk.type == "text", f"{msg}: Expected type 'text', got '{actual_chunk.type}'"
    assert actual_chunk.content == expected_content, f"{msg}: Expected content '{expected_content}', got '{actual_chunk.content}'"


# =============================================================================
# Test Cases
# =============================================================================

@pytest.mark.asyncio
async def test_single_tool_call_aggregation(provider, mock_openai_client):
    """
    Test that a single tool call is properly aggregated from multiple chunks.

    Simulates OpenAI's streaming behavior:
    - Chunk 1: tool_call with id and name, but no arguments yet
    - Chunk 2: tool_call with first part of arguments (id=None)
    - Chunk 3: tool_call with rest of arguments (id=None)
    - Chunk 4: finish_reason triggers yielding the aggregated tool_call
    """
    chunks = [
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, id="call_abc123", name="test_tool")]
        ),
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, arguments='{"arg1":')]
        ),
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, arguments=' "value1"}')]
        ),
        MockOpenAIChunk(finish_reason="tool_calls"),
    ]

    create_mock_stream(chunks, mock_openai_client)

    collected_chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "test"}],
        tools=[{"name": "test_tool", "description": "Test", "inputSchema": {}}]
    ):
        collected_chunks.append(chunk)

    # Verify: 1 tool_call_start + 1 tool_call_complete + 1 done chunk
    assert len(collected_chunks) == 3, f"Expected 3 chunks, got {len(collected_chunks)}"
    assert collected_chunks[0].type == "tool_call_start"
    assert collected_chunks[0].content['id'] == "call_abc123"
    assert collected_chunks[0].content['name'] == "test_tool"
    assert collected_chunks[1].type == "tool_call_complete"
    assert collected_chunks[1].content['arguments'] == '{"arg1": "value1"}'
    assert collected_chunks[2].type == "done"


@pytest.mark.asyncio
async def test_multiple_parallel_tool_calls(provider, mock_openai_client):
    """Test that multiple parallel tool calls are properly aggregated."""
    chunks = [
        # Both tool_calls get their ids and names
        MockOpenAIChunk(
            tool_calls=[
                MockToolCall(index=0, id="call_abc123", name="tool_a"),
                MockToolCall(index=1, id="call_def456", name="tool_b"),
            ]
        ),
        # First tool_call gets arguments
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, arguments='{"x":1}')]
        ),
        # Second tool_call gets arguments
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=1, arguments='{"y":2}')]
        ),
        MockOpenAIChunk(finish_reason="tool_calls"),
    ]

    create_mock_stream(chunks, mock_openai_client)

    collected_chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "test"}],
        tools=[
            {"name": "tool_a", "description": "Tool A", "inputSchema": {}},
            {"name": "tool_b", "description": "Tool B", "inputSchema": {}},
        ]
    ):
        collected_chunks.append(chunk)

    # Verify: 2 tool_call_start + 2 tool_call_complete + 1 done chunk
    assert len(collected_chunks) == 5, f"Expected 5 chunks, got {len(collected_chunks)}"
    assert collected_chunks[0].type == "tool_call_start"
    assert collected_chunks[0].content['id'] == "call_abc123"
    assert collected_chunks[0].content['name'] == "tool_a"
    assert collected_chunks[1].type == "tool_call_start"
    assert collected_chunks[1].content['id'] == "call_def456"
    assert collected_chunks[1].content['name'] == "tool_b"
    assert collected_chunks[2].type == "tool_call_complete"
    assert collected_chunks[2].content['arguments'] == '{"x":1}'
    assert collected_chunks[3].type == "tool_call_complete"
    assert collected_chunks[3].content['arguments'] == '{"y":2}'
    assert collected_chunks[4].type == "done"


@pytest.mark.asyncio
async def test_text_and_tool_calls_mixed(provider, mock_openai_client):
    """Test that text content and tool calls are both handled correctly."""
    chunks = [
        MockOpenAIChunk(content="I'll help you with "),
        MockOpenAIChunk(content="that task. "),
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, id="call_xyz", name="search")]
        ),
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, arguments='{"q":"test"}')]
        ),
        MockOpenAIChunk(finish_reason="tool_calls"),
    ]

    create_mock_stream(chunks, mock_openai_client)

    collected_chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "test"}],
        tools=[{"name": "search", "description": "Search", "inputSchema": {}}]
    ):
        collected_chunks.append(chunk)

    # Verify: 2 text chunks + 1 tool_call_start + 1 tool_call_complete + 1 done chunk
    assert len(collected_chunks) == 5, f"Expected 5 chunks, got {len(collected_chunks)}"
    assert_text_chunk(collected_chunks[0], "I'll help you with ")
    assert_text_chunk(collected_chunks[1], "that task. ")
    assert collected_chunks[2].type == "tool_call_start"
    assert collected_chunks[2].content['id'] == "call_xyz"
    assert collected_chunks[2].content['name'] == "search"
    assert collected_chunks[3].type == "tool_call_complete"
    assert collected_chunks[3].content['arguments'] == '{"q":"test"}'
    assert collected_chunks[4].type == "done"


@pytest.mark.asyncio
async def test_empty_arguments_stream(provider, mock_openai_client):
    """Test tool call with no arguments (edge case)."""
    chunks = [
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, id="call_empty", name="no_args_tool")]
        ),
        MockOpenAIChunk(finish_reason="tool_calls"),
    ]

    create_mock_stream(chunks, mock_openai_client)

    collected_chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "test"}],
        tools=[{"name": "no_args_tool", "description": "No args", "inputSchema": {}}]
    ):
        collected_chunks.append(chunk)

    # Tool call with empty arguments should still be yielded
    assert len(collected_chunks) == 3, f"Expected 3 chunks, got {len(collected_chunks)}"
    assert collected_chunks[0].type == "tool_call_start"
    assert collected_chunks[0].content["id"] == "call_empty"
    # When no arguments are provided, the framework returns an error chunk
    assert collected_chunks[1].type == "error"
    assert collected_chunks[2].type == "done"


@pytest.mark.asyncio
async def test_text_only_stream_no_tools(provider, mock_openai_client):
    """Test streaming with only text content, no tool calls."""
    chunks = [
        MockOpenAIChunk(content="Hello, "),
        MockOpenAIChunk(content="world!"),
        MockOpenAIChunk(finish_reason="stop"),
    ]

    create_mock_stream(chunks, mock_openai_client)

    collected_chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "test"}],
        tools=None  # No tools provided
    ):
        collected_chunks.append(chunk)

    # Should only have text chunks + done chunk
    assert len(collected_chunks) == 3, f"Expected 3 chunks, got {len(collected_chunks)}"
    assert_text_chunk(collected_chunks[0], "Hello, ")
    assert_text_chunk(collected_chunks[1], "world!")
    assert collected_chunks[2].type == "done"
    assert collected_chunks[2].metadata["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_tool_call_id_is_never_null(provider, mock_openai_client):
    """
    Critical test: Ensure tool_call.id is never None in the output.

    This is the core bug being fixed - previously, chunks with id=None
    were being yielded, causing OpenAI API errors.
    """
    chunks = [
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, id="call_123", name="test")]
        ),
        # This chunk has id=None - should NOT be yielded directly
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, id=None, arguments='{"a":')]
        ),
        # This chunk also has id=None - should NOT be yielded directly
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, id=None, arguments=' "b"}')]
        ),
        MockOpenAIChunk(finish_reason="tool_calls"),
    ]

    create_mock_stream(chunks, mock_openai_client)

    collected_chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "test"}],
        tools=[{"name": "test", "description": "Test", "inputSchema": {}}]
    ):
        collected_chunks.append(chunk)

    # The aggregated tool_call_complete should have a valid id (not None or empty)
    tool_call_start_chunk = collected_chunks[0]
    tool_call_complete_chunk = collected_chunks[1]
    assert tool_call_start_chunk.type == "tool_call_start"
    assert tool_call_start_chunk.content["id"] == "call_123", "Tool call id must not be null"
    assert tool_call_start_chunk.content["id"] != "", "Tool call id must not be empty"
    assert tool_call_complete_chunk.type == "tool_call_complete"
    assert tool_call_complete_chunk.content["id"] == "call_123"
    assert tool_call_complete_chunk.content["arguments"] == '{"a": "b"}'


@pytest.mark.asyncio
async def test_complex_json_arguments(provider, mock_openai_client):
    """Test tool call with complex nested JSON arguments."""
    chunks = [
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, id="call_complex", name="complex_tool")]
        ),
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, arguments='{"nested": {"key": "value"}, "array": [1, 2]}')]
        ),
        MockOpenAIChunk(finish_reason="tool_calls"),
    ]

    create_mock_stream(chunks, mock_openai_client)

    collected_chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "test"}],
        tools=[{"name": "complex_tool", "description": "Complex", "inputSchema": {}}]
    ):
        collected_chunks.append(chunk)

    # Check tool_call_start and tool_call_complete
    assert collected_chunks[0].type == "tool_call_start"
    assert collected_chunks[0].content['id'] == "call_complex"
    assert collected_chunks[0].content['name'] == "complex_tool"
    assert collected_chunks[1].type == "tool_call_complete"
    assert collected_chunks[1].content['arguments'] == '{"nested": {"key": "value"}, "array": [1, 2]}'


@pytest.mark.asyncio
async def test_unicode_in_arguments(provider, mock_openai_client):
    """Test tool call with unicode characters in arguments."""
    chunks = [
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, id="call_unicode", name="unicode_tool")]
        ),
        MockOpenAIChunk(
            tool_calls=[MockToolCall(index=0, arguments='{"text": "Hello 世界 🌍"}')]
        ),
        MockOpenAIChunk(finish_reason="tool_calls"),
    ]

    create_mock_stream(chunks, mock_openai_client)

    collected_chunks = []
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "test"}],
        tools=[{"name": "unicode_tool", "description": "Unicode", "inputSchema": {}}]
    ):
        collected_chunks.append(chunk)

    # Check tool_call_start and tool_call_complete
    assert collected_chunks[0].type == "tool_call_start"
    assert collected_chunks[0].content['id'] == "call_unicode"
    assert collected_chunks[0].content['name'] == "unicode_tool"
    assert collected_chunks[1].type == "tool_call_complete"
    assert collected_chunks[1].content['arguments'] == '{"text": "Hello 世界 🌍"}'
