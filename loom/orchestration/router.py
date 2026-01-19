"""
Router Orchestrator - 路由编排器

基于公理A5（认知调度公理）：
实现智能路由模式，根据任务特征选择最合适的节点。

设计原则：
1. 智能路由 - 根据能力匹配选择节点
2. 单节点执行 - 一个任务由一个节点处理
3. 高效决策 - 快速选择最优节点
"""

from loom.orchestration.base import Orchestrator
from loom.protocol import NodeProtocol, Task, TaskStatus


class RouterOrchestrator(Orchestrator):
    """
    路由编排器 - 智能路由模式

    根据任务的action和节点的capabilities进行匹配，
    选择最合适的节点执行任务。
    """

    async def orchestrate(self, task: Task) -> Task:
        """
        路由并执行任务

        Args:
            task: 要执行的任务

        Returns:
            更新后的任务
        """
        if not self.nodes:
            task.status = TaskStatus.FAILED
            task.error = "No nodes available"
            return task

        # 选择节点
        selected_node = self._select_node(task)

        if not selected_node:
            task.status = TaskStatus.FAILED
            task.error = "No suitable node found"
            return task

        # 执行任务
        try:
            result_task = await selected_node.execute_task(task)
            return result_task
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            return task

    def _select_node(self, task: Task) -> NodeProtocol | None:
        """
        选择最合适的节点

        基于任务action和节点capabilities进行匹配。
        遵循最简原则：简单的关键词匹配 + 降级策略。

        Args:
            task: 任务

        Returns:
            选中的节点或None
        """
        if not self.nodes:
            return None

        # 从task.action提取能力需求
        action_lower = task.action.lower()
        required_capability = None

        if "tool" in action_lower or "use" in action_lower:
            required_capability = "tool_use"
        elif "plan" in action_lower:
            required_capability = "planning"
        elif "reflect" in action_lower:
            required_capability = "reflection"
        elif "multi" in action_lower or "agent" in action_lower:
            required_capability = "multi_agent"

        # 如果有明确的能力需求，尝试匹配
        if required_capability:
            for node in self.nodes:
                try:
                    card = node.get_capabilities()
                    if card and any(cap.value == required_capability for cap in card.capabilities):
                        return node
                except Exception:
                    # 节点可能没有实现get_capabilities，跳过
                    continue

        # 降级策略：返回第一个节点
        return self.nodes[0]
