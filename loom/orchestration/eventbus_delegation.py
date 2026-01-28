"""
EventBus Delegation Handler - EventBus委派处理器

处理基于EventBus的异步Agent委派。
"""

import asyncio
from typing import Any

from loom.events.event_bus import EventBus
from loom.protocol import Task


class EventBusDelegationHandler:
    """
    EventBus委派处理器

    负责通过EventBus发送委派请求并等待响应。
    """

    def __init__(self, event_bus: EventBus, timeout: float = 30.0):
        """
        初始化处理器

        Args:
            event_bus: 事件总线
            timeout: 超时时间（秒）
        """
        self.event_bus = event_bus
        self.timeout = timeout
        self._pending_requests: dict[str, asyncio.Future] = {}

    async def delegate_task(
        self,
        source_agent_id: str,
        target_agent_id: str,
        subtask: str,
        parent_task_id: str,
        session_id: str | None = None,
    ) -> str:
        """
        通过EventBus委派任务

        Args:
            source_agent_id: 源Agent ID
            target_agent_id: 目标Agent ID
            subtask: 子任务描述
            parent_task_id: 父任务ID

        Returns:
            委派结果
        """
        request_id = f"{parent_task_id}:delegated:{target_agent_id}"

        # 创建Future用于等待响应
        future: asyncio.Future[str] = asyncio.Future()
        self._pending_requests[request_id] = future

        # 发布委派请求事件
        delegation_task = Task(
            task_id=request_id,
            source_agent=source_agent_id,
            target_agent=target_agent_id,
            action="node.delegation_request",
            parameters={
                "source_agent": source_agent_id,
                "target_agent": target_agent_id,
                "request_id": request_id,
                "subtask": subtask,
                "parent_task_id": parent_task_id,
                "content": subtask,
            },
            session_id=session_id,
        )
        await self.event_bus.publish(delegation_task)

        # 等待响应（带超时）
        try:
            result = await asyncio.wait_for(future, timeout=self.timeout)
            return str(result)
        except TimeoutError:
            self._pending_requests.pop(request_id, None)
            return f"Delegation timeout: {target_agent_id} did not respond within {self.timeout}s"
        except Exception as e:
            self._pending_requests.pop(request_id, None)
            return f"Delegation error: {str(e)}"

    async def handle_response(self, event: dict[str, Any]) -> None:
        """
        处理委派响应事件

        Args:
            event: 响应事件
        """
        request_id = event.get("request_id")
        if not request_id or request_id not in self._pending_requests:
            return

        future = self._pending_requests.pop(request_id)
        if not future.done():
            result = event.get("result", "")
            future.set_result(result)
