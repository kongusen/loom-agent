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

        projection = await memory.create_projection("Child Task")

        assert projection.instruction == "Child Task"
        assert projection.parent_plan == "Global Plan"
        assert len(projection.relevant_facts) > 0

    @pytest.mark.asyncio
    async def test_mode_detection(self):
        """Test automatic mode detection (English and Chinese)."""
        from loom.projection.profiles import ProjectionMode

        memory = LoomMemory("test_node")

        # Test DEBUG mode detection - English
        assert memory._detect_mode("Fix the error in the code") == ProjectionMode.DEBUG
        assert memory._detect_mode("Debug this issue") == ProjectionMode.DEBUG
        assert memory._detect_mode("Retry the failed request") == ProjectionMode.DEBUG

        # Test DEBUG mode detection - Chinese
        assert memory._detect_mode("修复这个错误") == ProjectionMode.DEBUG
        assert memory._detect_mode("调试这个问题") == ProjectionMode.DEBUG
        assert memory._detect_mode("重试失败的请求") == ProjectionMode.DEBUG

        # Test ANALYTICAL mode detection - English
        assert memory._detect_mode("Analyze the performance") == ProjectionMode.ANALYTICAL
        assert memory._detect_mode("Evaluate the results") == ProjectionMode.ANALYTICAL
        assert memory._detect_mode("Research this topic") == ProjectionMode.ANALYTICAL

        # Test ANALYTICAL mode detection - Chinese
        assert memory._detect_mode("分析系统性能") == ProjectionMode.ANALYTICAL
        assert memory._detect_mode("评估这个结果") == ProjectionMode.ANALYTICAL
        assert memory._detect_mode("研究这个主题") == ProjectionMode.ANALYTICAL

        # Test CONTEXTUAL mode detection - English
        assert memory._detect_mode("Continue the previous discussion") == ProjectionMode.CONTEXTUAL
        assert memory._detect_mode("Based on earlier context") == ProjectionMode.CONTEXTUAL

        # Test CONTEXTUAL mode detection - Chinese
        assert memory._detect_mode("继续之前的讨论") == ProjectionMode.CONTEXTUAL
        assert memory._detect_mode("基于刚才的上下文") == ProjectionMode.CONTEXTUAL

        # Test MINIMAL mode detection - English (short instruction)
        assert memory._detect_mode("Get status") == ProjectionMode.MINIMAL
        assert memory._detect_mode("Check") == ProjectionMode.MINIMAL

        # Test MINIMAL mode detection - Chinese (short instruction)
        assert memory._detect_mode("查询状态") == ProjectionMode.MINIMAL
        assert memory._detect_mode("检查") == ProjectionMode.MINIMAL

        # Test STANDARD mode (default) - English
        assert memory._detect_mode("Process the user data and generate report") == ProjectionMode.STANDARD

        # Test STANDARD mode (default) - Chinese
        assert memory._detect_mode("处理用户数据并生成报告") == ProjectionMode.STANDARD

    @pytest.mark.asyncio
    async def test_projection_with_mode(self):
        """Test projection with explicit mode parameter."""
        from loom.projection.profiles import ProjectionMode

        memory = LoomMemory("test_node")

        # Add some facts with different importance
        for i in range(10):
            await memory.add(MemoryUnit(
                content=f"Fact {i}",
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=0.5 + (i * 0.05)
            ))

        # Test with MINIMAL mode (should select fewer facts)
        projection_minimal = await memory.create_projection(
            instruction="Quick check",
            mode=ProjectionMode.MINIMAL
        )
        assert len(projection_minimal.relevant_facts) <= 2

        # Test with ANALYTICAL mode (should select more facts)
        projection_analytical = await memory.create_projection(
            instruction="Analyze the system",
            mode=ProjectionMode.ANALYTICAL
        )
        assert len(projection_analytical.relevant_facts) <= 15

        # Test with STANDARD mode
        projection_standard = await memory.create_projection(
            instruction="Process data",
            mode=ProjectionMode.STANDARD
        )
        assert len(projection_standard.relevant_facts) <= 8
