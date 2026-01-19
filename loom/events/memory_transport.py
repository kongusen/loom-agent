"""
Memory Transport - 内存传输层

基于内存的消息传递实现。

使用场景：
- 单机部署
- 开发测试
- 快速原型

特点：
- 零依赖
- 高性能
- 简单可靠
"""

import asyncio
from collections import defaultdict

from loom.events.transport import MessageHandler, Transport


class MemoryTransport(Transport):
    """
    内存传输层

    使用字典和异步调用实现进程内的消息传递。
    适用于单机部署和测试环境。
    """

    def __init__(self):
        """初始化内存传输层"""
        self._connected = False
        self._subscribers: dict[str, list[MessageHandler]] = defaultdict(list)

    async def connect(self) -> None:
        """建立连接（内存传输无需实际连接）"""
        self._connected = True

    async def disconnect(self) -> None:
        """断开连接，清理资源"""
        self._subscribers.clear()
        self._connected = False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    async def publish(self, topic: str, message: bytes) -> None:
        """
        发布消息到指定主题

        Args:
            topic: 主题名称
            message: 消息内容（字节）
        """
        if not self._connected:
            raise RuntimeError("Transport not connected")

        # 获取该主题的所有订阅者
        handlers = self._subscribers.get(topic, [])

        # 并发调用所有处理器
        if handlers:
            await asyncio.gather(
                *[handler(message) for handler in handlers], return_exceptions=True
            )

    async def subscribe(self, topic: str, handler: MessageHandler) -> None:
        """
        订阅主题

        Args:
            topic: 主题名称
            handler: 消息处理器
        """
        if not self._connected:
            raise RuntimeError("Transport not connected")

        # 添加处理器到订阅列表
        if handler not in self._subscribers[topic]:
            self._subscribers[topic].append(handler)

    async def unsubscribe(self, topic: str) -> None:
        """
        取消订阅主题

        Args:
            topic: 主题名称
        """
        if topic in self._subscribers:
            del self._subscribers[topic]
