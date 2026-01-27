"""
Phase 3 功能测试

测试编排能力提升的核心功能：
1. 节点基类增强 (BaseNode)
2. 流水线构建器 (PipelineBuilder)
"""

import pytest

from loom.orchestration.base_node import BaseNode, NodeState
from loom.protocol import Task, TaskStatus

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


# ==================== Pipeline Builder 测试 ====================


class TestPipelineBuilder:
    """测试流水线构建器"""

    @pytest.mark.asyncio
    async def test_sequential_pipeline(self):
        """测试顺序执行流水线"""
        from loom.orchestration.pipeline_builder import PipelineBuilder

        # 创建测试节点
        class TestNode(BaseNode):
            def __init__(self, node_id: str, append_text: str):
                super().__init__(node_id)
                self.append_text = append_text

            async def _execute_impl(self, task: Task) -> Task:
                result = task.result or ""
                task.result = result + self.append_text
                task.status = TaskStatus.COMPLETED
                return task

        node1 = TestNode("node1", "A")
        node2 = TestNode("node2", "B")
        node3 = TestNode("node3", "C")

        # 构建流水线
        pipeline = PipelineBuilder().add(node1).then(node2).then(node3).build("test_pipeline")

        # 执行流水线
        task = Task(action="test", parameters={})
        result = await pipeline.execute_task(task)

        # 验证顺序执行
        assert result.status == TaskStatus.COMPLETED
        assert result.result == "ABC"

    @pytest.mark.asyncio
    async def test_parallel_pipeline(self):
        """测试并行执行流水线"""
        from loom.orchestration.pipeline_builder import PipelineBuilder

        # 创建测试节点
        class TestNode(BaseNode):
            def __init__(self, node_id: str, value: int):
                super().__init__(node_id)
                self.value = value

            async def _execute_impl(self, task: Task) -> Task:
                task.result = self.value
                task.status = TaskStatus.COMPLETED
                return task

        node1 = TestNode("node1", 1)
        node2 = TestNode("node2", 2)
        node3 = TestNode("node3", 3)

        # 构建并行流水线
        pipeline = PipelineBuilder().parallel([node1, node2, node3]).build("parallel_pipeline")

        # 执行流水线
        task = Task(action="test", parameters={})
        result = await pipeline.execute_task(task)

        # 验证并行执行
        assert result.status == TaskStatus.COMPLETED
        assert "parallel_results" in result.result
        assert len(result.result["parallel_results"]) == 3
        assert set(result.result["parallel_results"]) == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_conditional_pipeline(self):
        """测试条件分支流水线"""
        from loom.orchestration.pipeline_builder import PipelineBuilder

        # 创建测试节点
        class TestNode(BaseNode):
            def __init__(self, node_id: str, result_value: str):
                super().__init__(node_id)
                self.result_value = result_value

            async def _execute_impl(self, task: Task) -> Task:
                task.result = self.result_value
                task.status = TaskStatus.COMPLETED
                return task

        true_node = TestNode("true_node", "TRUE_PATH")
        false_node = TestNode("false_node", "FALSE_PATH")

        # 条件函数
        async def condition(task: Task) -> bool:
            return task.parameters.get("value", 0) > 5

        # 构建条件流水线
        pipeline = (
            PipelineBuilder()
            .conditional(condition, true_node, false_node)
            .build("conditional_pipeline")
        )

        # 测试条件为真
        task1 = Task(action="test", parameters={"value": 10})
        result1 = await pipeline.execute_task(task1)
        assert result1.result == "TRUE_PATH"

        # 测试条件为假
        task2 = Task(action="test", parameters={"value": 3})
        result2 = await pipeline.execute_task(task2)
        assert result2.result == "FALSE_PATH"

    @pytest.mark.asyncio
    async def test_mixed_pipeline(self):
        """测试混合流水线（顺序+并行+条件）"""
        from loom.orchestration.pipeline_builder import PipelineBuilder

        class TestNode(BaseNode):
            def __init__(self, node_id: str, value: str):
                super().__init__(node_id)
                self.value = value

            async def _execute_impl(self, task: Task) -> Task:
                task.result = self.value
                task.status = TaskStatus.COMPLETED
                return task

        node1 = TestNode("node1", "step1")
        node2 = TestNode("node2", "step2")
        node3 = TestNode("node3", "step3")

        # 构建混合流水线
        pipeline = PipelineBuilder().add(node1).parallel([node2, node3]).build("mixed_pipeline")

        # 执行流水线
        task = Task(action="test", parameters={})
        result = await pipeline.execute_task(task)

        # 验证执行成功
        assert result.status == TaskStatus.COMPLETED
