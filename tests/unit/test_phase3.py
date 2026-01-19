"""
Phase 3 功能测试

测试编排能力提升的四个核心功能：
1. 节点基类增强 (BaseNode)
2. 流水线构建器 (PipelineBuilder)
3. 模板管理器 (TemplateManager)
4. 置信度评估器 (ConfidenceEvaluator)
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


# ==================== Confidence Evaluator 测试 ====================


class TestConfidenceEvaluator:
    """测试置信度评估器"""

    @pytest.mark.asyncio
    async def test_confidence_score_creation(self):
        """测试置信度评分创建"""
        from loom.orchestration.confidence_evaluator import ConfidenceScore

        score = ConfidenceScore(
            overall=0.85,
            dimensions={"completeness": 0.9, "correctness": 0.8},
            reasons=["High quality result"],
        )

        assert score.overall == 0.85
        assert score.dimensions["completeness"] == 0.9
        assert len(score.reasons) == 1

    @pytest.mark.asyncio
    async def test_confidence_score_bounds(self):
        """测试置信度评分边界"""
        from loom.orchestration.confidence_evaluator import ConfidenceScore

        # 测试超出上界
        score1 = ConfidenceScore(overall=1.5)
        assert score1.overall == 1.0

        # 测试超出下界
        score2 = ConfidenceScore(overall=-0.5)
        assert score2.overall == 0.0

    @pytest.mark.asyncio
    async def test_status_based_strategy(self):
        """测试基于状态的评估策略"""
        from loom.orchestration.confidence_evaluator import StatusBasedStrategy

        strategy = StatusBasedStrategy()

        # 测试完成状态
        task_completed = Task(action="test", parameters={})
        task_completed.status = TaskStatus.COMPLETED
        score = await strategy.evaluate(task_completed)
        assert score == 1.0

        # 测试失败状态
        task_failed = Task(action="test", parameters={})
        task_failed.status = TaskStatus.FAILED
        score = await strategy.evaluate(task_failed)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_error_presence_strategy(self):
        """测试基于错误的评估策略"""
        from loom.orchestration.confidence_evaluator import ErrorPresenceStrategy

        strategy = ErrorPresenceStrategy()

        # 测试无错误
        task_no_error = Task(action="test", parameters={})
        score = await strategy.evaluate(task_no_error)
        assert score == 1.0

        # 测试有错误
        task_with_error = Task(action="test", parameters={})
        task_with_error.error = "Something went wrong"
        score = await strategy.evaluate(task_with_error)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_result_length_strategy(self):
        """测试基于结果长度的评估策略"""
        from loom.orchestration.confidence_evaluator import ResultLengthStrategy

        strategy = ResultLengthStrategy(min_length=10)

        # 测试长结果
        task_long = Task(action="test", parameters={})
        task_long.result = "This is a long result with enough content"
        score = await strategy.evaluate(task_long)
        assert score == 1.0

        # 测试短结果
        task_short = Task(action="test", parameters={})
        task_short.result = "Short"
        score = await strategy.evaluate(task_short)
        assert score < 1.0

        # 测试空结果
        task_empty = Task(action="test", parameters={})
        task_empty.result = None
        score = await strategy.evaluate(task_empty)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_confidence_evaluator_with_default_strategies(self):
        """测试使用默认策略的评估器"""
        from loom.orchestration.confidence_evaluator import ConfidenceEvaluator

        evaluator = ConfidenceEvaluator()

        # 测试成功任务
        task_success = Task(action="test", parameters={})
        task_success.status = TaskStatus.COMPLETED
        task_success.result = "This is a successful result with good content"

        score = await evaluator.evaluate(task_success)
        assert score.overall > 0.7
        assert "status" in score.dimensions
        assert "error_presence" in score.dimensions

    @pytest.mark.asyncio
    async def test_confidence_evaluator_retry_decision(self):
        """测试重试决策"""
        from loom.orchestration.confidence_evaluator import ConfidenceEvaluator, ConfidenceScore

        evaluator = ConfidenceEvaluator(retry_threshold=0.6, escalate_threshold=0.4)

        # 测试应该重试（0.4 < score < 0.6）
        score_retry = ConfidenceScore(overall=0.5)
        assert evaluator.should_retry(score_retry) is True
        assert evaluator.should_escalate(score_retry) is False

        # 测试应该升级（score <= 0.4）
        score_escalate = ConfidenceScore(overall=0.3)
        assert evaluator.should_retry(score_escalate) is False
        assert evaluator.should_escalate(score_escalate) is True

        # 测试不需要重试或升级（score >= 0.6）
        score_good = ConfidenceScore(overall=0.8)
        assert evaluator.should_retry(score_good) is False
        assert evaluator.should_escalate(score_good) is False

    @pytest.mark.asyncio
    async def test_confidence_evaluator_custom_strategies(self):
        """测试自定义评估策略"""
        from loom.orchestration.confidence_evaluator import (
            ConfidenceEvaluator,
            EvaluationStrategy,
        )

        # 创建自定义策略
        class AlwaysHighStrategy(EvaluationStrategy):
            def __init__(self):
                super().__init__(name="always_high", weight=1.0)

            async def evaluate(self, task: Task) -> float:
                return 0.9

        evaluator = ConfidenceEvaluator(strategies=[AlwaysHighStrategy()])

        task = Task(action="test", parameters={})
        score = await evaluator.evaluate(task)

        assert score.overall == 0.9
        assert "always_high" in score.dimensions
