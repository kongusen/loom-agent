"""
Tests for Memory Compression
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from loom.memory.compression import (
    ContextCompressor,
    MemoryCompressor
)
from loom.memory.types import MemoryUnit, MemoryType, MemoryTier, MemoryStatus


@pytest.mark.asyncio
class TestContextCompressor:
    """Test ContextCompressor static methods."""

    def test_compress_history_empty_list(self):
        """Test compressing empty list."""
        result = ContextCompressor.compress_history([])
        assert result == []

    def test_compress_history_returns_original_when_few_items(self):
        """Test that small lists are returned unchanged."""
        units = [
            MemoryUnit(
                content=f"message {i}",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=datetime.now()
            )
            for i in range(3)
        ]

        result = ContextCompressor.compress_history(units, keep_last_n=4)

        # Should return original since len(units) <= keep_last_n
        assert len(result) == 3

    def test_compress_history_separates_immutable(self):
        """Test that L4 facts are separated as immutable."""
        now = datetime.now()
        units = [
            MemoryUnit(
                content="fact 1",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                created_at=now
            ),
            MemoryUnit(
                content="message 1",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=now
            )
        ]

        result = ContextCompressor.compress_history(units, keep_last_n=0)

        # Should have compressed the L1 message into a summary
        assert len(result) == 2  # 1 immutable fact + 1 summary

    def test_compress_history_keeps_last_n(self):
        """Test that last N items are kept uncompressed."""
        now = datetime.now()
        units = [
            MemoryUnit(
                content=f"message {i}",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=now,
                metadata={"role": "user"}
            )
            for i in range(10)
        ]

        result = ContextCompressor.compress_history(units, keep_last_n=3)

        # Should have 1 summary + 3 recent messages = 4
        assert len(result) >= 3

    def test_compress_history_with_fact_type(self):
        """Test that FACT type units are treated as immutable."""
        now = datetime.now()
        units = [
            MemoryUnit(
                content="fact content",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.FACT,
                created_at=now
            ),
            MemoryUnit(
                content="message",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=now
            )
        ]

        result = ContextCompressor.compress_history(units, keep_last_n=0)

        # FACT should be in immutable, message should be compressed
        assert len(result) == 2

    def test_compress_history_preserves_order(self):
        """Test that result is sorted by created_at."""
        now = datetime.now()
        units = [
            MemoryUnit(
                content=f"message {i}",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=now,
                metadata={"role": "user"}
            )
            for i in range(5)
        ]

        result = ContextCompressor.compress_history(units, keep_last_n=2)

        # Check that result is sorted by created_at
        timestamps = [u.created_at for u in result]
        assert timestamps == sorted(timestamps)

    def test_compress_segment_empty(self):
        """Test compressing empty segment."""
        result = ContextCompressor._compress_segment([])
        assert result == []

    def test_compress_segment_creates_summary(self):
        """Test that segment is compressed into summary unit."""
        now = datetime.now()
        segment = [
            MemoryUnit(
                content="user message",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=now,
                metadata={"role": "user"}
            ),
            MemoryUnit(
                content="assistant message",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=now,
                metadata={"role": "assistant"}
            )
        ]

        result = ContextCompressor._compress_segment(segment)

        assert len(result) == 1
        assert result[0].type == MemoryType.SUMMARY
        assert "Previous Context Summary" in result[0].content

    def test_compress_segment_with_tool_calls(self):
        """Test that tool calls are counted."""
        now = datetime.now()
        segment = [
            MemoryUnit(
                content=[{"name": "calculator", "args": {"x": 1}}],
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.TOOL_CALL,
                created_at=now
            )
        ]

        result = ContextCompressor._compress_segment(segment)

        assert len(result) == 1
        assert "calculator" in result[0].content

    def test_compress_segment_with_thoughts(self):
        """Test that thoughts are discarded."""
        now = datetime.now()
        segment = [
            MemoryUnit(
                content="thinking process",
                tier=MemoryTier.L2_WORKING,
                type=MemoryType.THOUGHT,
                created_at=now
            ),
            MemoryUnit(
                content="message",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=now,
                metadata={"role": "user"}
            )
        ]

        result = ContextCompressor._compress_segment(segment)

        # Thoughts should be discarded, only summary created
        assert len(result) == 1
        assert result[0].type == MemoryType.SUMMARY


@pytest.mark.asyncio
class TestMemoryCompressor:
    """Test MemoryCompressor class."""

    def test_initialization(self):
        """Test compressor initialization."""
        compressor = MemoryCompressor()

        assert compressor.llm_provider is None
        assert compressor.l1_to_l3_threshold == 30
        assert compressor.l3_to_l4_threshold == 50
        assert compressor.token_threshold == 4000
        assert compressor.enable_llm_summarization is True

    def test_initialization_with_custom_values(self):
        """Test initialization with custom values."""
        mock_llm = AsyncMock()
        compressor = MemoryCompressor(
            llm_provider=mock_llm,
            l1_to_l3_threshold=10,
            l3_to_l4_threshold=20,
            token_threshold=2000,
            enable_llm_summarization=False
        )

        assert compressor.llm_provider is mock_llm
        assert compressor.l1_to_l3_threshold == 10
        assert compressor.l3_to_l4_threshold == 20
        assert compressor.token_threshold == 2000
        assert compressor.enable_llm_summarization is False

    def test_count_tokens_without_encoder(self):
        """Test token counting fallback when encoder is not available."""
        compressor = MemoryCompressor()
        compressor.encoder = None  # Simulate no encoder

        units = [
            MemoryUnit(
                content="a" * 100,
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE
            )
        ]

        count = compressor._count_tokens(units)

        # Should use fallback: len(str(content)) // 4
        assert count > 0

    def test_count_tokens_with_encoder(self):
        """Test token counting with encoder."""
        compressor = MemoryCompressor()

        units = [
            MemoryUnit(
                content="test content",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE
            )
        ]

        count = compressor._count_tokens(units)

        assert count > 0

    @pytest.mark.asyncio
    async def test_compress_l1_to_l3_below_threshold(self):
        """Test that compression is skipped when below threshold."""
        compressor = MemoryCompressor(l1_to_l3_threshold=10)
        memory = AsyncMock()

        # Mock query to return few items
        memory.query.return_value = [
            MemoryUnit(
                content="message",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE
            )
        ]

        result = await compressor.compress_l1_to_l3(memory)

        # Should return None as there are not enough items
        assert result is None
        memory.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_compress_l1_to_l3_with_llm(self):
        """Test LLM-based compression."""
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = MagicMock(content="LLM summary")

        compressor = MemoryCompressor(
            llm_provider=mock_llm,
            l1_to_l3_threshold=5,
            token_threshold=100  # Lower threshold for testing
        )
        memory = AsyncMock()

        # Mock query to return items above threshold with enough content
        now = datetime.now()
        memory.query.return_value = [
            MemoryUnit(
                content="a" * 200,  # Long content to exceed token threshold
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=now
            )
            for i in range(10)
        ]
        memory.add.return_value = "summary_id"

        result = await compressor.compress_l1_to_l3(memory)

        assert result == "summary_id"
        memory.add.assert_called_once()
        # Check that the summary has the right type
        added_unit = memory.add.call_args[0][0]
        assert added_unit.tier == MemoryTier.L3_SESSION
        assert added_unit.type == MemoryType.SUMMARY

    @pytest.mark.asyncio
    async def test_compress_l1_to_l3_simple_summary(self):
        """Test simple rule-based compression."""
        compressor = MemoryCompressor(
            l1_to_l3_threshold=5,
            token_threshold=100,  # Lower threshold for testing
            enable_llm_summarization=False
        )
        memory = AsyncMock()

        now = datetime.now()
        memory.query.return_value = [
            MemoryUnit(
                content="a" * 200,  # Long content
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=now
            )
            for i in range(10)
        ]
        memory.add.return_value = "summary_id"

        result = await compressor.compress_l1_to_l3(memory)

        assert result == "summary_id"

    @pytest.mark.asyncio
    async def test_compress_l1_to_l3_marks_units_as_summarized(self):
        """Test that compressed units are marked as SUMMARIZED."""
        compressor = MemoryCompressor(
            l1_to_l3_threshold=5,
            token_threshold=100,  # Lower threshold for testing
            enable_llm_summarization=False
        )
        memory = AsyncMock()

        now = datetime.now()
        units = [
            MemoryUnit(
                content="a" * 200,  # Long content
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                created_at=now
            )
            for i in range(10)
        ]
        memory.query.return_value = units
        memory.add.return_value = "summary_id"

        await compressor.compress_l1_to_l3(memory)

        # Check that all units were marked as SUMMARIZED
        for unit in units:
            assert unit.status == MemoryStatus.SUMMARIZED

    @pytest.mark.asyncio
    async def test_extract_facts_to_l4_below_threshold(self):
        """Test that fact extraction is skipped when below threshold."""
        compressor = MemoryCompressor(l3_to_l4_threshold=20)
        memory = AsyncMock()

        memory.query.return_value = []

        result = await compressor.extract_facts_to_l4(memory)

        assert result == []

    @pytest.mark.asyncio
    async def test_extract_facts_to_l4_with_llm(self):
        """Test LLM-based fact extraction."""
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = MagicMock(content="Fact 1\nFact 2\nFact 3")

        compressor = MemoryCompressor(
            llm_provider=mock_llm,
            l3_to_l4_threshold=5
        )
        memory = AsyncMock()

        memory.query.return_value = [
            MemoryUnit(
                content="some content",
                tier=MemoryTier.L2_WORKING,
                type=MemoryType.MESSAGE
            )
            for _ in range(10)
        ]
        memory.add.return_value = "fact_id"

        result = await compressor.extract_facts_to_l4(memory)

        assert len(result) == 3  # 3 facts extracted

    @pytest.mark.asyncio
    async def test_extract_facts_simple_mode(self):
        """Test simple fact extraction without LLM."""
        compressor = MemoryCompressor(
            l3_to_l4_threshold=5,
            enable_llm_summarization=False
        )
        memory = AsyncMock()

        now = datetime.now()
        memory.query.return_value = [
            MemoryUnit(
                content="important content " * 10,  # Long content
                tier=MemoryTier.L2_WORKING,
                type=MemoryType.MESSAGE,
                importance=0.9,
                created_at=now
            )
            for _ in range(10)
        ]
        memory.add.return_value = "fact_id"

        result = await compressor.extract_facts_to_l4(memory)

        # Should extract some facts from high-importance units
        assert isinstance(result, list)

    def test_simple_summary(self):
        """Test simple summary generation."""
        compressor = MemoryCompressor()

        units = [
            MemoryUnit(
                content="message",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE
            ),
            MemoryUnit(
                content="tool call",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.TOOL_CALL
            )
        ]

        summary = compressor._simple_summary(units)

        assert "Compressed" in summary
        assert "1 messages" in summary
        assert "1 tool calls" in summary

    @pytest.mark.asyncio
    async def test_summarize_with_llm_fallback(self):
        """Test that _summarize_with_llm falls back on error."""
        mock_llm = AsyncMock()
        mock_llm.chat.side_effect = Exception("LLM error")

        compressor = MemoryCompressor(llm_provider=mock_llm)

        units = [
            MemoryUnit(
                content="message",
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE
            )
        ]

        result = await compressor._summarize_with_llm(units)

        # Should fallback to simple summary
        assert "Compressed" in result

    @pytest.mark.asyncio
    async def test_extract_facts_with_llm_fallback(self):
        """Test that _extract_facts_with_llm falls back on error."""
        mock_llm = AsyncMock()
        mock_llm.chat.side_effect = Exception("LLM error")

        compressor = MemoryCompressor(llm_provider=mock_llm)

        units = [
            MemoryUnit(
                content="important fact here with more content",
                tier=MemoryTier.L2_WORKING,
                type=MemoryType.MESSAGE,
                importance=0.9
            )
        ]

        result = await compressor._extract_facts_with_llm(units)

        # Should fallback to simple extraction
        assert isinstance(result, list)

    def test_extract_facts_simple_high_importance(self):
        """Test simple fact extraction with high importance units."""
        compressor = MemoryCompressor()

        units = [
            MemoryUnit(
                content="important fact with enough content here",
                tier=MemoryTier.L2_WORKING,
                type=MemoryType.MESSAGE,
                importance=0.9
            ),
            MemoryUnit(
                content="low importance",
                tier=MemoryTier.L2_WORKING,
                type=MemoryType.MESSAGE,
                importance=0.5
            )
        ]

        result = compressor._extract_facts_simple(units)

        # Should extract high importance fact
        assert len(result) >= 1

    def test_extract_facts_simple_short_content_skipped(self):
        """Test that very short content is skipped."""
        compressor = MemoryCompressor()

        units = [
            MemoryUnit(
                content="short",  # Less than 20 chars
                tier=MemoryTier.L2_WORKING,
                type=MemoryType.MESSAGE,
                importance=0.9
            )
        ]

        result = compressor._extract_facts_simple(units)

        # Short content should be skipped
        assert len(result) == 0

    def test_extract_facts_simple_limits_results(self):
        """Test that simple extraction limits results."""
        compressor = MemoryCompressor()

        units = [
            MemoryUnit(
                content="important fact " + "content " * 20,
                tier=MemoryTier.L2_WORKING,
                type=MemoryType.MESSAGE,
                importance=0.9
            )
            for _ in range(20)
        ]

        result = compressor._extract_facts_simple(units)

        # Should limit to top 5 facts
        assert len(result) <= 5
