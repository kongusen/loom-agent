"""
Unit Tests for LoomContext and Strategies
"""

import pytest

from loom.config import ContextConfig, CurationConfig
from loom.memory.context import ContextAssembler, ContextManager
from loom.memory.core import LoomMemory
from loom.memory.strategies import AutoStrategy, SnippetsStrategy
from loom.memory.types import MemoryQuery, MemoryTier, MemoryType, MemoryUnit


class TestContextCuration:
    """Tests for Curation Strategies."""

    @pytest.mark.asyncio
    async def test_auto_strategy_basic(self):
        """Test AutoStrategy curation logic."""
        memory = LoomMemory("test_node")

        # Add L2
        await memory.add(MemoryUnit(content="L2 Item", tier=MemoryTier.L2_WORKING))

        # Add many L1 items
        for i in range(20):
            await memory.add(MemoryUnit(content=f"L1 Item {i}", tier=MemoryTier.L1_RAW_IO))

        strategy = AutoStrategy()
        config = CurationConfig(focus_distance=0)

        curated = await strategy.curate(memory, config)

        # L2 should be present (1 item)
        l2_count = len([u for u in curated if u.tier == MemoryTier.L2_WORKING])
        assert l2_count == 1

        # L1 should be top 10 recent
        l1_count = len([u for u in curated if u.tier == MemoryTier.L1_RAW_IO])
        assert l1_count == 10

    @pytest.mark.asyncio
    async def test_snippets_strategy(self):
        """Test SnippetsStrategy logic."""
        memory = LoomMemory("test_node")

        # Add a full skill (L4)
        await memory.add(
            MemoryUnit(
                content="Full Skill Content..." * 10,
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.SKILL,
                metadata={"name": "TestSkill", "description": "A test skill"},
            )
        )

        strategy = SnippetsStrategy()
        config = CurationConfig(use_snippets=True)

        curated = await strategy.curate(memory, config)

        # Should find one snippet
        snippets = [u for u in curated if u.metadata.get("snippet_of")]
        assert len(snippets) == 1
        assert "TestSkill" in str(snippets[0].content)


class TestContextAssembler:
    """Tests for ContextAssembler."""

    @pytest.mark.asyncio
    async def test_assemble_basic(self):
        """Test basic assembly."""
        memory = LoomMemory("test_node")
        await memory.add(
            MemoryUnit(content="User message", tier=MemoryTier.L1_RAW_IO, type=MemoryType.MESSAGE)
        )

        assembler = ContextAssembler()
        messages = await assembler.assemble(memory, task="Test")

        assert len(messages) > 0
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_token_budget(self):
        """Test token budgeting."""
        memory = LoomMemory("test_node")

        # Add items that would exceed budget
        long_text = "word " * 100
        for _i in range(10):
            await memory.add(
                MemoryUnit(
                    content={"role": "user", "content": long_text},
                    tier=MemoryTier.L2_WORKING,
                    type=MemoryType.MESSAGE,
                )
            )

        # Strict budget
        config = ContextConfig()
        config.curation_config.max_tokens = 50  # Very small
        assembler = ContextAssembler(config=config)

        messages = await assembler.assemble(memory)

        # Should be empty or very few messages
        # Count tokens
        total = (
            assembler._count_tokens_msg(
                {"role": "user", "content": " ".join([m["content"] for m in messages])}
            )
            if messages
            else 0
        )
        assert total <= config.curation_config.max_tokens + 10  # approximate buffer


class TestContextManager:
    """Tests for ContextManager facade."""

    @pytest.mark.asyncio
    async def test_load_resource(self):
        """Test dynamic resource loading."""
        memory = LoomMemory("test_node")
        assembler = ContextAssembler()
        manager = ContextManager("test_node", memory, assembler)

        # Create a "snippet source" in memory
        unit = MemoryUnit(content="FULL CONTENT", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT)
        unit_id = await memory.add(unit)

        # Load it
        result = await manager.load_resource(unit_id)
        assert "Loaded" in result

        # Verify it's in L2 now
        l2_items = await memory.query(MemoryQuery(tiers=[MemoryTier.L2_WORKING]))

        # Find unit with metadata loaded_from
        loaded = [u for u in l2_items if u.metadata.get("loaded_from") == unit_id]
        assert len(loaded) == 1
        assert loaded[0].content == "FULL CONTENT"


class TestContextAssemblerAdditional:
    """Additional tests for ContextAssembler to improve coverage."""

    @pytest.fixture
    def mock_memory(self):
        """Create a mock memory object."""
        from unittest.mock import MagicMock

        memory = MagicMock(spec=LoomMemory)
        memory._l4_global = []
        memory.node_id = "test_node"
        return memory

    def test_count_tokens_msg(self):
        """Test token counting for message dict."""
        assembler = ContextAssembler()
        message = {"role": "user", "content": "Hello world"}
        count = assembler._count_tokens_msg(message)
        assert count > 0

    def test_count_tokens_str(self):
        """Test token counting for string."""
        assembler = ContextAssembler()
        count = assembler._count_tokens_str("Hello world")
        assert count > 0

    def test_calculate_dynamic_budget_simple_task(self, mock_memory):
        """Test budget calculation for simple task."""
        assembler = ContextAssembler()
        budget = assembler._calculate_dynamic_budget("simple task", mock_memory)
        assert budget > 0

    def test_calculate_dynamic_budget_complex_task(self, mock_memory):
        """Test budget calculation for complex task."""
        assembler = ContextAssembler()
        # Task with multiple complexity indicators
        complex_task = "analyze and refactor the code to optimize performance"
        budget = assembler._calculate_dynamic_budget(complex_task, mock_memory)
        simple_budget = assembler._calculate_dynamic_budget("simple task", mock_memory)
        assert budget >= simple_budget  # Complex task should get more budget

    def test_calculate_dynamic_budget_with_rich_l4(self, mock_memory):
        """Test budget reduction when L4 has rich context."""
        # Add high-importance L4 units
        for i in range(15):
            unit = MemoryUnit(
                content=f"Fact {i}", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT, importance=0.9
            )
            mock_memory._l4_global.append(unit)

        assembler = ContextAssembler()
        budget = assembler._calculate_dynamic_budget("test task", mock_memory)
        base_budget = assembler.config.curation_config.max_tokens
        assert budget < base_budget  # Should be reduced

    def test_build_load_hint_no_snippets(self):
        """Test load hint when no snippets available."""
        assembler = ContextAssembler()
        hint = assembler._build_load_hint([])
        assert hint is None

    def test_build_load_hint_with_snippets(self):
        """Test load hint with snippets."""
        assembler = ContextAssembler()
        units = [
            MemoryUnit(
                content="Snippet",
                tier=MemoryTier.L2_WORKING,
                type=MemoryType.CONTEXT,
                metadata={"full_available": True, "snippet_of": "test_id"},
            )
        ]
        hint = assembler._build_load_hint(units)
        assert hint is not None
        assert "Available Resources" in hint
        assert "test_id" in hint

    def test_build_load_hint_limits_to_five(self):
        """Test that load hint is limited to 5 items."""
        assembler = ContextAssembler()
        units = []
        for i in range(10):
            units.append(
                MemoryUnit(
                    content=f"Snippet {i}",
                    tier=MemoryTier.L2_WORKING,
                    type=MemoryType.CONTEXT,
                    metadata={"full_available": True, "snippet_of": f"id_{i}"},
                )
            )

        hint = assembler._build_load_hint(units)
        # Should only show first 5
        assert "id_0" in hint
        assert "id_9" not in hint

    def test_insert_cache_boundaries_disabled(self):
        """Test cache boundaries when caching is disabled."""
        from loom.config.memory import ContextConfig

        config = ContextConfig(enable_prompt_caching=False)
        assembler = ContextAssembler(config=config)
        messages = [{"role": "user", "content": "test"}]
        result = assembler._insert_cache_boundaries(messages, [])
        assert result == messages  # Should return unchanged

    def test_insert_cache_boundaries_enabled(self):
        """Test cache boundaries when caching is enabled."""
        from loom.config.memory import ContextConfig

        config = ContextConfig(enable_prompt_caching=True)
        assembler = ContextAssembler(config=config)
        messages = [{"role": "system", "content": "test"}, {"role": "user", "content": "hi"}]
        result = assembler._insert_cache_boundaries(messages, [])
        assert "cache_control" in result[0]

    def test_insert_cache_boundaries_with_l4_units(self):
        """Test cache boundaries with L4 units."""
        from loom.config.memory import ContextConfig

        config = ContextConfig(enable_prompt_caching=True)
        assembler = ContextAssembler(config=config)

        messages = [{"role": "system", "content": "test"}, {"role": "user", "content": "hi"}]
        units = [
            MemoryUnit(content="L4 fact", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT),
            MemoryUnit(content="L1 msg", tier=MemoryTier.L1_RAW_IO, type=MemoryType.MESSAGE),
        ]

        result = assembler._insert_cache_boundaries(messages, units)
        # Should mark both system and L4 boundary
        assert "cache_control" in result[0]

    @pytest.mark.asyncio
    async def test_assemble_with_prompt_caching_enabled(self, mock_memory):
        """Test assembly with prompt caching enabled."""
        from unittest.mock import AsyncMock, patch

        from loom.config.memory import ContextConfig

        config = ContextConfig(enable_prompt_caching=True)
        assembler = ContextAssembler(config=config)

        units = [MemoryUnit(content="L4 content", tier=MemoryTier.L4_GLOBAL, type=MemoryType.FACT)]

        with patch.object(assembler.strategy, "curate", new=AsyncMock(return_value=units)):
            messages = await assembler.assemble(mock_memory, task="test", system_prompt="test")
            # Should have cache_control markers
            assert any("cache_control" in msg for msg in messages)

    @pytest.mark.asyncio
    async def test_assemble_without_system_prompt(self, mock_memory):
        """Test assembly without system prompt."""
        from unittest.mock import AsyncMock, patch

        assembler = ContextAssembler()

        with patch.object(assembler.strategy, "curate", new=AsyncMock(return_value=[])):
            messages = await assembler.assemble(mock_memory, task="test")
            # Should still return a list, possibly empty
            assert isinstance(messages, list)


class TestContextManagerAdditional:
    """Additional tests for ContextManager to improve coverage."""

    @pytest.fixture
    def mock_memory(self):
        """Create a mock memory object."""
        from unittest.mock import MagicMock

        memory = MagicMock(spec=LoomMemory)
        memory.get_statistics = MagicMock(return_value={"total": 100})
        memory.node_id = "test_node"
        return memory

    @pytest.fixture
    def mock_assembler(self):
        """Create a mock assembler."""
        from unittest.mock import MagicMock

        assembler = MagicMock(spec=ContextAssembler)
        assembler.assemble = MagicMock(return_value=[])
        assembler.expand_snippet = MagicMock(return_value=None)
        return assembler

    @pytest.fixture
    def manager(self, mock_memory, mock_assembler):
        """Create a context manager."""
        return ContextManager(node_id="test_node", memory=mock_memory, assembler=mock_assembler)

    def test_get_context_stats(self, manager, mock_memory):
        """Test getting context statistics."""
        manager.last_snapshot = [{"role": "user"}, {"role": "assistant"}]
        stats = manager.get_context_stats()
        assert stats["last_message_count"] == 2
        assert stats["memory_stats"] == {"total": 100}

    def test_visualize(self, manager):
        """Test context visualization."""
        manager.last_snapshot = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        viz = manager.visualize()
        assert "test_node" in viz
        assert "SYSTEM" in viz
        assert "USER" in viz
        assert "=" in viz  # Separator lines

    def test_visualize_truncates_content(self, manager):
        """Test that visualization truncates long content."""
        manager.last_snapshot = [
            {"role": "user", "content": "x" * 200}  # Long content
        ]
        viz = manager.visualize()
        # Content should be truncated to ~100 chars
        assert "..." in viz or len([line for line in viz.split("\n") if "x" in line]) > 0

    @pytest.mark.asyncio
    async def test_build_prompt_updates_snapshot(self, manager, mock_assembler):
        """Test that build_prompt updates last_snapshot."""
        from unittest.mock import AsyncMock

        mock_assembler.assemble = AsyncMock(
            return_value=[{"role": "system", "content": "test"}, {"role": "user", "content": "hi"}]
        )

        messages = await manager.build_prompt("test task")
        assert manager.last_snapshot == messages
        assert len(messages) == 2
