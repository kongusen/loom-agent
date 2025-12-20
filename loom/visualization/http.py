"""
HTTP Trace Handler - 推送事件到 Loom Studio Server
"""

from __future__ import annotations

import aiohttp
import asyncio
from typing import Optional

from loom.core.events import AgentEvent
from loom.interfaces.event_producer import EventProducer


class HttpTraceHandler(EventProducer):
    """
    HTTP 追踪处理器
    
    将事件实时推送到 Loom Studio 后端
    """

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        self.trace_id: Optional[str] = None
        self.trace_name: str = "Untitled Trace"

    async def start_trace(self, name: str = "Untitled Trace"):
        """开始一个新的 Trace"""
        self.trace_name = name
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            async with self.session.post(
                f"{self.server_url}/api/traces", 
                json={"name": name}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.trace_id = data["id"]
        except Exception as e:
            # 忽略连接错误，避免影响主流程
            print(f"[Warning] Failed to connect to Loom Studio: {e}")

    async def emit(self, event: AgentEvent) -> None:
        """发送事件"""
        # 如果是第一次收到事件且没有 trace_id，自动启动
        if not self.trace_id:
            agent_name = event.agent_name or "Root"
            # 如果是 Agent Start，用它的输入作为 Trace Name 的一部分？
            await self.start_trace(name=f"Trace: {agent_name}")

        if not self.trace_id or not self.session:
            return

        try:
            # 异步发送，不等待结果
            payload = {
                "trace_id": self.trace_id,
                "event": event.to_dict()
            }
            # create_task 避免阻塞
            asyncio.create_task(self._send(payload))
                
        except Exception:
            pass

    async def _send(self, payload):
        try:
            if self.session:
                async with self.session.post(
                    f"{self.server_url}/api/events", 
                    json=payload
                ) as _:
                    pass
        except Exception:
            pass

    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            self.session = None
