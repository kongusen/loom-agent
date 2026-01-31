"""Integration tests for UnifiedMemoryManager"""
import pytest
from loom.memory.unified import UnifiedMemoryManager
from loom.fractal.memory import MemoryScope
from loom.protocol import Task


@pytest.mark.asyncio
async def test_parent_child_memory_sharing():
    """Test complete parent-child memory sharing workflow"""
    # Create parent and child
    parent = UnifiedMemoryManager(node_id="parent")
    child = UnifiedMemoryManager(node_id="child", parent=parent)

    # Parent writes to SHARED scope
    await parent.write("goal", "Analyze codebase", MemoryScope.SHARED)

    # Child can read as INHERITED
    goal = await child.read("goal", [MemoryScope.INHERITED])
    assert goal is not None
    assert goal.content == "Analyze codebase"

    # Child writes to LOCAL scope
    await child.write("finding", "Found bug", MemoryScope.LOCAL)

    # Child can read its own LOCAL memory
    finding = await child.read("finding", [MemoryScope.LOCAL])
    assert finding is not None
    assert finding.content == "Found bug"

    # Parent cannot read child's LOCAL memory
    private = await parent.read("finding")
    assert private is None


@pytest.mark.asyncio
async def test_loom_memory_compatibility():
    """Test that LoomMemory interface still works"""
    manager = UnifiedMemoryManager(node_id="test")

    # Add task via LoomMemory interface
    task = Task(task_id="task1", action="execute", parameters={"content": "test"})
    manager.add_task(task)

    # Retrieve via LoomMemory interface
    l1_tasks = manager.get_l1_tasks(limit=10)
    assert len(l1_tasks) == 1
    assert l1_tasks[0].task_id == "task1"
