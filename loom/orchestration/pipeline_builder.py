"""
Pipeline Builder - 流水线构建器

基于公理A5（认知调度公理）：
提供流式API构建复杂的节点编排流程。

功能：
- 顺序执行（Sequential）
- 并行执行（Parallel）
- 条件分支（Conditional）
- 流式API（Fluent API）

设计原则：
1. 直观易用 - 链式调用，语义清晰
2. 灵活组合 - 支持多种执行模式
3. 协议兼容 - Pipeline 实现 NodeProtocol
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any

from loom.protocol import AgentCard, NodeProtocol, Task, TaskStatus


class StepType(str, Enum):
    """流水线步骤类型"""

    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"  # 并行执行
    CONDITIONAL = "conditional"  # 条件分支


class PipelineStep(ABC):
    """
    流水线步骤抽象基类

    定义流水线中单个步骤的执行接口。
    """

    def __init__(self, step_type: StepType):
        """
        初始化步骤

        Args:
            step_type: 步骤类型
        """
        self.step_type = step_type

    @abstractmethod
    async def execute(self, task: Task) -> Task:
        """
        执行步骤

        Args:
            task: 输入任务

        Returns:
            输出任务
        """
        pass


class SequentialStep(PipelineStep):
    """
    顺序执行步骤

    按顺序执行一个节点，前一个任务的输出作为下一个任务的输入。
    """

    def __init__(self, node: NodeProtocol):
        """
        初始化顺序步骤

        Args:
            node: 要执行的节点
        """
        super().__init__(StepType.SEQUENTIAL)
        self.node = node

    async def execute(self, task: Task) -> Task:
        """
        执行节点

        Args:
            task: 输入任务

        Returns:
            节点执行后的任务
        """
        return await self.node.execute_task(task)


class ParallelStep(PipelineStep):
    """
    并行执行步骤

    并行执行多个节点，聚合所有结果。
    """

    def __init__(self, nodes: list[NodeProtocol]):
        """
        初始化并行步骤

        Args:
            nodes: 要并行执行的节点列表
        """
        super().__init__(StepType.PARALLEL)
        self.nodes = nodes

    async def execute(self, task: Task) -> Task:
        """
        并行执行所有节点

        Args:
            task: 输入任务

        Returns:
            聚合结果的任务
        """
        if not self.nodes:
            task.status = TaskStatus.FAILED
            task.error = "No nodes in parallel step"
            return task

        try:
            # 为每个节点创建任务副本（浅拷贝优化）
            # 只拷贝Task对象本身，共享parameters等数据，大幅减少内存占用
            tasks = [
                Task(
                    task_id=f"{task.task_id}_parallel_{i}",
                    action=task.action,
                    parameters=task.parameters,  # 共享引用，避免深拷贝
                    target_agent=task.target_agent,
                    metadata=task.metadata.copy() if task.metadata else {},
                )
                for i in range(len(self.nodes))
            ]

            # 并行执行所有节点
            results = await asyncio.gather(
                *[node.execute_task(t) for node, t in zip(self.nodes, tasks, strict=False)],
                return_exceptions=True,
            )

            # 聚合结果
            aggregated: dict[str, list[Any]] = {"parallel_results": [], "errors": []}

            for result in results:
                if isinstance(result, Exception):
                    aggregated["errors"].append(str(result))
                elif isinstance(result, Task):
                    aggregated["parallel_results"].append(result.result)

            task.result = aggregated
            task.status = TaskStatus.COMPLETED
            return task

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            return task


class ConditionalStep(PipelineStep):
    """
    条件分支步骤

    根据条件函数的结果选择执行不同的节点。
    """

    def __init__(
        self,
        condition: Callable[[Task], Awaitable[bool]],
        true_node: NodeProtocol,
        false_node: NodeProtocol,
    ):
        """
        初始化条件步骤

        Args:
            condition: 条件判断函数（异步）
            true_node: 条件为真时执行的节点
            false_node: 条件为假时执行的节点
        """
        super().__init__(StepType.CONDITIONAL)
        self.condition = condition
        self.true_node = true_node
        self.false_node = false_node

    async def execute(self, task: Task) -> Task:
        """
        根据条件执行相应节点

        Args:
            task: 输入任务

        Returns:
            选中节点执行后的任务
        """
        try:
            # 评估条件
            condition_result = await self.condition(task)

            # 选择节点
            selected_node = self.true_node if condition_result else self.false_node

            # 执行选中的节点
            return await selected_node.execute_task(task)

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = f"Conditional step failed: {str(e)}"
            return task


class Pipeline:
    """
    流水线执行器

    实现 NodeProtocol，可以作为节点使用。
    按顺序执行所有步骤，支持顺序、并行和条件执行。
    """

    def __init__(self, pipeline_id: str, steps: list[PipelineStep]):
        """
        初始化流水线

        Args:
            pipeline_id: 流水线ID
            steps: 执行步骤列表
        """
        self.node_id = pipeline_id
        self.source_uri = f"pipeline://{pipeline_id}"
        self.steps = steps
        self.agent_card = AgentCard(
            agent_id=pipeline_id,
            name=pipeline_id,
            description=f"Pipeline with {len(steps)} steps",
            capabilities=[],
        )

    async def process(self, event: Any) -> Any:
        """
        处理事件（委托给 execute_task）

        Args:
            event: 事件对象

        Returns:
            处理结果
        """
        if isinstance(event, Task):
            result_task = await self.execute_task(event)
            return result_task.result
        return {"status": "processed", "pipeline_id": self.node_id}

    async def execute_task(self, task: Task) -> Task:
        """
        执行流水线

        按顺序执行所有步骤，每个步骤的输出作为下一个步骤的输入。

        Args:
            task: 输入任务

        Returns:
            最终任务
        """
        if not self.steps:
            task.status = TaskStatus.COMPLETED
            task.result = {"message": "Empty pipeline"}
            return task

        current_task = task

        try:
            # 按顺序执行所有步骤
            for i, step in enumerate(self.steps):
                current_task = await step.execute(current_task)

                # 如果某个步骤失败，停止执行
                if current_task.status == TaskStatus.FAILED:
                    current_task.error = f"Pipeline failed at step {i + 1}: {current_task.error}"
                    return current_task

            return current_task

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = f"Pipeline execution failed: {str(e)}"
            return task

    def get_capabilities(self) -> AgentCard:
        """
        获取能力声明

        Returns:
            AgentCard对象
        """
        return self.agent_card


class PipelineBuilder:
    """
    流水线构建器

    提供流式API构建复杂的节点编排流程。

    示例用法：
        pipeline = (PipelineBuilder()
            .add(node1)
            .then(node2)
            .parallel([node3, node4])
            .conditional(condition_fn, node5, node6)
            .build("my_pipeline"))
    """

    def __init__(self):
        """初始化构建器"""
        self.steps: list[PipelineStep] = []

    def add(self, node: NodeProtocol) -> "PipelineBuilder":
        """
        添加顺序执行节点

        Args:
            node: 要添加的节点

        Returns:
            构建器自身（支持链式调用）
        """
        self.steps.append(SequentialStep(node))
        return self

    def then(self, node: NodeProtocol) -> "PipelineBuilder":
        """
        添加顺序执行节点（语义别名）

        Args:
            node: 要添加的节点

        Returns:
            构建器自身（支持链式调用）
        """
        return self.add(node)

    def parallel(self, nodes: list[NodeProtocol]) -> "PipelineBuilder":
        """
        添加并行执行步骤

        Args:
            nodes: 要并行执行的节点列表

        Returns:
            构建器自身（支持链式调用）
        """
        self.steps.append(ParallelStep(nodes))
        return self

    def conditional(
        self,
        condition: Callable[[Task], Awaitable[bool]],
        true_node: NodeProtocol,
        false_node: NodeProtocol,
    ) -> "PipelineBuilder":
        """
        添加条件分支步骤

        Args:
            condition: 条件判断函数（异步）
            true_node: 条件为真时执行的节点
            false_node: 条件为假时执行的节点

        Returns:
            构建器自身（支持链式调用）
        """
        self.steps.append(ConditionalStep(condition, true_node, false_node))
        return self

    def build(self, pipeline_id: str = "pipeline") -> Pipeline:
        """
        构建流水线

        Args:
            pipeline_id: 流水线ID

        Returns:
            构建好的流水线对象
        """
        return Pipeline(pipeline_id, self.steps)
