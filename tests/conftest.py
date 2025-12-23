"""
Pytest Configuration and Fixtures
"""

import pytest
import shutil
import tempfile
import os
from typing import Generator

from loom.api.main import LoomApp
from loom.infra.llm import MockLLMProvider
from loom.memory.hierarchical import HierarchicalMemory

@pytest.fixture
def app() -> LoomApp:
    """Returns a fresh LoomApp instance."""
    return LoomApp()

@pytest.fixture
def mock_llm() -> MockLLMProvider:
    """Returns a Mock LLM Provider."""
    return MockLLMProvider()

@pytest.fixture
def temp_memory_path() -> Generator[str, None, None]:
    """Returns a temporary directory for memory storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)
