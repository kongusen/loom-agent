"""
Event Stream Converter - 事件流转换器

基于公理A2（事件主权）和推论A2.2（分布式就绪）：
将事件总线的Task转换为SSE流，供前端订阅。

设计原则：
1. 标准化 - 使用SSE标准格式
2. 实时性 - 事件即时转换和推送
3. 可过滤 - 支持按模式订阅

核心功能：
- 订阅事件总线的特定事件
- 转换为SSE格式
- 流式推送给观测者
"""

import asyncio
import json
from collections.abc import AsyncIterator

from loom.events import EventBus
from loom.events.sse_formatter import SSEFormatter
from loom.protocol import Task


class EventStreamConverter:
    """
    事件流转换器

    将事件总线的Task事件转换为SSE流。
    """

    def __init__(self, event_bus: EventBus):
        """
        初始化转换器

        Args:
            event_bus: 事件总线
        """
        self.event_bus = event_bus
        self._subscriptions: dict[str, asyncio.Queue] = {}

    async def subscribe_and_stream(
        self,
        action_pattern: str,
        node_id: str | None = None,
    ) -> AsyncIterator[str]:
        """
        订阅事件并转换为SSE流

        Args:
            action_pattern: 动作模式（如 "node.*" 订阅所有节点事件）
            node_id: 可选的节点ID过滤

        Yields:
            SSE格式的事件字符串
        """
        # 创建事件队列
        queue: asyncio.Queue[Task] = asyncio.Queue()

        # 定义事件处理器
        async def event_handler(task: Task) -> Task:
            """处理事件并放入队列"""
            # 过滤节点ID
            if node_id and task.parameters.get("node_id") != node_id:
                return task

            # 放入队列
            await queue.put(task)
            return task

        # 注册处理器
        self.event_bus.register_handler(action_pattern, event_handler)

        try:
            # 发送初始连接事件
            yield SSEFormatter.format_sse_message(
                event_type="connected",
                data=json.dumps({"status": "connected", "pattern": action_pattern}),
            )

            # 持续从队列读取事件
            while True:
                try:
                    # 等待事件（带超时，用于发送心跳）
                    task = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # 转换为SSE格式
                    sse_message = self._convert_task_to_sse(task)
                    yield sse_message

                except TimeoutError:
                    # 超时，发送心跳
                    yield SSEFormatter.format_sse_message(
                        event_type="heartbeat",
                        data=json.dumps({"timestamp": asyncio.get_event_loop().time()}),
                    )

        except asyncio.CancelledError:
            # 客户端断开连接
            yield SSEFormatter.format_sse_message(
                event_type="disconnected",
                data=json.dumps({"status": "disconnected"}),
            )
        finally:
            # 注销 handler 防止内存泄漏
            self.event_bus.unregister_handler(action_pattern, event_handler)

    def _convert_task_to_sse(self, task: Task) -> str:
        """
        将Task转换为SSE格式

        Args:
            task: 任务事件

        Returns:
            SSE格式字符串
        """
        # 提取事件数据
        event_data = {
            "task_id": task.task_id,
            "source_agent": task.source_agent,
            "action": task.action,
            "parameters": task.parameters,
            "status": task.status.value,
            "timestamp": task.created_at.isoformat() if task.created_at else None,
        }

        # 转换为SSE格式
        return SSEFormatter.format_sse_message(
            event_type=task.action,
            data=json.dumps(event_data),
            event_id=task.task_id,
        )

    async def stream_node_events(
        self,
        node_id: str,
    ) -> AsyncIterator[str]:
        """
        订阅特定节点的所有事件

        Args:
            node_id: 节点ID

        Yields:
            SSE格式的事件字符串
        """
        async for sse_event in self.subscribe_and_stream(
            action_pattern="node.*",
            node_id=node_id,
        ):
            yield sse_event

    async def stream_thinking_events(
        self,
        node_id: str | None = None,
    ) -> AsyncIterator[str]:
        """
        订阅思考过程事件

        Args:
            node_id: 可选的节点ID过滤

        Yields:
            SSE格式的事件字符串
        """
        async for sse_event in self.subscribe_and_stream(
            action_pattern="node.thinking",
            node_id=node_id,
        ):
            yield sse_event
