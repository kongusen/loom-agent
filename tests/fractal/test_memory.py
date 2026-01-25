"""
Phase 1: Fractal Memory System Tests

Tests for MemoryScope, MemoryAccessPolicy, MemoryEntry, and FractalMemory.
"""

import pytest

from loom.fractal.memory import (
    FractalMemory,
    MemoryAccessPolicy,
    MemoryEntry,
    MemoryScope,
)


class TestMemoryScope:
    """Test MemoryScope enum"""

    def test_memory_scope_values(self) -> None:
        """Test that all memory scopes have correct values"""
        assert MemoryScope.LOCAL.value == "local"
        assert MemoryScope.SHARED.value == "shared"
        assert MemoryScope.INHERITED.value == "inherited"
        assert MemoryScope.GLOBAL.value == "global"

    def test_memory_scope_members(self) -> None:
        """Test that all expected members exist"""
        scopes = list(MemoryScope)
        assert len(scopes) == 4
        assert MemoryScope.LOCAL in scopes
        assert MemoryScope.SHARED in scopes
        assert MemoryScope.INHERITED in scopes
        assert MemoryScope.GLOBAL in scopes


class TestMemoryAccessPolicy:
    """Test MemoryAccessPolicy dataclass"""

    def test_policy_creation(self) -> None:
        """Test creating a memory access policy"""
        policy = MemoryAccessPolicy(
            scope=MemoryScope.LOCAL,
            readable=True,
            writable=True,
            propagate_up=False,
            propagate_down=False,
        )
        assert policy.scope == MemoryScope.LOCAL
        assert policy.readable is True
        assert policy.writable is True
        assert policy.propagate_up is False
        assert policy.propagate_down is False


class TestMemoryEntry:
    """Test MemoryEntry dataclass"""

    def test_entry_creation(self) -> None:
        """Test creating a memory entry"""
        entry = MemoryEntry(
            id="test-entry",
            content={"key": "value"},
            scope=MemoryScope.LOCAL,
        )
        assert entry.id == "test-entry"
        assert entry.content == {"key": "value"}
        assert entry.scope == MemoryScope.LOCAL


class TestFractalMemory:
    """Test FractalMemory class"""

    @pytest.fixture
    def memory(self) -> FractalMemory:
        """Create a FractalMemory instance for testing"""
        return FractalMemory(node_id="test-node")

    @pytest.mark.asyncio
    async def test_memory_creation(self, memory: FractalMemory) -> None:
        """Test creating a fractal memory instance"""
        assert memory.node_id == "test-node"
        assert memory.parent_memory is None

    @pytest.mark.asyncio
    async def test_write_and_read_local(self, memory: FractalMemory) -> None:
        """Test writing and reading local memory"""
        await memory.write(
            entry_id="test-1",
            content={"data": "test"},
            scope=MemoryScope.LOCAL,
        )

        entry = await memory.read("test-1")
        assert entry is not None
        assert entry.id == "test-1"
        assert entry.content == {"data": "test"}
        assert entry.scope == MemoryScope.LOCAL
