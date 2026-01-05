"""
Unit Tests for LoomMemory Core
"""
import pytest
from datetime import datetime, timedelta

from loom.memory.core import LoomMemory
from loom.memory.types import (
    MemoryUnit, MemoryTier, MemoryType,
    MemoryQuery
)

class TestLoomMemory:
    """LoomMemory Basic Tests"""

    @pytest.mark.asyncio
    async def test_basic_storage(self):
        """Test basic add and retrieval."""
        memory = LoomMemory("test_node")

        # Add L1
        l1_id = await memory.add(MemoryUnit(
            content="Hello",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE
        ))

        # Add L2
        l2_id = await memory.add(MemoryUnit(
            content="Plan: analyze data",
            tier=MemoryTier.L2_WORKING,
            type=MemoryType.PLAN
        ))

        # Verify
        assert memory.get(l1_id) is not None
        assert memory.get(l2_id) is not None

        stats = memory.get_statistics()
        assert stats["l1_size"] == 1
        assert stats["l2_size"] == 1

    @pytest.mark.asyncio
    async def test_l1_buffer_limit(self):
        """Test L1 circular buffer limit."""
        memory = LoomMemory("test_node", max_l1_size=5)

        # Add 10 items
        for i in range(10):
            await memory.add(MemoryUnit(
                content=f"Message {i}",
                tier=MemoryTier.L1_RAW_IO
            ))

        # Verify only 5 remain
        stats = memory.get_statistics()
        assert stats["l1_size"] == 5

        # Verify the oldest (first added) are gone
        # The first 5 (0-4) should be gone, 5-9 should remain
        query = MemoryQuery(tiers=[MemoryTier.L1_RAW_IO], descending=False)
        results = await memory.query(query)
        assert len(results) == 5
        assert results[0].content == "Message 5"

    @pytest.mark.asyncio
    async def test_query_by_tier(self):
        """Test querying by tier."""
        memory = LoomMemory("test_node")

        await memory.add(MemoryUnit(content="L1", tier=MemoryTier.L1_RAW_IO))
        await memory.add(MemoryUnit(content="L2", tier=MemoryTier.L2_WORKING))

        query = MemoryQuery(tiers=[MemoryTier.L2_WORKING])
        results = await memory.query(query)
        assert len(results) == 1
        assert results[0].tier == MemoryTier.L2_WORKING
        assert results[0].content == "L2"

    @pytest.mark.asyncio
    async def test_query_by_type(self):
        """Test querying by type."""
        memory = LoomMemory("test_node")

        await memory.add(MemoryUnit(
            content="User message",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE
        ))
        await memory.add(MemoryUnit(
            content="Agent thought",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.THOUGHT
        ))

        query = MemoryQuery(types=[MemoryType.MESSAGE])
        results = await memory.query(query)
        assert len(results) == 1
        assert results[0].type == MemoryType.MESSAGE

    @pytest.mark.asyncio
    async def test_promote_to_l4(self):
        """Test promoting L2 to L4."""
        memory = LoomMemory("test_node")

        # Add L2
        unit_id = await memory.add(MemoryUnit(
            content="Important fact",
            tier=MemoryTier.L2_WORKING,
            type=MemoryType.FACT
        ))

        # Promote
        memory.promote_to_l4(unit_id)

        # Verify
        unit = memory.get(unit_id)
        assert unit.tier == MemoryTier.L4_GLOBAL

        stats = memory.get_statistics()
        assert stats["l2_size"] == 0
        assert stats["l4_size"] == 1

    @pytest.mark.asyncio
    async def test_projection(self):
        """Test context projection creation."""
        memory = LoomMemory("parent")

        # Add Plan
        await memory.add(MemoryUnit(
            content="Global Plan",
            tier=MemoryTier.L2_WORKING,
            type=MemoryType.PLAN
        ))

        # Add Fact
        await memory.add(MemoryUnit(
            content="Fact A",
            tier=MemoryTier.L4_GLOBAL,
            type=MemoryType.FACT,
            importance=0.9
        ))

        projection = memory.create_projection("Child Task")

        assert projection.instruction == "Child Task"
        assert projection.parent_plan == "Global Plan"
        assert len(projection.relevant_facts) > 0
