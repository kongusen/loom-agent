"""
Context Builder - 上下文构建器

基于公理A4（记忆层次）和A5（认知调度）：
从EventBus的"集体记忆"中构建节点的上下文。

核心概念：
1. 节点不是被动接收上下文
2. 节点主动从EventBus搜索需要的信息
3. 实现智能上下文构建

设计原则：
1. 按需构建 - 根据节点需求构建上下文
2. 智能过滤 - 只提取相关信息
3. 时间感知 - 考虑事件的时间顺序
"""

from typing import Any

from loom.events.queryable_event_bus import QueryableEventBus


class ContextBuilder:
    """
    上下文构建器

    从EventBus的集体记忆中构建节点的上下文。
    """

    def __init__(self, event_bus: QueryableEventBus):
        """
        初始化上下文构建器

        Args:
            event_bus: 可查询事件总线
        """
        self.event_bus = event_bus

    def build_context_for_node(
        self,
        node_id: str,
        task_id: str,
        include_siblings: bool = True,
        include_parent: bool = True,
        max_events: int = 20,
    ) -> dict[str, Any]:
        """
        为节点构建上下文

        Args:
            node_id: 节点ID
            task_id: 当前任务ID
            include_siblings: 是否包含兄弟节点的信息
            include_parent: 是否包含父节点的信息
            max_events: 最大事件数量

        Returns:
            上下文字典
        """
        context: dict[str, Any] = {
            "node_id": node_id,
            "task_id": task_id,
            "self_history": [],
            "sibling_insights": [],
            "parent_context": [],
            "collective_memory": {},
        }

        # 1. 自己的历史
        self_events = self.event_bus.query_by_node(
            node_id,
            action_filter="node.thinking",
            limit=max_events,
        )
        context["self_history"] = [
            {
                "content": str(e.parameters.get("content", "")),
                "timestamp": e.created_at.isoformat() if e.created_at else None,
            }
            for e in self_events
        ]

        # 2. 兄弟节点的洞察（如果需要）
        if include_siblings:
            sibling_insights: list[dict[str, Any]] = self._get_sibling_insights(
                node_id, task_id, max_events
            )
            context["sibling_insights"] = sibling_insights  # type: ignore[assignment]

        # 3. 父节点的上下文（如果需要）
        if include_parent:
            parent_context: list[dict[str, Any]] = self._get_parent_context(task_id, max_events)
            context["parent_context"] = parent_context  # type: ignore[assignment]

        # 4. 集体记忆
        context["collective_memory"] = self.event_bus.get_collective_memory(limit=max_events)

        return context

    def _get_sibling_insights(
        self,
        current_node_id: str,
        task_id: str,
        max_events: int,
    ) -> list[dict[str, Any]]:
        """
        获取兄弟节点的洞察

        Args:
            current_node_id: 当前节点ID
            task_id: 任务ID
            max_events: 最大事件数量

        Returns:
            兄弟节点洞察列表
        """
        # 查询同一任务下的所有thinking事件
        task_events = self.event_bus.query_by_task(
            task_id,
            action_filter="node.thinking",
        )

        # 过滤掉自己的事件
        sibling_events = [e for e in task_events if e.parameters.get("node_id") != current_node_id]

        # 限制数量
        sibling_events = sibling_events[-max_events:]

        # 提取洞察
        insights = []
        for event in sibling_events:
            insights.append(
                {
                    "node_id": event.parameters.get("node_id"),
                    "content": event.parameters.get("content", ""),
                    "timestamp": event.created_at.isoformat() if event.created_at else None,
                }
            )

        return insights

    def _get_parent_context(
        self,
        task_id: str,
        max_events: int,
    ) -> list[dict[str, Any]]:
        """
        获取父节点的上下文

        Args:
            task_id: 任务ID
            max_events: 最大事件数量

        Returns:
            父节点上下文列表
        """
        # 查询任务的所有事件
        task_events = self.event_bus.query_by_task(task_id)

        # 过滤出父节点的thinking事件
        parent_events = [e for e in task_events if e.action == "node.thinking"]

        # 限制数量
        parent_events = parent_events[-max_events:]

        # 提取上下文
        context = []
        for event in parent_events:
            context.append(
                {
                    "node_id": event.parameters.get("node_id"),
                    "content": event.parameters.get("content", ""),
                    "timestamp": event.created_at.isoformat() if event.created_at else None,
                }
            )

        return context

    def build_thinking_summary(
        self,
        node_id: str | None = None,
        task_id: str | None = None,
        limit: int = 10,
    ) -> str:
        """
        构建思考过程摘要

        Args:
            node_id: 可选的节点过滤
            task_id: 可选的任务过滤
            limit: 最大事件数量

        Returns:
            思考过程摘要
        """
        thoughts = self.event_bus.query_thinking_process(
            node_id=node_id,
            task_id=task_id,
            limit=limit,
        )

        if not thoughts:
            return "No thinking process found."

        # 构建摘要
        summary = "Thinking Process:\n"
        for i, thought in enumerate(thoughts, 1):
            summary += f"{i}. {thought}\n"

        return summary

    def search_relevant_events(
        self,
        query: str,
        action_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        搜索相关事件（简单的关键词匹配）

        Args:
            query: 搜索查询
            action_types: 可选的动作类型过滤
            limit: 最大结果数量

        Returns:
            相关事件列表
        """
        if action_types is None:
            action_types = ["node.thinking", "node.tool_call"]

        relevant_events = []

        for action_type in action_types:
            events = self.event_bus.query_by_action(action_type, limit=limit * 2)

            # 简单的关键词匹配
            for event in events:
                content = event.parameters.get("content", "")
                if query.lower() in content.lower():
                    relevant_events.append(
                        {
                            "node_id": event.parameters.get("node_id"),
                            "action": event.action,
                            "content": content,
                            "timestamp": event.created_at.isoformat() if event.created_at else None,
                        }
                    )

        # 限制数量
        return relevant_events[:limit]

    def get_collective_insights(
        self,
        topic: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        获取集体洞察（Collective Insights）

        从所有节点的思考过程中提取洞察。

        Args:
            topic: 可选的主题过滤
            limit: 最大数量

        Returns:
            集体洞察字典
        """
        # 获取集体记忆
        collective_memory = self.event_bus.get_collective_memory(limit=limit)

        thinking_memory = collective_memory.get("node.thinking", {})
        if not isinstance(thinking_memory, dict):
            thinking_memory = {}

        insights: dict[str, Any] = {
            "total_nodes": len(thinking_memory),
            "total_thoughts": 0,
            "by_node": {},
        }

        # 统计每个节点的思考数量
        for node_id, thoughts in thinking_memory.items():
            if not isinstance(thoughts, list):
                continue
            thought_count = len(thoughts)
            insights["total_thoughts"] += thought_count
            insights["by_node"][node_id] = {
                "thought_count": thought_count,
                "recent_thoughts": [
                    str(t.get("content", "")) if isinstance(t, dict) else str(t)
                    for t in thoughts[-3:]
                ],  # 最近3条
            }

        # 如果有主题过滤
        if topic:
            filtered_insights: dict[str, Any] = {"by_node": {}}
            for node_id, node_data in insights["by_node"].items():
                if not isinstance(node_data, dict):
                    continue
                recent_thoughts = node_data.get("recent_thoughts", [])
                if not isinstance(recent_thoughts, list):
                    continue
                relevant_thoughts = [
                    str(t) for t in recent_thoughts if topic.lower() in str(t).lower()
                ]
                if relevant_thoughts:
                    filtered_insights["by_node"][node_id] = {
                        "thought_count": len(relevant_thoughts),
                        "recent_thoughts": relevant_thoughts,
                    }
            return filtered_insights

        return insights
