"""Tests for ContextOrchestrator"""
import pytest
from loom.memory.orchestrator import ContextOrchestrator
from loom.memory.tokenizer import EstimateCounter
from loom.protocol import Task


def test_init_basic():
    """Test basic initialization"""
    counter = EstimateCounter()
    orchestrator = ContextOrchestrator(
        token_counter=counter,
        sources=[],
        max_tokens=4000,
    )

    assert orchestrator.max_tokens == 4000
    assert orchestrator.budgeter is not None
    assert orchestrator.converter is not None


@pytest.mark.asyncio
async def test_build_context_basic():
    """Test basic context building"""
    from loom.memory.task_context import MemoryContextSource
    from loom.memory.core import LoomMemory

    counter = EstimateCounter()
    memory = LoomMemory(node_id="test")
    source = MemoryContextSource(memory)

    orchestrator = ContextOrchestrator(
        token_counter=counter,
        sources=[source],
        max_tokens=4000,
        system_prompt="You are a helpful assistant",
    )

    task = Task(task_id="task1", action="execute", parameters={"content": "test"})
    messages = await orchestrator.build_context(task)

    assert len(messages) > 0
    assert messages[0]["role"] == "system"
    assert "helpful assistant" in messages[0]["content"]
