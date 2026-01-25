"""
Unit tests for Fractal Memory Synchronization and Conflict Resolution

Tests cover:
- MemorySyncManager version control (optimistic locking)
- Parent-child synchronization
- Three conflict resolution strategies
- Version conflict detection
"""

import pytest

from loom.fractal.memory import FractalMemory, MemoryEntry, MemoryScope
from loom.fractal.resolvers import (
    ChildWinsResolver,
    ConflictResolver,
    MergeResolver,
    ParentWinsResolver,
)
from loom.fractal.sync import MemorySyncManager


class TestMemorySyncManager:
    """Test MemorySyncManager basic functionality"""

    @pytest.mark.asyncio
    async def test_create_sync_manager(self):
        """Test creating a sync manager"""
        memory = FractalMemory(node_id="test-node")
        sync_manager = MemorySyncManager(memory)

        assert sync_manager.memory is memory

    @pytest.mark.asyncio
    async def test_write_with_version_check_success(self):
        """Test successful write with correct version"""
        memory = FractalMemory(node_id="test-node")
        sync_manager = MemorySyncManager(memory)

        # Write initial entry
        entry = await memory.write("key1", "value1", MemoryScope.LOCAL)
        assert entry.version == 1

        # Update with correct version
        entry.content = "value2"
        success, error = await sync_manager.write_with_version_check(entry, 1)

        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_write_with_version_check_conflict(self):
        """Test version conflict detection"""
        memory = FractalMemory(node_id="test-node")
        sync_manager = MemorySyncManager(memory)

        # Write initial entry
        entry = await memory.write("key1", "value1", MemoryScope.LOCAL)
        assert entry.version == 1

        # Try to update with wrong version (simulating concurrent modification)
        entry.content = "value2"
        success, error = await sync_manager.write_with_version_check(entry, 0)

        assert success is False
        assert error is not None
        assert "Version conflict" in error

    @pytest.mark.asyncio
    async def test_sync_from_parent_no_parent(self):
        """Test sync when there's no parent"""
        memory = FractalMemory(node_id="child")
        sync_manager = MemorySyncManager(memory)

        synced_count = await sync_manager.sync_from_parent()
        assert synced_count == 0

    @pytest.mark.asyncio
    async def test_sync_from_parent_new_entries(self):
        """Test syncing new entries from parent"""
        parent = FractalMemory(node_id="parent")
        child = FractalMemory(node_id="child", parent_memory=parent)
        sync_manager = MemorySyncManager(child)

        # Parent writes to SHARED scope
        await parent.write("key1", "value1", MemoryScope.SHARED)
        await parent.write("key2", "value2", MemoryScope.SHARED)

        # Sync from parent
        synced_count = await sync_manager.sync_from_parent()

        assert synced_count == 2

        # Verify child has the entries
        entry1 = await child.read("key1", search_scopes=[MemoryScope.SHARED])
        entry2 = await child.read("key2", search_scopes=[MemoryScope.SHARED])
        assert entry1 is not None
        assert entry2 is not None


class TestConflictResolvers:
    """Test conflict resolution strategies"""

    @pytest.mark.asyncio
    async def test_parent_wins_resolver(self):
        """Test ParentWinsResolver strategy"""
        resolver = ParentWinsResolver()

        parent_entry = MemoryEntry(
            id="key1",
            content="parent_value",
            scope=MemoryScope.SHARED,
            version=2,
        )
        child_entry = MemoryEntry(
            id="key1",
            content="child_value",
            scope=MemoryScope.SHARED,
            version=1,
        )

        result = await resolver.resolve(parent_entry, child_entry)

        assert result is parent_entry
        assert result.content == "parent_value"

    @pytest.mark.asyncio
    async def test_child_wins_resolver(self):
        """Test ChildWinsResolver strategy"""
        resolver = ChildWinsResolver()

        parent_entry = MemoryEntry(
            id="key1",
            content="parent_value",
            scope=MemoryScope.SHARED,
            version=2,
        )
        child_entry = MemoryEntry(
            id="key1",
            content="child_value",
            scope=MemoryScope.SHARED,
            version=1,
        )

        result = await resolver.resolve(parent_entry, child_entry)

        assert result is child_entry
        assert result.content == "child_value"

    @pytest.mark.asyncio
    async def test_merge_resolver_dict_merge(self):
        """Test MergeResolver with dict content"""
        resolver = MergeResolver()

        parent_entry = MemoryEntry(
            id="key1",
            content={"a": 1, "b": 2, "c": {"x": 10}},
            scope=MemoryScope.SHARED,
            version=2,
            created_by="parent",
            updated_by="parent",
        )
        child_entry = MemoryEntry(
            id="key1",
            content={"b": 3, "d": 4, "c": {"y": 20}},
            scope=MemoryScope.SHARED,
            version=1,
            created_by="parent",
            updated_by="child",
        )

        result = await resolver.resolve(parent_entry, child_entry)

        # Check merged content
        assert result.content["a"] == 1  # From parent
        assert result.content["b"] == 3  # From child (overrides)
        assert result.content["d"] == 4  # From child (new)
        assert result.content["c"]["x"] == 10  # From parent
        assert result.content["c"]["y"] == 20  # From child

    @pytest.mark.asyncio
    async def test_merge_resolver_non_dict(self):
        """Test MergeResolver with non-dict content (uses child version)"""
        resolver = MergeResolver()

        parent_entry = MemoryEntry(
            id="key1",
            content="parent_value",
            scope=MemoryScope.SHARED,
            version=2,
            created_by="parent",
            updated_by="parent",
        )
        child_entry = MemoryEntry(
            id="key1",
            content="child_value",
            scope=MemoryScope.SHARED,
            version=1,
            created_by="parent",
            updated_by="child",
        )

        result = await resolver.resolve(parent_entry, child_entry)

        # For non-dict content, child version wins
        assert result.content == "child_value"
        assert result.version == 3  # max(2, 1) + 1

