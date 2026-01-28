"""
Event Bus - 事件总线

基于公理A2（事件主权公理）：所有通信都是Task。
实现任务的发布、订阅和路由机制。

设计原则：
1. 异步优先 - 所有操作都是async
2. 类型安全 - 使用Task模型和枚举路由
3. 可扩展 - 支持中间件/拦截器
4. 可插拔传输层 - 支持本地和分布式部署
"""

import asyncio
import contextlib
import json
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional

from loom.events.actions import AgentAction, MemoryAction, TaskAction
from loom.protocol.task import Task, TaskStatus

if TYPE_CHECKING:
    from loom.events.transport import Transport

TaskHandler = Callable[[Task], Awaitable[Task]]
ActionType = TaskAction | MemoryAction | AgentAction | str


class EventBus:
    """
    事件总线 - 任务路由和分发

    功能：
    - 注册任务处理器
    - 发布任务
    - 路由任务到对应的处理器
    - 支持可插拔的传输层（本地/分布式）
    """

    def __init__(self, transport: Optional["Transport"] = None, max_history: int = 1000):
        """
        初始化事件总线

        Args:
            transport: 可选的传输层（如果不提供，使用本地内存实现）
        """
        self._handlers: dict[str, list[TaskHandler]] = defaultdict(list)
        self._transport = transport
        self._transport_initialized = False

        # 事件历史（按时间顺序）
        self._event_history: list[Task] = []

        # 索引：按节点ID
        self._events_by_node: dict[str, list[Task]] = defaultdict(list)

        # 索引：按动作类型
        self._events_by_action: dict[str, list[Task]] = defaultdict(list)

        # 索引：按任务ID（包含task_id与parent_task_id两类）
        self._events_by_task: dict[str, list[Task]] = defaultdict(list)

        # 索引：按目标agent / 目标node（点对点消息）
        self._events_by_target_agent: dict[str, list[Task]] = defaultdict(list)
        self._events_by_target_node: dict[str, list[Task]] = defaultdict(list)

        # 最大历史数量
        self._max_history = max_history

    async def _ensure_transport_connected(self) -> None:
        """确保传输层已连接"""
        if self._transport and not self._transport_initialized:
            await self._transport.connect()
            self._transport_initialized = True

    def register_handler(self, action: ActionType, handler: TaskHandler) -> None:
        """
        注册任务处理器

        Args:
            action: 任务动作类型（支持枚举或字符串）
            handler: 处理器函数
        """
        # 将枚举转换为字符串值
        action_key = (
            action.value if isinstance(action, TaskAction | MemoryAction | AgentAction) else action
        )
        self._handlers[action_key].append(handler)

    async def publish(self, task: Task, wait_result: bool = True) -> Task:
        """
        发布任务

        执行策略：
        - 如果有transport：通过transport发布（分布式模式）
        - 如果无transport：执行本地handlers（单机模式）

        Args:
            task: 要发布的任务
            wait_result: 是否等待任务完成
                - True: 等待任务执行完成，返回最终结果（默认）
                - False: 立即返回RUNNING状态，不等待完成

        Returns:
            更新后的任务（包含结果或错误）
        """
        # 确保transport已连接
        await self._ensure_transport_connected()

        # 更新状态为运行中
        task.status = TaskStatus.RUNNING

        # 如果有transport，通过transport发布（分布式模式）
        if self._transport:
            task_json = json.dumps(task.to_dict())
            await self._transport.publish(f"task.{task.action}", task_json.encode())
            # 分布式模式下，由订阅者处理任务，返回RUNNING状态
            result_task = task
            self._record_event(result_task)
            return result_task

        # 无transport，执行本地处理器（单机模式）
        handlers = self._handlers.get(task.action, [])

        if not handlers:
            task.status = TaskStatus.FAILED
            task.error = f"No handler found for action: {task.action}"
            self._record_event(task)
            return task

        # Fire-and-forget模式：异步执行但不等待结果
        if not wait_result:

            async def _execute_async() -> None:
                with contextlib.suppress(Exception):
                    await handlers[0](task)

            asyncio.create_task(_execute_async())
            self._record_event(task)
            return task  # 立即返回RUNNING状态

        # 等待结果模式：执行并返回结果
        try:
            result_task = await handlers[0](task)
            result_task.status = TaskStatus.COMPLETED
            self._record_event(result_task)
            return result_task
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._record_event(task)
            return task

    # ==================== 事件记录与查询 ====================

    def _record_event(self, task: Task) -> None:
        """
        记录事件到历史

        Args:
            task: 任务事件
        """
        # 添加到历史
        self._event_history.append(task)

        # 更新索引：按节点ID
        node_id = task.parameters.get("node_id")
        if node_id:
            self._events_by_node[node_id].append(task)

        # 更新索引：按动作类型
        self._events_by_action[task.action].append(task)

        # 更新索引：按任务ID（包含自身task_id与父任务ID）
        self._events_by_task[task.task_id].append(task)
        parent_task_id = task.parameters.get("parent_task_id") or task.parent_task_id
        if parent_task_id:
            self._events_by_task[parent_task_id].append(task)

        # 更新索引：按目标agent / 目标node（点对点消息）
        if task.target_agent:
            self._events_by_target_agent[task.target_agent].append(task)
        target_node_id = task.parameters.get("target_node_id")
        if target_node_id:
            self._events_by_target_node[target_node_id].append(task)

        # 限制历史大小
        if len(self._event_history) > self._max_history:
            # 移除最旧的事件
            old_task = self._event_history.pop(0)

            # 更新索引：节点
            old_node_id = old_task.parameters.get("node_id")
            if old_node_id and old_node_id in self._events_by_node:
                with contextlib.suppress(ValueError):
                    self._events_by_node[old_node_id].remove(old_task)

            # 更新索引：动作
            if old_task.action in self._events_by_action:
                with contextlib.suppress(ValueError):
                    self._events_by_action[old_task.action].remove(old_task)

            # 更新索引：任务
            with contextlib.suppress(ValueError):
                self._events_by_task[old_task.task_id].remove(old_task)
            old_parent_id = old_task.parameters.get("parent_task_id") or old_task.parent_task_id
            if old_parent_id:
                with contextlib.suppress(ValueError):
                    self._events_by_task[old_parent_id].remove(old_task)

            # 更新索引：目标agent / 目标node
            if old_task.target_agent:
                with contextlib.suppress(ValueError):
                    self._events_by_target_agent[old_task.target_agent].remove(old_task)
            old_target_node_id = old_task.parameters.get("target_node_id")
            if old_target_node_id:
                with contextlib.suppress(ValueError):
                    self._events_by_target_node[old_target_node_id].remove(old_task)

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

    def query_by_target(
        self,
        target_agent: str | None = None,
        target_node_id: str | None = None,
        action_filter: str | None = None,
        limit: int | None = None,
    ) -> list[Task]:
        """
        查询点对点目标的事件

        Args:
            target_agent: 目标 agent ID
            target_node_id: 目标 node ID（可选）
            action_filter: 可选的动作过滤
            limit: 可选的结果数量限制

        Returns:
            事件列表（按时间顺序）
        """
        events: list[Task] = []

        if target_agent:
            events.extend(self._events_by_target_agent.get(target_agent, []))
        if target_node_id:
            events.extend(self._events_by_target_node.get(target_node_id, []))

        if not events:
            return []

        # 去重（按 task_id）
        seen_ids: set[str] = set()
        unique: list[Task] = []
        for event in events:
            if event.task_id in seen_ids:
                continue
            unique.append(event)
            seen_ids.add(event.task_id)

        # TTL过滤
        now = datetime.now(UTC)
        filtered: list[Task] = []
        for event in unique:
            ttl_seconds = event.parameters.get("ttl_seconds")
            if ttl_seconds is None:
                filtered.append(event)
                continue
            if not event.created_at:
                continue
            if (now - event.created_at).total_seconds() <= float(ttl_seconds):
                filtered.append(event)

        if not filtered:
            return []

        # 应用动作过滤
        if action_filter:
            filtered = [e for e in filtered if e.action == action_filter]

        # 按优先级+时间排序（高优先级/最新优先）
        filtered.sort(
            key=lambda e: (
                float(e.parameters.get("priority", 0.5)),
                e.created_at.timestamp() if e.created_at else 0,
            ),
            reverse=True,
        )

        # 应用数量限制
        if limit:
            filtered = filtered[:limit]

        return filtered

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
        self._events_by_target_agent.clear()
        self._events_by_target_node.clear()
