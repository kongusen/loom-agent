"""
Phase 3 功能测试

测试编排能力提升的核心功能：
1. 节点基类增强 (BaseNode)
2. 流水线构建器 (PipelineBuilder)
"""

import pytest

from loom.agent import BaseNode, NodeState
from loom.runtime import Task, TaskStatus

# ==================== BaseNode 测试 ====================


class TestBaseNode:
    """测试增强的节点基类"""

    @pytest.mark.asyncio
    async def test_node_initialization(self):
        """测试节点初始化"""
        node = BaseNode(node_id="test_node", node_type="test")

        assert node.node_id == "test_node"
        assert node.node_type == "test"
        assert node.state == NodeState.IDLE
        assert node.stats["execution_count"] == 0

    @pytest.mark.asyncio
    async def test_node_lifecycle_hooks(self):
        """测试生命周期钩子"""

        class CustomNode(BaseNode):
            def __init__(self):
                super().__init__("custom_node")
                self.started = False
                self.completed = False
                self.errored = False

            async def on_start(self, task: Task):
                await super().on_start(task)
                self.started = True

            async def on_complete(self, task: Task):
                await super().on_complete(task)
                self.completed = True

            async def on_error(self, task: Task, error: Exception):
                await super().on_error(task, error)
                self.errored = True

        node = CustomNode()
        task = Task(action="test", parameters={"data": "test"})

        # 执行任务
        await node.execute_task(task)

        # 验证钩子被调用
        assert node.started is True
        assert node.completed is True
        assert node.errored is False

    @pytest.mark.asyncio
    async def test_node_state_management(self):
        """测试状态管理"""
        node = BaseNode("test_node")
        task = Task(action="test", parameters={})

        # 初始状态
        assert node.get_state() == NodeState.IDLE

        # 执行任务后状态变化
        await node.execute_task(task)
        assert node.get_state() == NodeState.COMPLETED

        # 重置状态
        node.reset_state()
        assert node.get_state() == NodeState.IDLE

    @pytest.mark.asyncio
    async def test_node_statistics(self):
        """测试执行统计"""
        node = BaseNode("test_node")

        # 执行多次任务
        for i in range(3):
            task = Task(action="test", parameters={"index": i})
            await node.execute_task(task)

        # 获取统计信息
        stats = node.get_stats()

        assert stats["execution_count"] == 3
        assert stats["success_count"] == 3
        assert stats["failure_count"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["avg_duration"] > 0

    @pytest.mark.asyncio
    async def test_node_error_handling(self):
        """测试错误处理"""

        class FailingNode(BaseNode):
            async def _execute_impl(self, task: Task) -> Task:
                raise ValueError("Test error")

        node = FailingNode("failing_node")
        task = Task(action="test", parameters={})

        # 执行会失败的任务
        result = await node.execute_task(task)

        # 验证错误处理
        assert result.status == TaskStatus.FAILED
        assert "Test error" in result.error
        assert node.get_state() == NodeState.FAILED
        assert node.stats["failure_count"] == 1

    @pytest.mark.asyncio
    async def test_node_reset_stats(self):
        """测试重置统计"""
        node = BaseNode("test_node")

        # 执行任务
        task = Task(action="test", parameters={})
        await node.execute_task(task)

        # 验证有统计数据
        assert node.stats["execution_count"] == 1

        # 重置统计
        node.reset_stats()

        # 验证统计被清空
        assert node.stats["execution_count"] == 0
        assert node.stats["success_count"] == 0
        assert node.stats["total_duration"] == 0.0
