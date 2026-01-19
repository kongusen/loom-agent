"""
Mock Providers for Testing

提供测试所需的 Mock 对象，包括 LLM Provider、Event Bus 等。
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.events import EventBus
from loom.memory import LoomMemory


@pytest.fixture
def mock_llm_provider():
    """
    Mock LLM Provider

    提供一个模拟的 LLM Provider，用于测试不需要真实 LLM 调用的场景。
    """
    provider = Mock()
    provider.chat = AsyncMock(return_value="Mock LLM response")
    provider.stream = AsyncMock(return_value=["Mock", " stream", " response"])
    return provider


@pytest.fixture
def mock_event_bus():
    """
    Mock Event Bus

    提供一个真实的 Event Bus 实例，用于测试事件相关功能。
    """
    return EventBus()


@pytest.fixture
def mock_memory():
    """
    Mock Memory System

    提供一个真实的 Memory 实例，用于测试记忆相关功能。
    """
    return LoomMemory(node_id="test_memory")
