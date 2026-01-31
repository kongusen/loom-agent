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
