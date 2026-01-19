"""
NATS Transport - NATS传输层

基于nats-py的分布式传输实现。

使用场景：
- 分布式部署
- 生产环境
- 跨节点通信

特点：
- 高性能
- 可扩展
- 支持集群
"""

from loom.events.transport import MessageHandler, Transport

try:
    import nats
    from nats.aio.client import Client as NATSClient
except ImportError:
    raise ImportError("NATS support requires nats-py. Install with: pip install nats-py") from None


class NATSTransport(Transport):
    """
    NATS传输层

    使用NATS实现分布式消息传递。
    适用于生产环境和分布式部署。
    """

    def __init__(
        self,
        servers: list[str] | None = None,
        name: str = "loom-agent",
        max_reconnect_attempts: int = 10,
    ):
        """
        初始化NATS传输层

        Args:
            servers: NATS服务器地址列表（默认：["nats://localhost:4222"]）
            name: 客户端名称
            max_reconnect_attempts: 最大重连次数
        """
        self._servers = servers or ["nats://localhost:4222"]
        self._name = name
        self._max_reconnect_attempts = max_reconnect_attempts

        self._client: NATSClient | None = None
        self._subscriptions: dict[str, int] = {}  # topic -> subscription_id
        self._connected = False

    async def connect(self) -> None:
        """建立NATS连接"""
        if self._connected:
            return

        self._client = await nats.connect(
            servers=self._servers,
            name=self._name,
            max_reconnect_attempts=self._max_reconnect_attempts,
        )
        self._connected = True

    async def disconnect(self) -> None:
        """断开NATS连接"""
        if not self._connected or not self._client:
            return

        # 取消所有订阅
        for topic in list(self._subscriptions.keys()):
            await self.unsubscribe(topic)

        # 关闭连接
        await self._client.close()
        self._client = None
        self._connected = False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self._client is not None

    async def publish(self, topic: str, message: bytes) -> None:
        """
        发布消息到指定主题

        Args:
            topic: 主题名称
            message: 消息内容（字节）
        """
        if not self._connected or not self._client:
            raise RuntimeError("Transport not connected")

        await self._client.publish(topic, message)

    async def subscribe(self, topic: str, handler: MessageHandler) -> None:
        """
        订阅主题

        Args:
            topic: 主题名称
            handler: 消息处理器
        """
        if not self._connected or not self._client:
            raise RuntimeError("Transport not connected")

        # 创建消息处理包装器
        async def message_handler(msg):
            await handler(msg.data)

        # 订阅主题
        sid = await self._client.subscribe(topic, cb=message_handler)
        self._subscriptions[topic] = sid

    async def unsubscribe(self, topic: str) -> None:
        """
        取消订阅主题

        Args:
            topic: 主题名称
        """
        if topic not in self._subscriptions:
            return

        if self._client:
            sid = self._subscriptions[topic]
            await self._client.unsubscribe(sid)

        del self._subscriptions[topic]
