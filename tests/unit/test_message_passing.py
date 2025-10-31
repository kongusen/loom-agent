"""
Unit tests for Phase 3: Context Management - Message Passing Optimization

Tests the enhanced message preparation system for tt recursion.
"""

import pytest
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock

from loom.core.agent_executor import AgentExecutor
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.events import ToolResult
from loom.core.types import Message
from loom.interfaces.llm import BaseLLM
from loom.interfaces.compressor import BaseCompressor
from loom.utils.token_counter import count_messages_tokens


# ===== Mock Components =====

class MockLLM(BaseLLM):
    """Mock LLM for testing"""

    @property
    def model_name(self) -> str:
        return "mock-llm"

    async def generate(self, messages: List[Dict]) -> str:
        return "Mock response"

    async def stream(self, messages):
        yield "Mock"

    async def generate_with_tools(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        return {"content": "Mock response", "tool_calls": []}


class MockCompressor(BaseCompressor):
    """Mock compressor for testing"""

    def should_compress(self, current_tokens: int, max_tokens: int) -> bool:
        return current_tokens > max_tokens

    async def compress(self, messages: List[Message]):
        """Simulate compression by keeping only first and last message"""
        if len(messages) <= 2:
            return messages, MagicMock()

        compressed = [messages[0], messages[-1]]
        metadata = MagicMock()
        metadata.original_tokens = count_messages_tokens(messages)
        metadata.compressed_tokens = count_messages_tokens(compressed)
        metadata.compression_ratio = 0.5
        metadata.original_message_count = len(messages)
        metadata.compressed_message_count = len(compressed)
        metadata.key_topics = ["test"]

        return compressed, metadata


# ===== Tests =====

class TestMessagePassingOptimization:
    """Test suite for Phase 3 message passing optimization"""

    @pytest.mark.asyncio
    async def test_basic_message_preparation(self):
        """Test basic message preparation includes tool results"""
        llm = MockLLM()
        executor = AgentExecutor(llm=llm, tools={})

        messages = [Message(role="user", content="Do something")]
        tool_results = [
            ToolResult(
                tool_call_id="call_1",
                tool_name="search",
                content="Search result: Found data"
            )
        ]
        turn_state = TurnState.initial(max_iterations=10)
        context = ExecutionContext.create()

        # Prepare recursive messages
        next_messages = await executor._prepare_recursive_messages(
            messages, tool_results, turn_state, context
        )

        # Should have guidance message + tool result message
        assert len(next_messages) >= 2

        # Check tool result is included
        tool_messages = [m for m in next_messages if m.role == "tool"]
        assert len(tool_messages) == 1
        assert tool_messages[0].content == "Search result: Found data"
        assert tool_messages[0].tool_call_id == "call_1"

    @pytest.mark.asyncio
    async def test_multiple_tool_results(self):
        """Test handling multiple tool results"""
        llm = MockLLM()
        executor = AgentExecutor(llm=llm, tools={})

        messages = [Message(role="user", content="Complex task")]
        tool_results = [
            ToolResult(tool_call_id="call_1", tool_name="search", content="Result 1"),
            ToolResult(tool_call_id="call_2", tool_name="analyze", content="Result 2"),
            ToolResult(tool_call_id="call_3", tool_name="calculate", content="Result 3"),
        ]
        turn_state = TurnState.initial()
        context = ExecutionContext.create()

        next_messages = await executor._prepare_recursive_messages(
            messages, tool_results, turn_state, context
        )

        # All tool results should be included
        tool_messages = [m for m in next_messages if m.role == "tool"]
        assert len(tool_messages) == 3

        # Check order is preserved
        assert tool_messages[0].content == "Result 1"
        assert tool_messages[1].content == "Result 2"
        assert tool_messages[2].content == "Result 3"

    @pytest.mark.asyncio
    async def test_recursion_depth_hint(self):
        """Test that recursion hint is added at depth > 3"""
        llm = MockLLM()
        executor = AgentExecutor(llm=llm, tools={})

        messages = [Message(role="user", content="Task")]
        tool_results = [
            ToolResult(tool_call_id="call_1", tool_name="tool", content="Result")
        ]

        # Test at depth 3 (no hint)
        turn_state_3 = TurnState.initial().next_turn().next_turn().next_turn()
        context = ExecutionContext.create()

        next_messages_3 = await executor._prepare_recursive_messages(
            messages, tool_results, turn_state_3, context
        )

        system_messages_3 = [m for m in next_messages_3 if m.role == "system"]
        assert len(system_messages_3) == 0, "No hint at depth 3"

        # Test at depth 4 (hint should be added)
        turn_state_4 = turn_state_3.next_turn()
        next_messages_4 = await executor._prepare_recursive_messages(
            messages, tool_results, turn_state_4, context
        )

        system_messages_4 = [m for m in next_messages_4 if m.role == "system"]
        assert len(system_messages_4) == 1, "Hint should be added at depth 4"

        # Check hint content
        hint = system_messages_4[0]
        assert "Recursion Status" in hint.content or "Depth" in hint.content

    @pytest.mark.asyncio
    async def test_context_length_checking_no_compression(self):
        """Test that context length is checked but no compression if under limit"""
        llm = MockLLM()
        # Set high max_context_tokens to avoid compression
        executor = AgentExecutor(llm=llm, tools={}, max_context_tokens=100000)

        messages = [Message(role="user", content="Short message")]
        tool_results = [
            ToolResult(tool_call_id="call_1", tool_name="tool", content="Short result")
        ]
        turn_state = TurnState.initial()
        context = ExecutionContext.create()

        next_messages = await executor._prepare_recursive_messages(
            messages, tool_results, turn_state, context
        )

        # Should not trigger compression
        assert "last_compression" not in context.metadata

    @pytest.mark.asyncio
    async def test_automatic_compression_when_needed(self):
        """Test automatic compression when context exceeds limit"""
        llm = MockLLM()
        compressor = MockCompressor()

        # Set low max_context_tokens to trigger compression
        executor = AgentExecutor(
            llm=llm,
            tools={},
            compressor=compressor,
            max_context_tokens=100  # Very low to trigger compression
        )

        # Create messages that will exceed token limit
        long_content = "x" * 1000  # Long message to exceed limit
        messages = [Message(role="user", content="Task")]
        tool_results = [
            ToolResult(tool_call_id=f"call_{i}", tool_name="tool", content=long_content)
            for i in range(5)
        ]
        turn_state = TurnState.initial()
        context = ExecutionContext.create()

        next_messages = await executor._prepare_recursive_messages(
            messages, tool_results, turn_state, context
        )

        # Compression should have been triggered
        assert "last_compression" in context.metadata
        comp_info = context.metadata["last_compression"]
        assert "tokens_before" in comp_info
        assert "tokens_after" in comp_info
        assert comp_info["tokens_before"] > comp_info["tokens_after"]

    @pytest.mark.asyncio
    async def test_no_compression_without_compressor(self):
        """Test that no compression happens if compressor is not configured"""
        llm = MockLLM()
        # No compressor configured
        executor = AgentExecutor(
            llm=llm,
            tools={},
            compressor=None,
            max_context_tokens=10  # Very low limit
        )

        long_content = "x" * 1000
        messages = [Message(role="user", content="Task")]
        tool_results = [
            ToolResult(tool_call_id=f"call_{i}", tool_name="tool", content=long_content)
            for i in range(5)
        ]
        turn_state = TurnState.initial()
        context = ExecutionContext.create()

        next_messages = await executor._prepare_recursive_messages(
            messages, tool_results, turn_state, context
        )

        # No compression should happen
        assert "last_compression" not in context.metadata

    @pytest.mark.asyncio
    async def test_token_estimation(self):
        """Test token estimation utility"""
        llm = MockLLM()
        executor = AgentExecutor(llm=llm, tools={})

        # Test with various message lengths
        short_messages = [Message(role="user", content="Hi")]
        long_messages = [
            Message(role="user", content="x" * 1000),
            Message(role="assistant", content="y" * 1000),
        ]

        short_tokens = executor._estimate_tokens(short_messages)
        long_tokens = executor._estimate_tokens(long_messages)

        # Long messages should have more tokens
        assert long_tokens > short_tokens
        assert long_tokens > 400  # ~2000 chars / 4 = ~500 tokens

    @pytest.mark.asyncio
    async def test_build_recursion_hint(self):
        """Test recursion hint generation"""
        llm = MockLLM()
        executor = AgentExecutor(llm=llm, tools={})

        hint = executor._build_recursion_hint(current_depth=5, max_depth=10)

        # Check hint contains key information
        assert "5/10" in hint or "5" in hint and "10" in hint
        assert "50" in hint or "50%" in hint  # Progress percentage
        assert "5" in hint  # Remaining iterations

    @pytest.mark.asyncio
    async def test_tool_result_metadata_preserved(self):
        """Test that tool result metadata is preserved"""
        llm = MockLLM()
        executor = AgentExecutor(llm=llm, tools={})

        messages = [Message(role="user", content="Task")]
        tool_results = [
            ToolResult(
                tool_call_id="call_1",
                tool_name="search",
                content="Result",
                metadata={"source": "database", "confidence": 0.95}
            )
        ]
        turn_state = TurnState.initial()
        context = ExecutionContext.create()

        next_messages = await executor._prepare_recursive_messages(
            messages, tool_results, turn_state, context
        )

        tool_message = [m for m in next_messages if m.role == "tool"][0]
        assert tool_message.metadata is not None
        assert tool_message.metadata.get("source") == "database"
        assert tool_message.metadata.get("confidence") == 0.95

    @pytest.mark.asyncio
    async def test_empty_tool_results(self):
        """Test handling of empty tool results list"""
        llm = MockLLM()
        executor = AgentExecutor(llm=llm, tools={})

        messages = [Message(role="user", content="Task")]
        tool_results = []  # No tool results
        turn_state = TurnState.initial()
        context = ExecutionContext.create()

        next_messages = await executor._prepare_recursive_messages(
            messages, tool_results, turn_state, context
        )

        # Should still have guidance message, no tool messages
        assert len(next_messages) >= 1
        tool_messages = [m for m in next_messages if m.role == "tool"]
        assert len(tool_messages) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
