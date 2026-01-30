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
    """

    def __init__(self, transport: Optional["Transport"] = None, debug_mode: bool = False):
        """
        初始化事件总线

        Args:
            transport: 可选的传输层（如果不提供，使用本地内存实现）
            debug_mode: 是否启用调试模式（保留最近100条事件用于调试）
        """
        self._handlers: dict[str, list[TaskHandler]] = defaultdict(list)
        self._transport = transport
        self._transport_initialized = False

        # 可选的调试事件记录（仅保留最近100条）
        self._recent_events: Any | None = None
        if debug_mode:
            from collections import deque

            self._recent_events = deque(maxlen=100)

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
                   特殊值 "*" 表示订阅所有任务（通配符订阅）
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
            asyncio.create_task(_notify_wildcard_handlers())

        if not handlers:
            # 无特定 handler 不修改状态，直接返回原始任务
            self._record_event(task)
            return task

        # Fire-and-forget模式：异步执行但不等待结果
        if not wait_result:

            async def _execute_async() -> None:
                with contextlib.suppress(Exception):
                    await handlers[0](task)

            asyncio.create_task(_execute_async())
            self._record_event(task)
            return task  # 返回原始任务

        # 等待结果模式：执行并返回结果
        try:
            result_task = await handlers[0](task)
            # 不修改 handler 返回的状态，保留原样
            self._record_event(result_task)
            return result_task
        except Exception as e:
            # 异常情况下，设置错误信息但不强制修改状态
            task.error = str(e)
            self._record_event(task)
            return task

    # ==================== 调试支持 ====================

    def _record_event(self, task: Task) -> None:
        """
        记录事件（仅用于调试模式）

        Args:
            task: 任务事件
        """
        # 仅在调试模式下记录到 _recent_events
        if self._recent_events is not None:
            self._recent_events.append(task)

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
