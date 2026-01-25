"""
Phase 2: Sync Mechanism Tests

Tests for MemorySyncManager and conflict resolvers.
"""

import pytest

from loom.fractal.memory import FractalMemory, MemoryEntry, MemoryScope
from loom.fractal.resolvers import ChildWinsResolver, MergeResolver, ParentWinsResolver
from loom.fractal.sync import MemorySyncManager


class TestMemorySyncManager:
    """Test MemorySyncManager class"""

    @pytest.fixture
    def memory(self) -> FractalMemory:
        """Create a FractalMemory instance for testing"""
        return FractalMemory(node_id="test-node")

    @pytest.fixture
    def sync_manager(self, memory: FractalMemory) -> MemorySyncManager:
        """Create a MemorySyncManager instance for testing"""
        return MemorySyncManager(memory)

    @pytest.mark.asyncio
    async def test_sync_manager_creation(
        self, sync_manager: MemorySyncManager, memory: FractalMemory
    ) -> None:
        """Test creating a sync manager"""
        assert sync_manager.memory == memory

    @pytest.mark.asyncio
    async def test_write_with_version_check_success(
        self, sync_manager: MemorySyncManager
    ) -> None:
        """Test successful write with version check"""
        entry = MemoryEntry(
            id="test-1",
            content={"data": "test"},
            scope=MemoryScope.LOCAL,
            version=1,
        )

        success, error = await sync_manager.write_with_version_check(entry, 0)
        assert success is True
        assert error is None


class TestConflictResolvers:
    """Test conflict resolver strategies"""

    @pytest.mark.asyncio
    async def test_parent_wins_resolver(self) -> None:
        """Test ParentWinsResolver strategy"""
        resolver = ParentWinsResolver()

        parent_entry = MemoryEntry(
            id="test-1",
            content={"value": "parent"},
            scope=MemoryScope.SHARED,
            version=2,
        )

        child_entry = MemoryEntry(
            id="test-1",
            content={"value": "child"},
            scope=MemoryScope.SHARED,
            version=2,
        )

        result = await resolver.resolve(parent_entry, child_entry)
        assert result.content == {"value": "parent"}

    @pytest.mark.asyncio
    async def test_child_wins_resolver(self) -> None:
        """Test ChildWinsResolver strategy"""
        resolver = ChildWinsResolver()

        parent_entry = MemoryEntry(
            id="test-1",
            content={"value": "parent"},
            scope=MemoryScope.SHARED,
            version=2,
        )

        child_entry = MemoryEntry(
            id="test-1",
            content={"value": "child"},
            scope=MemoryScope.SHARED,
            version=2,
        )

        result = await resolver.resolve(parent_entry, child_entry)
        assert result.content == {"value": "child"}

