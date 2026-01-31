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
