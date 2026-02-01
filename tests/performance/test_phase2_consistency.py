"""
Phase 2 Consistency Testing

Tests consistency issues mentioned in the implementation plan:
1. Parent-child node data synchronization
2. Concurrent writes causing data loss
3. Memory version conflicts
"""

import asyncio

import pytest

from loom.fractal.memory import MemoryScope
from loom.memory.manager import MemoryManager


@pytest.mark.asyncio
async def test_parent_child_synchronization():
    """Test that parent-child memory stays synchronized"""
    # Create parent and child
    parent = MemoryManager(node_id="parent")
    child = MemoryManager(node_id="child", parent=parent)

    # Parent writes to SHARED scope
    await parent.write("shared_key", "parent_value", MemoryScope.SHARED)

    # Child should be able to read it as INHERITED
    entry = await child.read("shared_key", [MemoryScope.INHERITED])
    assert entry is not None, "Child cannot read parent's SHARED memory"
    assert entry.content == "parent_value", "Child read wrong value from parent"

    # Child writes to SHARED scope
    await child.write("child_key", "child_value", MemoryScope.SHARED)

    # Parent should be able to read it
    entry = await parent.read("child_key", [MemoryScope.SHARED])
    assert entry is not None, "Parent cannot read child's SHARED memory"
    assert entry.content == "child_value", "Parent read wrong value from child"

    print("✓ Parent-child synchronization working correctly")


@pytest.mark.asyncio
async def test_concurrent_writes_no_data_loss():
    """Test that concurrent writes don't cause data loss"""
    memory = MemoryManager(node_id="concurrent-test")

    async def write_entry(key: str, value: str):
        """Write an entry"""
        await memory.write(key, value, MemoryScope.LOCAL)

    # Write 20 entries concurrently
    keys = [f"key_{i}" for i in range(20)]
    values = [f"value_{i}" for i in range(20)]

    await asyncio.gather(
        *[write_entry(key, value) for key, value in zip(keys, values, strict=False)]
    )

    # Verify all entries were written
    for key, expected_value in zip(keys, values, strict=False):
        entry = await memory.read(key)
        assert entry is not None, f"Entry {key} was lost during concurrent writes"
        assert entry.content == expected_value, f"Entry {key} has wrong value"

    print("✓ No data loss in concurrent writes (20/20 entries preserved)")
