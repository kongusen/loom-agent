"""
Unit tests for Fractal Memory System

Tests cover:
- All four memory scopes (LOCAL, SHARED, INHERITED, GLOBAL)
- Access policies and permissions
- Parent-child memory inheritance
- Memory read/write operations
"""

import pytest

from loom.fractal.memory import (
    ACCESS_POLICIES,
    FractalMemory,
    MemoryEntry,
    MemoryScope,
)


class TestMemoryScope:
    """Test MemoryScope enum"""

    def test_all_scopes_defined(self):
        """Test that all four scopes are defined"""
        assert MemoryScope.LOCAL.value == "local"
        assert MemoryScope.SHARED.value == "shared"
        assert MemoryScope.INHERITED.value == "inherited"
        assert MemoryScope.GLOBAL.value == "global"


class TestMemoryAccessPolicy:
    """Test MemoryAccessPolicy dataclass"""

    def test_local_policy(self):
        """Test LOCAL scope access policy"""
        policy = ACCESS_POLICIES[MemoryScope.LOCAL]
        assert policy.scope == MemoryScope.LOCAL
        assert policy.readable is True
        assert policy.writable is True
        assert policy.propagate_up is False
        assert policy.propagate_down is False

    def test_shared_policy(self):
        """Test SHARED scope access policy"""
        policy = ACCESS_POLICIES[MemoryScope.SHARED]
        assert policy.scope == MemoryScope.SHARED
        assert policy.readable is True
        assert policy.writable is True
        assert policy.propagate_up is True
        assert policy.propagate_down is True

    def test_inherited_policy(self):
        """Test INHERITED scope access policy (read-only)"""
        policy = ACCESS_POLICIES[MemoryScope.INHERITED]
        assert policy.scope == MemoryScope.INHERITED
        assert policy.readable is True
        assert policy.writable is False  # Read-only
        assert policy.propagate_up is False
        assert policy.propagate_down is True

    def test_global_policy(self):
        """Test GLOBAL scope access policy"""
        policy = ACCESS_POLICIES[MemoryScope.GLOBAL]
        assert policy.scope == MemoryScope.GLOBAL
        assert policy.readable is True
        assert policy.writable is True
        assert policy.propagate_up is True
        assert policy.propagate_down is True


class TestMemoryEntry:
    """Test MemoryEntry dataclass"""

    def test_create_entry(self):
        """Test creating a memory entry"""
        entry = MemoryEntry(
            id="test-1",
            content="test content",
            scope=MemoryScope.LOCAL,
        )
        assert entry.id == "test-1"
        assert entry.content == "test content"
        assert entry.scope == MemoryScope.LOCAL
        assert entry.version == 1
        assert entry.created_by == ""
        assert entry.updated_by == ""
        assert entry.parent_version is None
        assert entry.metadata == {}

    def test_entry_with_metadata(self):
        """Test creating entry with metadata"""
        entry = MemoryEntry(
            id="test-2",
            content="test content",
            scope=MemoryScope.SHARED,
            metadata={"key": "value"},
        )
        assert entry.metadata == {"key": "value"}

    def test_entry_version_tracking(self):
        """Test version tracking in memory entry"""
        entry = MemoryEntry(
            id="test-3",
            content="test content",
            scope=MemoryScope.SHARED,
            version=5,
            created_by="node-1",
            updated_by="node-2",
        )
        assert entry.version == 5
        assert entry.created_by == "node-1"
        assert entry.updated_by == "node-2"


class TestFractalMemoryBasic:
    """Test basic FractalMemory operations"""

    @pytest.mark.asyncio
    async def test_create_memory(self):
        """Test creating a FractalMemory instance"""
        memory = FractalMemory(node_id="test-node")
        assert memory.node_id == "test-node"
        assert memory.parent_memory is None
        assert memory.base_memory is None

    @pytest.mark.asyncio
    async def test_write_local_memory(self):
        """Test writing to LOCAL scope"""
        memory = FractalMemory(node_id="test-node")
        entry = await memory.write("key1", "value1", MemoryScope.LOCAL)

        assert entry.id == "key1"
        assert entry.content == "value1"
        assert entry.scope == MemoryScope.LOCAL
        assert entry.created_by == "test-node"
        assert entry.updated_by == "test-node"

    @pytest.mark.asyncio
    async def test_write_shared_memory(self):
        """Test writing to SHARED scope"""
        memory = FractalMemory(node_id="test-node")
        entry = await memory.write("key2", "value2", MemoryScope.SHARED)

        assert entry.id == "key2"
        assert entry.content == "value2"
        assert entry.scope == MemoryScope.SHARED

    @pytest.mark.asyncio
    async def test_write_global_memory(self):
        """Test writing to GLOBAL scope"""
        memory = FractalMemory(node_id="test-node")
        entry = await memory.write("key3", "value3", MemoryScope.GLOBAL)

        assert entry.id == "key3"
        assert entry.content == "value3"
        assert entry.scope == MemoryScope.GLOBAL

    @pytest.mark.asyncio
    async def test_write_inherited_fails(self):
        """Test that writing to INHERITED scope fails (read-only)"""
        memory = FractalMemory(node_id="test-node")

        with pytest.raises(PermissionError, match="read-only"):
            await memory.write("key4", "value4", MemoryScope.INHERITED)

    @pytest.mark.asyncio
    async def test_read_memory(self):
        """Test reading memory"""
        memory = FractalMemory(node_id="test-node")
        await memory.write("key1", "value1", MemoryScope.LOCAL)

        entry = await memory.read("key1")
        assert entry is not None
        assert entry.id == "key1"
        assert entry.content == "value1"

    @pytest.mark.asyncio
    async def test_read_nonexistent(self):
        """Test reading non-existent memory returns None"""
        memory = FractalMemory(node_id="test-node")
        entry = await memory.read("nonexistent")
        assert entry is None

    @pytest.mark.asyncio
    async def test_read_with_scope_filter(self):
        """Test reading with specific scope filter"""
        memory = FractalMemory(node_id="test-node")
        await memory.write("key1", "value1", MemoryScope.LOCAL)
        await memory.write("key2", "value2", MemoryScope.SHARED)

        # Read only from LOCAL scope
        entry = await memory.read("key1", search_scopes=[MemoryScope.LOCAL])
        assert entry is not None
        assert entry.id == "key1"

        # Try to read SHARED from LOCAL scope only - should fail
        entry = await memory.read("key2", search_scopes=[MemoryScope.LOCAL])
        assert entry is None

    @pytest.mark.asyncio
    async def test_list_by_scope(self):
        """Test listing memories by scope"""
        memory = FractalMemory(node_id="test-node")
        await memory.write("key1", "value1", MemoryScope.LOCAL)
        await memory.write("key2", "value2", MemoryScope.LOCAL)
        await memory.write("key3", "value3", MemoryScope.SHARED)

        local_entries = await memory.list_by_scope(MemoryScope.LOCAL)
        assert len(local_entries) == 2
        assert all(e.scope == MemoryScope.LOCAL for e in local_entries)

        shared_entries = await memory.list_by_scope(MemoryScope.SHARED)
        assert len(shared_entries) == 1
        assert shared_entries[0].id == "key3"


class TestFractalMemoryInheritance:
    """Test parent-child memory inheritance"""

    @pytest.mark.asyncio
    async def test_create_child_with_parent(self):
        """Test creating child memory with parent reference"""
        parent = FractalMemory(node_id="parent")
        child = FractalMemory(node_id="child", parent_memory=parent)

        assert child.node_id == "child"
        assert child.parent_memory is parent

    @pytest.mark.asyncio
    async def test_child_inherits_shared_memory(self):
        """Test child can read parent's SHARED memory"""
        parent = FractalMemory(node_id="parent")
        child = FractalMemory(node_id="child", parent_memory=parent)

        # Parent writes to SHARED scope
        await parent.write("shared_key", "shared_value", MemoryScope.SHARED)

        # Child should be able to read it through INHERITED scope
        entry = await child.read("shared_key", search_scopes=[MemoryScope.INHERITED])
        assert entry is not None
        assert entry.id == "shared_key"
        assert entry.content == "shared_value"
        assert entry.scope == MemoryScope.INHERITED  # Converted to INHERITED

    @pytest.mark.asyncio
    async def test_child_inherits_global_memory(self):
        """Test child can read parent's GLOBAL memory"""
        parent = FractalMemory(node_id="parent")
        child = FractalMemory(node_id="child", parent_memory=parent)

        # Parent writes to GLOBAL scope
        await parent.write("global_key", "global_value", MemoryScope.GLOBAL)

        # Child should be able to read it through INHERITED scope
        entry = await child.read("global_key", search_scopes=[MemoryScope.INHERITED])
        assert entry is not None
        assert entry.id == "global_key"
        assert entry.content == "global_value"
        assert entry.scope == MemoryScope.INHERITED

    @pytest.mark.asyncio
    async def test_child_cannot_inherit_local_memory(self):
        """Test child cannot read parent's LOCAL memory"""
        parent = FractalMemory(node_id="parent")
        child = FractalMemory(node_id="child", parent_memory=parent)

        # Parent writes to LOCAL scope
        await parent.write("local_key", "local_value", MemoryScope.LOCAL)

        # Child should NOT be able to read it
        entry = await child.read("local_key", search_scopes=[MemoryScope.INHERITED])
        assert entry is None

    @pytest.mark.asyncio
    async def test_inherited_entry_version_tracking(self):
        """Test that inherited entries track parent version"""
        parent = FractalMemory(node_id="parent")
        child = FractalMemory(node_id="child", parent_memory=parent)

        # Parent writes with specific version
        parent_entry = await parent.write("key1", "value1", MemoryScope.SHARED)
        parent_entry.version = 5  # Simulate version update

        # Child reads and inherits
        child_entry = await child.read("key1", search_scopes=[MemoryScope.INHERITED])
        assert child_entry is not None
        assert child_entry.version == 5
        assert child_entry.parent_version == 5

    @pytest.mark.asyncio
    async def test_inherited_entry_caching(self):
        """Test that inherited entries are cached locally"""
        parent = FractalMemory(node_id="parent")
        child = FractalMemory(node_id="child", parent_memory=parent)

        await parent.write("key1", "value1", MemoryScope.SHARED)

        # First read - should fetch from parent
        entry1 = await child.read("key1", search_scopes=[MemoryScope.INHERITED])
        assert entry1 is not None

        # Check that it's cached in child's INHERITED scope
        inherited_entries = await child.list_by_scope(MemoryScope.INHERITED)
        assert len(inherited_entries) == 1
        assert inherited_entries[0].id == "key1"

    @pytest.mark.asyncio
    async def test_multi_level_inheritance(self):
        """Test multi-level inheritance (grandparent -> parent -> child)"""
        grandparent = FractalMemory(node_id="grandparent")
        parent = FractalMemory(node_id="parent", parent_memory=grandparent)
        child = FractalMemory(node_id="child", parent_memory=parent)

        # Grandparent writes to GLOBAL scope
        await grandparent.write("global_key", "global_value", MemoryScope.GLOBAL)

        # Parent should be able to inherit from grandparent
        parent_entry = await parent.read("global_key", search_scopes=[MemoryScope.INHERITED])
        assert parent_entry is not None
        assert parent_entry.content == "global_value"

        # Child should be able to inherit from parent (which inherited from grandparent)
        child_entry = await child.read("global_key", search_scopes=[MemoryScope.INHERITED])
        assert child_entry is not None
        assert child_entry.content == "global_value"

    @pytest.mark.asyncio
    async def test_child_local_overrides_inherited(self):
        """Test that child's LOCAL memory takes precedence over inherited"""
        parent = FractalMemory(node_id="parent")
        child = FractalMemory(node_id="child", parent_memory=parent)

        # Parent writes
        await parent.write("key1", "parent_value", MemoryScope.SHARED)

        # Child writes to LOCAL with same key
        await child.write("key1", "child_value", MemoryScope.LOCAL)

        # Child should read its own LOCAL value first
        entry = await child.read("key1")
        assert entry is not None
        assert entry.content == "child_value"
        assert entry.scope == MemoryScope.LOCAL

