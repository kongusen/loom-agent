"""Integration tests for ContextOrchestrator with MemoryManager"""

import pytest

from loom.memory.manager import MemoryManager
from loom.context.orchestrator import ContextOrchestrator
from loom.context.sources.memory import L1RecentSource
from loom.memory.tokenizer import EstimateCounter
from loom.runtime import Task


@pytest.mark.asyncio
async def test_orchestrator_with_memory_manager():
    """Test ContextOrchestrator using MemoryManager"""
    # Create memory manager
    memory = MemoryManager(node_id="test")

    # Add some tasks
    task1 = Task(task_id="t1", action="execute", parameters={"content": "task 1"}, session_id="s1")
    task2 = Task(task_id="t2", action="execute", parameters={"content": "task 2"}, session_id="s1")
    memory.add_task(task1)
    memory.add_task(task2)

    # Create context source using L1RecentSource
    source = L1RecentSource(memory._loom_memory, session_id="s1")

    # Create orchestrator with correct parameters
    counter = EstimateCounter()
    orchestrator = ContextOrchestrator(
        token_counter=counter,
        sources=[source],
        model_context_window=4000,
    )

    # Build context
    current = Task(
        task_id="t3", action="execute", parameters={"content": "current"}, session_id="s1"
    )
    messages = await orchestrator.build_context(current)

    # Verify messages were built
    assert isinstance(messages, list)
