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
