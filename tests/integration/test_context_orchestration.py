"""Integration tests for ContextOrchestrator with UnifiedMemoryManager"""
import pytest
from loom.memory.unified import UnifiedMemoryManager
from loom.memory.orchestrator import ContextOrchestrator
from loom.memory.task_context import MemoryContextSource
from loom.memory.tokenizer import EstimateCounter
from loom.protocol import Task
from loom.fractal.memory import MemoryScope


@pytest.mark.asyncio
async def test_orchestrator_with_unified_memory():
    """Test ContextOrchestrator using UnifiedMemoryManager"""
    # Create unified memory
    memory = UnifiedMemoryManager(node_id="test")

    # Add some tasks
    task1 = Task(task_id="t1", action="execute", parameters={"content": "task 1"}, session_id="s1")
    task2 = Task(task_id="t2", action="execute", parameters={"content": "task 2"}, session_id="s1")
    memory.add_task(task1)
    memory.add_task(task2)

    # Create context source
    source = MemoryContextSource(memory._loom_memory)

    # Create orchestrator
    counter = EstimateCounter()
    orchestrator = ContextOrchestrator(
        token_counter=counter,
        sources=[source],
        max_tokens=4000,
        system_prompt="Test system",
    )

    # Build context
    current = Task(task_id="t3", action="execute", parameters={"content": "current"}, session_id="s1")
    messages = await orchestrator.build_context(current)

    assert len(messages) > 0
    assert any("Test system" in m.get("content", "") for m in messages)
