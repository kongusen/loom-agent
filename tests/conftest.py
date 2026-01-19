"""
Pytest 配置和共享 Fixtures

提供测试所需的通用fixtures和配置。
"""

import pytest

from loom.memory.tokenizer import EstimateCounter
from loom.memory.types import MemoryTier, MemoryType, MemoryUnit
from tests.api_config import api_config, get_embedding_config, get_openai_config


@pytest.fixture
def estimate_counter():
    """提供估算计数器"""
    return EstimateCounter()


@pytest.fixture
def sample_messages():
    """提供示例消息列表"""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
        {"role": "user", "content": "Can you help me with a task?"},
        {"role": "assistant", "content": "Of course! What do you need help with?"},
    ]


@pytest.fixture
def sample_memory_units():
    """提供示例记忆单元列表"""
    return [
        MemoryUnit(
            id="unit-1",
            content="System prompt: You are a helpful assistant.",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE,
            importance=1.0,
        ),
        MemoryUnit(
            id="unit-2",
            content="User: Hello, how are you?",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE,
            importance=0.7,
        ),
        MemoryUnit(
            id="unit-3",
            content="Assistant: I'm doing well, thank you!",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE,
            importance=0.6,
        ),
        MemoryUnit(
            id="unit-4",
            content="User: Can you help me with a task?",
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE,
            importance=0.8,
        ),
    ]


@pytest.fixture
def long_text():
    """提供长文本用于token计数测试"""
    return (
        """
    This is a longer text that will be used to test token counting functionality.
    It contains multiple sentences and should result in a reasonable token count.
    The purpose is to verify that our token counters work correctly with longer inputs.
    """
        * 10
    )


# ============================================================================
# API测试相关 Fixtures
# ============================================================================


@pytest.fixture
def api_test_config():
    """提供API测试配置"""
    return api_config


@pytest.fixture
def openai_config():
    """提供OpenAI配置字典"""
    return get_openai_config()


@pytest.fixture
def embedding_config():
    """提供Embedding配置字典"""
    return get_embedding_config()
