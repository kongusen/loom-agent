"""
Dispatcher - 事件调度器

运行时支持：事件的调度和分发。

设计原则：
1. 异步优先 - 所有操作都是async
2. 可扩展 - 支持中间件和拦截器
3. 高性能 - 高效的事件分发
"""

from __future__ import annotations

from loom.agent.card import NodeProtocol
from loom.events.event_bus import EventBus
from loom.runtime.task import Task


class Dispatcher:
    """
    事件调度器

    负责将任务调度到合适的节点执行。
    """

    def __init__(self, event_bus: EventBus):
        """
        初始化调度器

        Args:
            event_bus: 事件总线
        """
        self.event_bus = event_bus
        self.nodes: dict[str, NodeProtocol] = {}

    def register_node(self, node: NodeProtocol) -> None:
        """
        注册节点

        Args:
            node: 节点
        """
        self.nodes[node.node_id] = node

    def unregister_node(self, node_id: str) -> bool:
        """
        注销节点

        Args:
            node_id: 节点ID

        Returns:
            是否成功注销
        """
        if node_id in self.nodes:
            del self.nodes[node_id]
            return True
        return False

    async def dispatch(self, task: Task) -> Task:
        """
        调度任务

        Args:
            task: 任务

        Returns:
            执行后的任务
        """
        # 查找目标节点
        target_node = self.nodes.get(task.target_agent)

        if not target_node:
            # 通过事件总线发布
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Dispatch target '{task.target_agent}' not found in nodes. Publishing to EventBus as fallback."
            )

            return await self.event_bus.publish(task)

        # 直接执行
        return await target_node.execute_task(task)
