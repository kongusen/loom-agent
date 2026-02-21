"""
Transport - 传输层抽象接口

基于第一性原理的传输层设计。

设计原则：
1. 抽象统一 - 统一的传输层接口
2. 可插拔 - 支持多种传输实现
3. 异步优先 - 所有操作都是async
4. 类型安全 - 使用类型注解

传输层职责：
- 消息发布/订阅
- 连接管理
- 消息序列化/反序列化
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

# 消息处理器类型
MessageHandler = Callable[[bytes], Awaitable[None]]


class Transport(ABC):
    """
    传输层抽象接口

    所有传输层实现必须继承此接口。
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        建立连接

        对于内存传输，此方法可能是空操作。
        对于网络传输（如NATS），需要建立实际连接。
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        断开连接

        清理资源，关闭连接。
        """
        pass

    @abstractmethod
    async def publish(self, topic: str, message: bytes) -> None:
        """
        发布消息到指定主题

        Args:
            topic: 主题名称
            message: 消息内容（字节）
        """
        pass

    @abstractmethod
    async def subscribe(self, topic: str, handler: MessageHandler) -> None:
        """
        订阅主题

        Args:
            topic: 主题名称
            handler: 消息处理器
        """
        pass

    @abstractmethod
    async def unsubscribe(self, topic: str) -> None:
        """
        取消订阅主题

        Args:
            topic: 主题名称
        """
        pass

    def is_connected(self) -> bool:
        """
        检查是否已连接

        Returns:
            是否已连接
        """
        return False
