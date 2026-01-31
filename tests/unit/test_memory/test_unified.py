"""Tests for UnifiedMemoryManager"""
import pytest
from loom.memory.unified import UnifiedMemoryManager
from loom.fractal.memory import MemoryScope


def test_init_basic():
    """Test basic initialization"""
    manager = UnifiedMemoryManager(node_id="test-node")
    assert manager.node_id == "test-node"
    assert manager.parent is None
    assert len(manager._memory_by_scope) == len(MemoryScope)


def test_init_with_parent():
    """Test initialization with parent"""
    parent = UnifiedMemoryManager(node_id="parent")
    child = UnifiedMemoryManager(node_id="child", parent=parent)
    assert child.parent is parent


@pytest.mark.asyncio
async def test_write_local():
    """Test writing to LOCAL scope"""
    manager = UnifiedMemoryManager(node_id="test")
    entry = await manager.write("key1", "value1", MemoryScope.LOCAL)

    assert entry.id == "key1"
    assert entry.content == "value1"
    assert entry.scope == MemoryScope.LOCAL
    assert entry.created_by == "test"


@pytest.mark.asyncio
async def test_write_inherited_fails():
    """Test that writing to INHERITED scope fails"""
    manager = UnifiedMemoryManager(node_id="test")

    with pytest.raises(PermissionError):
        await manager.write("key1", "value1", MemoryScope.INHERITED)


@pytest.mark.asyncio
async def test_read_local():
    """Test reading from LOCAL scope"""
    manager = UnifiedMemoryManager(node_id="test")
    await manager.write("key1", "value1", MemoryScope.LOCAL)

    entry = await manager.read("key1")
    assert entry is not None
    assert entry.content == "value1"


@pytest.mark.asyncio
async def test_read_inherited_from_parent():
    """Test reading INHERITED scope from parent"""
    parent = UnifiedMemoryManager(node_id="parent")
    child = UnifiedMemoryManager(node_id="child", parent=parent)

    # Parent writes to SHARED
    await parent.write("shared_key", "shared_value", MemoryScope.SHARED)

    # Child reads as INHERITED
    entry = await child.read("shared_key", [MemoryScope.INHERITED])
    assert entry is not None
    assert entry.content == "shared_value"
    assert entry.scope == MemoryScope.INHERITED
