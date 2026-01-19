"""
Queryable Event Bus - 可查询事件总线

基于公理A2（事件主权）和A4（记忆层次）：
EventBus不仅是通信机制，更是"集体记忆"（Collective Memory）。

核心概念：
1. 所有事件都被记录在EventBus中
2. 节点可以查询EventBus获取历史事件
3. 实现分形结构的"集体潜意识"（Collective Unconscious）

设计原则：
1. 事件持久化 - 所有事件都被记录
2. 灵活查询 - 支持多种查询条件
3. 高效检索 - 使用索引优化查询性能
"""

from collections import defaultdict
from typing import Any

from loom.events.event_bus import EventBus
from loom.protocol import Task


class QueryableEventBus(EventBus):
    """
    可查询事件总线

    在EventBus基础上增加事件查询能力，实现"集体记忆"。
    """

    def __init__(self, transport=None, max_history: int = 1000):
        """
        初始化可查询事件总线

        Args:
            transport: 可选的传输层
            max_history: 最大历史事件数量（默认1000）
        """
        super().__init__(transport)

        # 事件历史（按时间顺序）
        self._event_history: list[Task] = []

        # 索引：按节点ID
        self._events_by_node: dict[str, list[Task]] = defaultdict(list)

        # 索引：按动作类型
        self._events_by_action: dict[str, list[Task]] = defaultdict(list)

        # 索引：按任务ID
        self._events_by_task: dict[str, list[Task]] = defaultdict(list)

        # 最大历史数量
        self._max_history = max_history

    async def publish(self, task: Task, wait_result: bool = True) -> Task:
        """
        发布任务（增强版 - 记录到历史）

        Args:
            task: 要发布的任务
            wait_result: 是否等待任务完成

        Returns:
            更新后的任务
        """
        # 调用父类的publish
        result_task = await super().publish(task, wait_result)

        # 记录到历史
        self._record_event(result_task)

        return result_task

    def _record_event(self, task: Task) -> None:
        """
        记录事件到历史

        Args:
            task: 任务事件
        """
        # 添加到历史
        self._event_history.append(task)

        # 更新索引
        node_id = task.parameters.get("node_id")
        if node_id:
            self._events_by_node[node_id].append(task)

        self._events_by_action[task.action].append(task)

        parent_task_id = task.parameters.get("parent_task_id")
        if parent_task_id:
            self._events_by_task[parent_task_id].append(task)

        # 限制历史大小
        if len(self._event_history) > self._max_history:
            # 移除最旧的事件
            old_task = self._event_history.pop(0)

            # 更新索引
            old_node_id = old_task.parameters.get("node_id")
            if old_node_id and old_node_id in self._events_by_node:
                self._events_by_node[old_node_id].remove(old_task)

            if old_task.action in self._events_by_action:
                self._events_by_action[old_task.action].remove(old_task)

    # ==================== 查询接口 ====================

    def query_by_node(
        self,
        node_id: str,
        action_filter: str | None = None,
        limit: int | None = None,
    ) -> list[Task]:
        """
        查询特定节点的事件

        Args:
            node_id: 节点ID
            action_filter: 可选的动作过滤（如 "node.thinking"）
            limit: 可选的结果数量限制

        Returns:
            事件列表
        """
        events = self._events_by_node.get(node_id, [])

        # 应用动作过滤
        if action_filter:
            events = [e for e in events if e.action == action_filter]

        # 应用数量限制
        if limit:
            events = events[-limit:]  # 返回最近的N个

        return events

    def query_by_action(
        self,
        action: str,
        node_filter: str | None = None,
        limit: int | None = None,
    ) -> list[Task]:
        """
        查询特定动作类型的事件

        Args:
            action: 动作类型（如 "node.thinking"）
            node_filter: 可选的节点过滤
            limit: 可选的结果数量限制

        Returns:
            事件列表
        """
        events = self._events_by_action.get(action, [])

        # 应用节点过滤
        if node_filter:
            events = [e for e in events if e.parameters.get("node_id") == node_filter]

        # 应用数量限制
        if limit:
            events = events[-limit:]

        return events

    def query_by_task(
        self,
        task_id: str,
        action_filter: str | None = None,
    ) -> list[Task]:
        """
        查询特定任务的所有事件

        Args:
            task_id: 任务ID
            action_filter: 可选的动作过滤

        Returns:
            事件列表
        """
        events = self._events_by_task.get(task_id, [])

        # 应用动作过滤
        if action_filter:
            events = [e for e in events if e.action == action_filter]

        return events

    def query_recent(
        self,
        limit: int = 10,
        action_filter: str | None = None,
        node_filter: str | None = None,
    ) -> list[Task]:
        """
        查询最近的事件

        Args:
            limit: 结果数量限制
            action_filter: 可选的动作过滤
            node_filter: 可选的节点过滤

        Returns:
            事件列表
        """
        events = self._event_history[-limit:]

        # 应用过滤
        if action_filter:
            events = [e for e in events if e.action == action_filter]

        if node_filter:
            events = [e for e in events if e.parameters.get("node_id") == node_filter]

        return events

    def query_thinking_process(
        self,
        node_id: str | None = None,
        task_id: str | None = None,
        limit: int | None = None,
    ) -> list[str]:
        """
        查询思考过程（提取思考内容）

        Args:
            node_id: 可选的节点过滤
            task_id: 可选的任务过滤
            limit: 可选的结果数量限制

        Returns:
            思考内容列表
        """
        # 查询thinking事件
        if task_id:
            events = self.query_by_task(task_id, action_filter="node.thinking")
        elif node_id:
            events = self.query_by_node(node_id, action_filter="node.thinking", limit=limit)
        else:
            events = self.query_by_action("node.thinking", limit=limit)

        # 提取思考内容
        thoughts = []
        for event in events:
            content = event.parameters.get("content", "")
            if content:
                thoughts.append(content)

        return thoughts

    def get_collective_memory(
        self,
        action_types: list[str] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """
        获取集体记忆（Collective Memory）

        返回所有节点的思考过程和工具调用，形成"集体潜意识"。

        Args:
            action_types: 可选的动作类型列表（默认：thinking和tool_call）
            limit: 每种类型的最大数量

        Returns:
            集体记忆字典
        """
        if action_types is None:
            action_types = ["node.thinking", "node.tool_call"]

        collective_memory = {}

        for action_type in action_types:
            events = self.query_by_action(action_type, limit=limit)

            # 按节点分组
            by_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for event in events:
                node_id = event.parameters.get("node_id", "unknown")
                by_node[node_id].append(
                    {
                        "content": event.parameters.get("content"),
                        "timestamp": event.created_at.isoformat() if event.created_at else None,
                        "metadata": event.parameters.get("metadata", {}),
                    }
                )

            collective_memory[action_type] = dict(by_node)

        return collective_memory

    def clear_history(self) -> None:
        """清空历史记录"""
        self._event_history.clear()
        self._events_by_node.clear()
        self._events_by_action.clear()
        self._events_by_task.clear()
