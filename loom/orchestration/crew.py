"""
Crew Orchestrator - 团队编排器

基于公理A5（认知调度公理）：
实现团队协作模式，多个节点协同完成任务。

设计原则：
1. 协作优先 - 多节点协同工作
2. 并行执行 - 充分利用并行能力
3. 结果聚合 - 整合多个节点的输出
"""

import asyncio
from typing import Any

from loom.orchestration.base import Orchestrator
from loom.protocol import Task, TaskStatus


class CrewOrchestrator(Orchestrator):
    """
    团队编排器 - 多节点协作模式

    将任务分发给多个节点并行执行，
    然后聚合结果。
    """

    async def orchestrate(self, task: Task) -> Task:
        """
        团队协作执行任务

        Args:
            task: 要执行的任务

        Returns:
            更新后的任务
        """
        if not self.nodes:
            task.status = TaskStatus.FAILED
            task.error = "No nodes available"
            return task

        try:
            # 并行执行
            results = await asyncio.gather(
                *[node.execute_task(task) for node in self.nodes], return_exceptions=True
            )

            # 聚合结果
            task.result = self._aggregate_results(results)
            task.status = TaskStatus.COMPLETED
            return task

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            return task

    def _aggregate_results(self, results: list) -> dict:
        """
        聚合多个节点的结果

        Args:
            results: 结果列表

        Returns:
            聚合后的结果
        """
        aggregated: dict[str, list[Any]] = {"results": [], "errors": []}

        for result in results:
            if isinstance(result, Exception):
                aggregated["errors"].append(str(result))
            elif isinstance(result, Task):
                aggregated["results"].append(result.result)

        return aggregated
