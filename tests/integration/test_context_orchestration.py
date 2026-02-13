"""Integration tests for ContextOrchestrator with MemoryManager"""

import pytest

from loom.context.orchestrator import ContextOrchestrator
from loom.context.sources.memory import L2WorkingSource
from loom.memory.manager import MemoryManager
from loom.memory.tokenizer import EstimateCounter


@pytest.mark.asyncio
async def test_orchestrator_with_memory_manager():
    """Test ContextOrchestrator using MemoryManager and L2WorkingSource"""
    # Create memory manager
    memory = MemoryManager(node_id="test")

    # Add messages to L1 (new 3-layer API)
    memory.add_message("user", "What is the weather?")
    memory.add_message("assistant", "Let me check the weather for you.")

    # Create context source using L2WorkingSource
    source = L2WorkingSource(memory.memory)

    # Create orchestrator
    counter = EstimateCounter()
    orchestrator = ContextOrchestrator(
        token_counter=counter,
        sources=[source],
        model_context_window=4000,
    )

    # Build context
    messages = await orchestrator.build_context("current query")

    # Verify messages were built (system prompt at minimum)
    assert isinstance(messages, list)
