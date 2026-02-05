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
from typing import TYPE_CHECKING, Any, Optional

from loom.events.actions import AgentAction, MemoryAction, TaskAction
from loom.protocol.task import Task

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
    - 支持层级结构（子节点事件自动向父节点传播）
    """

    def __init__(
        self,
        transport: Optional["Transport"] = None,
        debug_mode: bool = False,
        parent_bus: Optional["EventBus"] = None,
        node_id: str | None = None,
    ):
        """
        初始化事件总线

        Args:
            transport: 可选的传输层（如果不提供，使用本地内存实现）
            debug_mode: 是否启用调试模式（保留最近100条事件用于调试）
            parent_bus: 父级事件总线（子节点事件会自动向上传播）
            node_id: 关联的节点ID（用于标识事件来源）
        """
        self._handlers: dict[str, list[TaskHandler]] = defaultdict(list)
        self._transport = transport
        self._transport_initialized = False
        self._parent_bus = parent_bus
        self._node_id = node_id

        # 后台任务集合（防止 fire-and-forget 任务被 GC）
        self._background_tasks: set[asyncio.Task[Any]] = set()

        # 可选的调试事件记录（仅保留最近100条）
        self._recent_events: Any | None = None
        if debug_mode:
            from collections import deque

            self._recent_events = deque(maxlen=100)

    def create_child_bus(self, node_id: str) -> "EventBus":
        """
        创建子级事件总线

        子级总线发布的事件会自动向上传播到父级总线。
        这支持分形架构中的多层级事件汇聚。

        Args:
            node_id: 子节点的ID（用于标识事件来源）

        Returns:
            新的EventBus实例，其parent_bus指向当前实例
        """
        return EventBus(
            transport=self._transport,
            debug_mode=self._recent_events is not None,
            parent_bus=self,
            node_id=node_id,
        )

    @property
    def node_id(self) -> str | None:
        """获取关联的节点ID"""
        return self._node_id

    @property
    def parent_bus(self) -> Optional["EventBus"]:
        """获取父级事件总线"""
        return self._parent_bus

    @property
    def registered_handlers(self) -> dict[str, int]:
        """获取已注册的处理器统计"""
        return {action: len(handlers) for action, handlers in self._handlers.items()}

    @property
    def pending_tasks_count(self) -> int:
        """获取待处理的后台任务数量"""
        return len(self._background_tasks)

    @property
    def is_transport_connected(self) -> bool:
        """传输层是否已连接"""
        return self._transport_initialized

    async def _ensure_transport_connected(self) -> None:
        """确保传输层已连接"""
        if self._transport and not self._transport_initialized:
            await self._transport.connect()
            self._transport_initialized = True

    def _create_background_task(self, coro: Any) -> asyncio.Task[Any]:
        """
        创建后台任务并跟踪其生命周期

        防止 fire-and-forget 任务被垃圾回收。

        Args:
            coro: 协程对象

        Returns:
            创建的 Task 对象
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    def register_handler(self, action: ActionType, handler: TaskHandler) -> None:
        """
        注册任务处理器

        Args:
            action: 任务动作类型（支持枚举或字符串）
                   特殊值 "*" 表示订阅所有任务（通配符订阅）
                   支持 pattern 匹配，如 "node.*" 匹配所有 node.xxx 事件
            handler: 处理器函数
        """
        # 将枚举转换为字符串值
        action_key = (
            action.value if isinstance(action, (TaskAction, MemoryAction, AgentAction)) else action
        )
        self._handlers[action_key].append(handler)

    def unregister_handler(self, action: ActionType, handler: TaskHandler) -> bool:
        """
        注销任务处理器

        Args:
            action: 任务动作类型（支持枚举或字符串）
            handler: 要注销的处理器函数

        Returns:
            是否成功注销（如果 handler 不存在返回 False）
        """
        action_key = (
            action.value if isinstance(action, (TaskAction, MemoryAction, AgentAction)) else action
        )
        if action_key in self._handlers and handler in self._handlers[action_key]:
            self._handlers[action_key].remove(handler)
            return True
        return False

    def _get_pattern_handlers(self, action: str) -> list[TaskHandler]:
        """
        获取匹配 action 的 pattern handlers

        支持 "prefix.*" 格式的 pattern 匹配。

        Args:
            action: 实际的 action 字符串

        Returns:
            匹配的 handler 列表
        """
        pattern_handlers = []
        for pattern, handlers in self._handlers.items():
            # 跳过精确匹配和全局通配符（已单独处理）
            if pattern == action or pattern == "*":
                continue
            # 检查 pattern 匹配（支持 "prefix.*" 格式）
            if pattern.endswith(".*"):
                prefix = pattern[:-2]  # 去掉 ".*"
                if action.startswith(prefix + "."):
                    pattern_handlers.extend(handlers)
        return pattern_handlers

    async def publish(self, task: Task, wait_result: bool = True) -> Task:
        """
        发布任务

        执行策略：
        - 如果有transport：通过transport发布（分布式模式）
        - 如果无transport：执行本地handlers（单机模式）

        重要：EventBus 不修改 Task.status，由 handler 决定状态

        Args:
            task: 要发布的任务
            wait_result: 是否等待任务完成
                - True: 等待任务执行完成，返回最终结果（默认）
                - False: 立即返回，不等待完成

        Returns:
            任务（handler 返回的结果或原始任务）
        """
        # 确保transport已连接
        await self._ensure_transport_connected()

        # 如果有transport，通过transport发布（分布式模式）
        if self._transport:
            task_json = json.dumps(task.to_dict())
            await self._transport.publish(f"task.{task.action}", task_json.encode())
            # 分布式模式下，由订阅者处理任务，返回原始任务
            result_task = task
            self._record_event(result_task)
            return result_task

        # 无transport，执行本地处理器（单机模式）
        handlers = self._handlers.get(task.action, [])
        # 添加 pattern 匹配的 handlers
        pattern_handlers = self._get_pattern_handlers(task.action)
        handlers = handlers + pattern_handlers
        wildcard_handlers = self._handlers.get("*", [])

        # 执行通配符订阅者（观察者模式，不等待结果）
        async def _notify_wildcard_handlers() -> None:
            """通知所有通配符订阅者"""
            for wildcard_handler in wildcard_handlers:
                # 通配符处理器异常不影响主流程
                with contextlib.suppress(Exception):
                    await wildcard_handler(task)

        # 如果有通配符订阅者，异步通知它们
        if wildcard_handlers:
            self._create_background_task(_notify_wildcard_handlers())

        if not handlers:
            # 无特定 handler 不修改状态，直接返回原始任务
            self._record_event(task)
            return task

        # Fire-and-forget模式：异步执行但不等待结果
        if not wait_result:

            async def _execute_async() -> None:
                for handler in handlers:
                    with contextlib.suppress(Exception):
                        await handler(task)

            self._create_background_task(_execute_async())
            self._record_event(task)
            return task  # 返回原始任务

        # 等待结果模式：执行所有 handlers，返回第一个的结果
        result_task = task
        for i, handler in enumerate(handlers):
            try:
                handler_result = await handler(task)
                # 第一个 handler 的结果作为主结果
                if i == 0:
                    result_task = handler_result
            except Exception as e:
                # 第一个 handler 异常时设置错误
                if i == 0:
                    task.error = str(e)
                    result_task = task
                # 后续 handler 异常静默忽略

        self._record_event(result_task)
        return result_task

    # ==================== 调试支持 ====================

    def _record_event(self, task: Task) -> None:
        """
        记录事件（仅用于调试模式）并向父级传播

        Args:
            task: 任务事件
        """
        # 仅在调试模式下记录到 _recent_events
        if self._recent_events is not None:
            self._recent_events.append(task)

        # 向父级总线传播事件（异步，fire-and-forget）
        if self._parent_bus is not None:
            self._create_background_task(self._propagate_to_parent(task))

    async def _propagate_to_parent(self, task: Task) -> None:
        """
        异步向父级总线传播事件

        Args:
            task: 要传播的任务事件
        """
        with contextlib.suppress(Exception):
            # 使用 fire-and-forget 模式，不等待父级处理结果
            await self._parent_bus.publish(task, wait_result=False)  # type: ignore[union-attr]

    def get_recent_events(self, limit: int = 10) -> list[Task]:
        """
        获取最近的事件（仅在调试模式下可用）

        Args:
            limit: 结果数量限制

        Returns:
            事件列表（如果调试模式未启用，返回空列表）
        """
        if self._recent_events is None:
            return []

        # 返回最近的 N 个事件
        events = list(self._recent_events)
        return events[-limit:] if len(events) > limit else events
