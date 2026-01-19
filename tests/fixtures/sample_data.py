"""
Sample Data Generators for Testing

提供测试所需的示例数据生成器。
"""

import pytest

from loom.memory.types import MemoryTier, MemoryType, MemoryUnit


@pytest.fixture
def sample_messages() -> list[dict]:
    """
    生成示例消息列表

    Returns:
        消息列表
    """
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
        {"role": "user", "content": "Can you help me with a task?"},
        {"role": "assistant", "content": "Of course! What do you need help with?"},
    ]


@pytest.fixture
def sample_memory_units() -> list[MemoryUnit]:
    """
    生成示例记忆单元列表

    Returns:
        记忆单元列表
    """
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
    ]
