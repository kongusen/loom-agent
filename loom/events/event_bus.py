"""
Event Bus - 事件总线

基于公理A2（事件主权公理）：所有通信都是Task。
实现任务的发布、订阅和路由机制。

设计原则：
1. 异步优先 - 所有操作都是async
2. 类型安全 - 使用Task模型
3. 可扩展 - 支持中间件/拦截器
4. 可插拔传输层 - 支持本地和分布式部署
"""

import asyncio
import contextlib
import json
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Optional

from loom.protocol.task import Task, TaskStatus

if TYPE_CHECKING:
    from loom.events.transport import Transport

TaskHandler = Callable[[Task], Awaitable[Task]]


class EventBus:
    """
    事件总线 - 任务路由和分发

    功能：
    - 注册任务处理器
    - 发布任务
    - 路由任务到对应的处理器
    - 支持可插拔的传输层（本地/分布式）
    """

    def __init__(self, transport: Optional["Transport"] = None):
        """
        初始化事件总线

        Args:
            transport: 可选的传输层（如果不提供，使用本地内存实现）
        """
        self._handlers: dict[str, list[TaskHandler]] = defaultdict(list)
        self._transport = transport
        self._transport_initialized = False

    async def _ensure_transport_connected(self) -> None:
        """确保传输层已连接"""
        if self._transport and not self._transport_initialized:
            await self._transport.connect()
            self._transport_initialized = True

    def register_handler(self, action: str, handler: TaskHandler) -> None:
        """
        注册任务处理器

        Args:
            action: 任务动作类型
            handler: 处理器函数
        """
        self._handlers[action].append(handler)

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
            return task

        # 无transport，执行本地处理器（单机模式）
        handlers = self._handlers.get(task.action, [])

        if not handlers:
            task.status = TaskStatus.FAILED
            task.error = f"No handler found for action: {task.action}"
            return task

        # Fire-and-forget模式：异步执行但不等待结果
        if not wait_result:

            async def _execute_async() -> None:
                with contextlib.suppress(Exception):
                    await handlers[0](task)

            asyncio.create_task(_execute_async())
            return task  # 立即返回RUNNING状态

        # 等待结果模式：执行并返回结果
        try:
            result_task = await handlers[0](task)
            result_task.status = TaskStatus.COMPLETED
            return result_task
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            return task
