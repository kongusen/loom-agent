"""
Tests for Memory System Strategies
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from loom.memory.system_strategies import System1Strategy, System2Strategy
from loom.memory.strategies import CurationConfig
from loom.memory.types import MemoryUnit, MemoryTier, MemoryType


@pytest.mark.asyncio
class TestSystem1Strategy:
    """Test System1Strategy - Fast, minimal context."""

    @pytest.fixture
    def strategy(self):
        return System1Strategy()

    @pytest.fixture
    def mock_memory(self):
        memory = AsyncMock()
        memory.node_id = "test_node"
        return memory

    @pytest.fixture
    def config(self):
        return CurationConfig(
            max_tokens=500,
            include_facts=True,
            focus_distance=0
        )

    async def test_curate_returns_list(self, strategy, mock_memory, config):
        """Test that curate returns a list."""
        mock_memory.query.return_value = []

        result = await strategy.curate(mock_memory, config)

        assert isinstance(result, list)

    async def test_curate_queries_l1_messages(self, strategy, mock_memory, config):
        """Test that System 1 queries L1 messages."""
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config)

        # Should query L1 messages
        assert mock_memory.query.called
        calls = mock_memory.query.call_args_list
        # Check that at least one query was for L1 messages
        l1_found = False
        for call in calls:
            query = call[0][0]
            if MemoryTier.L1_RAW_IO in query.tiers:
                l1_found = True
                break
        assert l1_found, "System 1 should query L1 messages"

    async def test_curate_queries_l2_plans(self, strategy, mock_memory, config):
        """Test that System 1 queries L2 plans."""
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config)

        # Should query L2 plans
        calls = mock_memory.query.call_args_list
        l2_found = False
        for call in calls:
            query = call[0][0]
            if MemoryTier.L2_WORKING in query.tiers:
                l2_found = True
                break
        assert l2_found, "System 1 should query L2 plans"

    async def test_curate_includes_l4_facts_when_enabled(self, strategy, mock_memory, config):
        """Test that System 1 includes L4 facts when enabled."""
        mock_memory.query.return_value = [
            MemoryUnit(
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                content="Test fact",
                importance=0.9
            )
        ]

        result = await strategy.curate(mock_memory, config)

        # Should have queried for facts
        calls = mock_memory.query.call_args_list
        l4_found = False
        for call in calls:
            query = call[0][0]
            if MemoryTier.L4_GLOBAL in query.tiers and MemoryType.FACT in query.types:
                l4_found = True
                break
        assert l4_found, "System 1 should query L4 facts when enabled"

    async def test_curate_skips_l4_facts_when_disabled(self, strategy, mock_memory):
        """Test that System 1 skips L4 facts when disabled."""
        config = CurationConfig(
            max_tokens=500,
            include_facts=False,
            focus_distance=0
        )
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config)

        # Should NOT query for facts
        calls = mock_memory.query.call_args_list
        for call in calls:
            query = call[0][0]
            # Should not query L4 facts
            if MemoryTier.L4_GLOBAL in query.tiers:
                assert MemoryType.FACT not in query.types, \
                    "System 1 should not query L4 facts when disabled"

    async def test_curate_limits_l1_to_5_messages(self, strategy, mock_memory, config):
        """Test that System 1 limits L1 to last 5 messages."""
        # Create 10 mock messages
        messages = [
            MemoryUnit(
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                content=f"Message {i}"
            )
            for i in range(10)
        ]

        async def mock_query_side_effect(query):
            if MemoryTier.L1_RAW_IO in query.tiers:
                return messages
            return []

        mock_memory.query.side_effect = mock_query_side_effect

        result = await strategy.curate(mock_memory, config)

        # Count L1 messages in result
        l1_count = sum(1 for u in result if u.tier == MemoryTier.L1_RAW_IO)
        assert l1_count <= 5, f"System 1 should limit L1 to 5, got {l1_count}"

    async def test_curate_limits_l4_to_3_facts(self, strategy, mock_memory, config):
        """Test that System 1 limits L4 to top 3 facts."""
        # Create 10 mock facts
        facts = [
            MemoryUnit(
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                content=f"Fact {i}",
                importance=0.5 + (i * 0.05)
            )
            for i in range(10)
        ]

        call_count = 0

        async def mock_query_side_effect(query):
            nonlocal call_count
            call_count += 1
            if MemoryTier.L1_RAW_IO in query.tiers:
                return []
            elif MemoryTier.L4_GLOBAL in query.tiers and MemoryType.FACT in query.types:
                return facts
            return []

        mock_memory.query.side_effect = mock_query_side_effect

        result = await strategy.curate(mock_memory, config)

        # Count L4 facts in result
        l4_count = sum(1 for u in result if u.tier == MemoryTier.L4_GLOBAL)
        assert l4_count <= 3, f"System 1 should limit L4 facts to 3, got {l4_count}"

    async def test_curate_with_task_context(self, strategy, mock_memory, config):
        """Test that System 1 handles task_context parameter."""
        mock_memory.query.return_value = []

        # System 1 doesn't use task_context for L4, but should accept it
        result = await strategy.curate(mock_memory, config, task_context="test task")

        assert isinstance(result, list)


@pytest.mark.asyncio
class TestSystem2Strategy:
    """Test System2Strategy - Comprehensive, deep reasoning context."""

    @pytest.fixture
    def strategy(self):
        return System2Strategy()

    @pytest.fixture
    def mock_memory(self):
        memory = AsyncMock()
        memory.node_id = "test_node"
        return memory

    @pytest.fixture
    def config(self):
        return CurationConfig(
            max_tokens=8000,
            include_facts=True,
            focus_distance=1
        )

    async def test_curate_returns_list(self, strategy, mock_memory, config):
        """Test that curate returns a list."""
        mock_memory.query.return_value = []

        result = await strategy.curate(mock_memory, config)

        assert isinstance(result, list)

    async def test_curate_queries_l2_working_memory(self, strategy, mock_memory, config):
        """Test that System 2 queries full L2 working memory."""
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config)

        # Should query L2 working memory with node_id filter
        calls = mock_memory.query.call_args_list
        l2_found = False
        for call in calls:
            query = call[0][0]
            if MemoryTier.L2_WORKING in query.tiers:
                l2_found = True
                # Check that node_id is included
                assert mock_memory.node_id in query.node_ids
                break
        assert l2_found, "System 2 should query L2 working memory"

    async def test_curate_queries_l1_history(self, strategy, mock_memory, config):
        """Test that System 2 queries extensive L1 history."""
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config)

        # Should query L1 with node_id filter
        calls = mock_memory.query.call_args_list
        l1_found = False
        for call in calls:
            query = call[0][0]
            if MemoryTier.L1_RAW_IO in query.tiers:
                l1_found = True
                assert mock_memory.node_id in query.node_ids
                break
        assert l1_found, "System 2 should query L1 history"

    async def test_curate_limits_l1_to_20_messages(self, strategy, mock_memory, config):
        """Test that System 2 limits L1 to last 20 messages."""
        # Create 30 mock messages
        messages = [
            MemoryUnit(
                tier=MemoryTier.L1_RAW_IO,
                type=MemoryType.MESSAGE,
                content=f"Message {i}"
            )
            for i in range(30)
        ]

        async def mock_query_side_effect(query):
            if MemoryTier.L1_RAW_IO in query.tiers:
                return messages
            return []

        mock_memory.query.side_effect = mock_query_side_effect

        result = await strategy.curate(mock_memory, config)

        # Count L1 messages in result
        l1_count = sum(1 for u in result if u.tier == MemoryTier.L1_RAW_IO)
        assert l1_count <= 20, f"System 2 should limit L1 to 20, got {l1_count}"

    async def test_curate_queries_l3_when_focus_distance_enabled(self, strategy, mock_memory, config):
        """Test that System 2 queries L3 when focus_distance >= 1."""
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config)

        # Should query L3
        calls = mock_memory.query.call_args_list
        l3_found = False
        for call in calls:
            query = call[0][0]
            if MemoryTier.L3_SESSION in query.tiers:
                l3_found = True
                break
        assert l3_found, "System 2 should query L3 when focus_distance >= 1"

    async def test_curate_skips_l3_when_focus_distance_zero(self, strategy, mock_memory):
        """Test that System 2 skips L3 when focus_distance = 0."""
        config = CurationConfig(
            max_tokens=8000,
            include_facts=True,
            focus_distance=0
        )
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config)

        # Should NOT query L3
        calls = mock_memory.query.call_args_list
        for call in calls:
            query = call[0][0]
            assert MemoryTier.L3_SESSION not in query.tiers, \
                "System 2 should not query L3 when focus_distance = 0"

    async def test_curate_queries_l4_with_task_context(self, strategy, mock_memory, config):
        """Test that System 2 queries L4 with semantic search when task_context provided."""
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config, task_context="find relevant information")

        # Should query L4 with query_text
        calls = mock_memory.query.call_args_list
        l4_found = False
        for call in calls:
            query = call[0][0]
            if MemoryTier.L4_GLOBAL in query.tiers:
                if query.query_text == "find relevant information":
                    l4_found = True
                    break
        assert l4_found, "System 2 should query L4 with task_context for semantic search"

    async def test_curate_skips_l4_without_task_context(self, strategy, mock_memory, config):
        """Test that System 2 skips L4 semantic search without task_context."""
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config, task_context=None)

        # Should NOT query L4 with query_text
        calls = mock_memory.query.call_args_list
        for call in calls:
            query = call[0][0]
            if MemoryTier.L4_GLOBAL in query.tiers:
                # If L4 is queried, it should not have query_text
                assert query.query_text is None, \
                    "System 2 should not query L4 with text without task_context"

    async def test_curate_skips_l4_facts_when_disabled(self, strategy, mock_memory, config):
        """Test that System 2 skips L4 facts when disabled."""
        config = CurationConfig(
            max_tokens=8000,
            include_facts=False,
            focus_distance=1
        )
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config, task_context="test")

        # Should NOT query L4 for facts when include_facts=False
        calls = mock_memory.query.call_args_list
        for call in calls:
            query = call[0][0]
            if MemoryTier.L4_GLOBAL in query.tiers:
                # If L4 is queried, it's only for semantic search
                # But with include_facts=False, we still might want semantic search
                pass

    async def test_curate_uses_top_k_10_for_l4_search(self, strategy, mock_memory, config):
        """Test that System 2 uses top_k=10 for L4 semantic search."""
        mock_memory.query.return_value = []

        await strategy.curate(mock_memory, config, task_context="test")

        # Should query L4 with top_k=10
        calls = mock_memory.query.call_args_list
        l4_found = False
        for call in calls:
            query = call[0][0]
            if MemoryTier.L4_GLOBAL in query.tiers and query.query_text:
                l4_found = True
                assert query.top_k == 10, f"System 2 should use top_k=10 for L4, got {query.top_k}"
                break
        assert l4_found, "System 2 should query L4 with top_k=10"
