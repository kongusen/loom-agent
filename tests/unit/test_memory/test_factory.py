"""
Memory Factory Unit Tests

测试记忆工厂的创建方法
"""

import pytest

from loom.memory.core import LoomMemory
from loom.memory.factory import MemoryFactory


class TestMemoryFactory:
    """测试MemoryFactory工厂类"""

    def test_create_default(self):
        """测试创建默认记忆系统"""
        memory = MemoryFactory.create_default("test-node")

        assert isinstance(memory, LoomMemory)
        assert memory.node_id == "test-node"

    def test_create_for_chat(self):
        """测试创建对话记忆系统"""
        memory = MemoryFactory.create_for_chat("chat-node")

        assert isinstance(memory, LoomMemory)
        assert memory.node_id == "chat-node"
        assert memory.max_l1_size == 30

    def test_create_for_task(self):
        """测试创建任务记忆系统"""
        memory = MemoryFactory.create_for_task("task-node")

        assert isinstance(memory, LoomMemory)
        assert memory.node_id == "task-node"
        assert memory.max_l1_size == 100

    def test_create_custom(self):
        """测试创建自定义记忆系统"""
        memory = MemoryFactory.create_custom(
            node_id="custom-node",
            max_l1_size=200,
            enable_l4_vectorization=False,
        )

        assert isinstance(memory, LoomMemory)
        assert memory.node_id == "custom-node"
        assert memory.max_l1_size == 200
