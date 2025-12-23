# 分布式强化设计文档

## 一、概述

### 1.1 核心目标

为 Loom 框架提供**开箱即用的分布式传输层实现**，支持跨进程、跨机器的节点通信，实现真正的分布式 Agent 系统。

**设计理念**：
- **零配置切换**：从本地内存传输切换到分布式传输只需修改一行配置
- **传输层透明**：节点代码无需修改，完全兼容现有 API
- **高可用性**：支持故障转移、负载均衡、消息持久化
- **协议一致性**：继续使用 CloudEvents 标准，保持协议统一

### 1.2 核心价值

| 场景 | 痛点 | 分布式强化解决方案 |
|------|------|------------------|
| **多机部署** | 单机资源受限，无法扩展 | 节点分布在多台机器，水平扩展 |
| **高可用** | 单点故障导致系统崩溃 | 节点冗余部署，自动故障转移 |
| **负载均衡** | 热点节点成为瓶颈 | 同一节点多实例，自动负载分发 |
| **异步解耦** | 同步调用导致级联失败 | 消息队列解耦，异步处理 |
| **持久化** | 进程重启丢失消息 | 消息持久化到 Redis/NATS |

### 1.3 技术选型

#### Redis 传输层

**优势**：
- 简单易用，部署成本低
- 支持 Pub/Sub 和 Stream 两种模式
- 内置持久化（AOF/RDB）
- 丰富的数据结构支持

**适用场景**：
- 中小规模部署（<100 节点）
- 对延迟要求不高（<10ms）
- 需要消息持久化

#### NATS 传输层

**优势**：
- 高性能（百万级 QPS）
- 轻量级（<10MB 内存占用）
- 原生支持集群和故障转移
- JetStream 提供持久化和 exactly-once 语义

**适用场景**：
- 大规模部署（>100 节点）
- 对延迟敏感（<1ms）
- 需要高吞吐量

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Loom 应用层（不变）                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  AgentNode   │  │  ToolNode    │  │  CrewNode    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                  传输层抽象（Transport）                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Memory     │  │    Redis     │  │    NATS      │      │
│  │  Transport   │  │  Transport   │  │  Transport   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    分布式基础设施                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Redis       │  │  NATS        │  │  服务发现     │      │
│  │  Cluster     │  │  Cluster     │  │  (Consul)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 传输层接口（已有）

Loom 已经定义了传输层抽象接口，我们只需实现具体的传输层：

```python
# loom/interfaces/transport.py
class Transport(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def publish(self, topic: str, event: CloudEvent) -> None:
        """发布事件"""
        pass

    @abstractmethod
    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        """订阅主题"""
        pass
```

**关键设计点**：
- 所有传输层实现相同接口
- 节点代码无需感知底层传输机制
- 通过依赖注入切换传输层

---

## 三、Redis 传输层实现

### 3.1 核心实现

**文件位置**：`loom/infra/transport/redis.py`

```python
import asyncio
import json
from typing import Dict, List, Callable, Optional
import redis.asyncio as aioredis
from loom.interfaces.transport import Transport, EventHandler
from loom.protocol.cloudevents import CloudEvent

class RedisTransport(Transport):
    """
    基于 Redis Pub/Sub 的分布式传输层

    特性：
    - 支持通配符订阅（使用 Redis Pattern Subscribe）
    - 消息持久化（可选，使用 Redis Stream）
    - 自动重连机制
    - 连接池管理
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        use_streams: bool = False,
        stream_maxlen: int = 10000,
        connection_pool_size: int = 10
    ):
        self.redis_url = redis_url
        self.use_streams = use_streams
        self.stream_maxlen = stream_maxlen
        self.connection_pool_size = connection_pool_size

        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.handlers: Dict[str, List[EventHandler]] = {}
        self.subscription_tasks: List[asyncio.Task] = []
        self._connected = False

    async def connect(self) -> None:
        """建立 Redis 连接"""
        try:
            # 创建连接池
            pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.connection_pool_size,
                decode_responses=False  # 使用二进制模式以支持 CloudEvent 序列化
            )
            self.redis = aioredis.Redis(connection_pool=pool)

            # 测试连接
            await self.redis.ping()

            # 创建 Pub/Sub 客户端
            self.pubsub = self.redis.pubsub()

            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        self._connected = False

        # 取消所有订阅任务
        for task in self.subscription_tasks:
            task.cancel()

        # 关闭 Pub/Sub
        if self.pubsub:
            await self.pubsub.close()

        # 关闭 Redis 连接
        if self.redis:
            await self.redis.close()

        logger.info("Disconnected from Redis")

    async def publish(self, topic: str, event: CloudEvent) -> None:
        """
        发布事件

        支持两种模式：
        1. Pub/Sub 模式：实时发布，不持久化
        2. Stream 模式：持久化到 Redis Stream
        """
        if not self._connected:
            raise RuntimeError("Not connected to Redis")

        # 序列化事件
        event_data = event.model_dump_json()

        if self.use_streams:
            # 使用 Redis Stream（持久化）
            stream_key = f"loom:stream:{topic}"
            await self.redis.xadd(
                stream_key,
                {"event": event_data},
                maxlen=self.stream_maxlen
            )
        else:
            # 使用 Pub/Sub（实时）
            channel = f"loom:channel:{topic}"
            await self.redis.publish(channel, event_data)

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        """
        订阅主题

        支持通配符：
        - "node.request/*" 匹配所有 node.request 子主题
        - "node.*/agent_1" 匹配 agent_1 的所有事件类型
        """
        if not self._connected:
            raise RuntimeError("Not connected to Redis")

        # 记录处理器
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)

        if self.use_streams:
            # Stream 模式：启动消费者任务
            task = asyncio.create_task(
                self._consume_stream(topic, handler)
            )
            self.subscription_tasks.append(task)
        else:
            # Pub/Sub 模式：订阅频道
            channel = f"loom:channel:{topic}"

            if "*" in topic:
                # 通配符订阅
                await self.pubsub.psubscribe(channel)
            else:
                # 精确订阅
                await self.pubsub.subscribe(channel)

            # 启动监听任务（如果还没有）
            if not self.subscription_tasks:
                task = asyncio.create_task(self._listen_pubsub())
                self.subscription_tasks.append(task)

    async def _listen_pubsub(self) -> None:
        """监听 Pub/Sub 消息"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] in ["message", "pmessage"]:
                    # 解析事件
                    event_data = message["data"]
                    if isinstance(event_data, bytes):
                        event_data = event_data.decode("utf-8")

                    event = CloudEvent.model_validate_json(event_data)

                    # 提取主题
                    channel = message["channel"]
                    if isinstance(channel, bytes):
                        channel = channel.decode("utf-8")
                    topic = channel.replace("loom:channel:", "")

                    # 调用匹配的处理器
                    await self._dispatch_to_handlers(topic, event)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in Pub/Sub listener: {e}")

    async def _consume_stream(self, topic: str, handler: EventHandler) -> None:
        """消费 Redis Stream"""
        stream_key = f"loom:stream:{topic}"
        last_id = "0"  # 从头开始消费

        try:
            while self._connected:
                # 阻塞读取（超时 1 秒）
                messages = await self.redis.xread(
                    {stream_key: last_id},
                    count=10,
                    block=1000
                )

                for stream, entries in messages:
                    for entry_id, entry_data in entries:
                        # 解析事件
                        event_json = entry_data[b"event"].decode("utf-8")
                        event = CloudEvent.model_validate_json(event_json)

                        # 调用处理器
                        await handler(event)

                        # 更新 last_id
                        last_id = entry_id

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in Stream consumer: {e}")

    async def _dispatch_to_handlers(self, topic: str, event: CloudEvent) -> None:
        """分发事件到匹配的处理器"""
        matched_handlers = []

        # 精确匹配
        if topic in self.handlers:
            matched_handlers.extend(self.handlers[topic])

        # 通配符匹配
        for pattern, handlers in self.handlers.items():
            if "*" in pattern:
                if self._match_pattern(topic, pattern):
                    matched_handlers.extend(handlers)

        # 并发调用所有处理器
        if matched_handlers:
            await asyncio.gather(
                *[h(event) for h in matched_handlers],
                return_exceptions=True
            )

    def _match_pattern(self, topic: str, pattern: str) -> bool:
        """简单的通配符匹配"""
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return topic.startswith(prefix)
        return topic == pattern
```

### 3.2 使用示例

```python
from loom.api.main import LoomApp
from loom.infra.transport.redis import RedisTransport

# 创建 Redis 传输层
redis_transport = RedisTransport(
    redis_url="redis://localhost:6379",
    use_streams=False  # 使用 Pub/Sub 模式
)

# 注入到 LoomApp
app = LoomApp(transport=redis_transport)

# 其他代码完全不变
agent = Agent(app, "my_agent", role="Assistant")
await app.run("Hello", target="node/my_agent")
```

### 3.3 配置选项

```python
# 开发环境：使用内存传输
app = LoomApp()  # 默认使用 InMemoryTransport

# 生产环境：使用 Redis Pub/Sub（实时，不持久化）
app = LoomApp(transport=RedisTransport(
    redis_url="redis://prod-redis:6379",
    use_streams=False
))

# 需要消息持久化：使用 Redis Stream
app = LoomApp(transport=RedisTransport(
    redis_url="redis://prod-redis:6379",
    use_streams=True,
    stream_maxlen=100000  # 保留最近 10 万条消息
))
```

---

## 四、NATS 传输层实现

### 4.1 核心实现

**文件位置**：`loom/infra/transport/nats.py`

```python
import asyncio
import json
from typing import Dict, List, Optional
import nats
from nats.aio.client import Client as NATSClient
from nats.js import JetStreamContext
from loom.interfaces.transport import Transport, EventHandler
from loom.protocol.cloudevents import CloudEvent

class NATSTransport(Transport):
    """
    基于 NATS 的高性能分布式传输层

    特性：
    - 超低延迟（<1ms）
    - 支持 JetStream 持久化
    - 原生集群支持
    - 自动负载均衡
    """

    def __init__(
        self,
        servers: List[str] = ["nats://localhost:4222"],
        use_jetstream: bool = False,
        stream_name: str = "LOOM_EVENTS",
        max_msgs: int = 100000
    ):
        self.servers = servers
        self.use_jetstream = use_jetstream
        self.stream_name = stream_name
        self.max_msgs = max_msgs

        self.nc: Optional[NATSClient] = None
        self.js: Optional[JetStreamContext] = None
        self.handlers: Dict[str, List[EventHandler]] = {}
        self.subscriptions: List = []
        self._connected = False

    async def connect(self) -> None:
        """建立 NATS 连接"""
        try:
            # 连接到 NATS 集群
            self.nc = await nats.connect(servers=self.servers)

            if self.use_jetstream:
                # 启用 JetStream
                self.js = self.nc.jetstream()

                # 创建 Stream（如果不存在）
                try:
                    await self.js.add_stream(
                        name=self.stream_name,
                        subjects=[f"loom.>"],  # 匹配所有 loom.* 主题
                        max_msgs=self.max_msgs
                    )
                except Exception as e:
                    # Stream 已存在
                    logger.debug(f"Stream already exists: {e}")

            self._connected = True
            logger.info(f"Connected to NATS at {self.servers}")

        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        self._connected = False

        # 取消所有订阅
        for sub in self.subscriptions:
            await sub.unsubscribe()

        # 关闭连接
        if self.nc:
            await self.nc.close()

        logger.info("Disconnected from NATS")

    async def publish(self, topic: str, event: CloudEvent) -> None:
        """发布事件"""
        if not self._connected:
            raise RuntimeError("Not connected to NATS")

        # 转换主题格式（将 / 替换为 .）
        nats_subject = f"loom.{topic.replace('/', '.')}"

        # 序列化事件
        event_data = event.model_dump_json().encode()

        if self.use_jetstream:
            # 使用 JetStream（持久化）
            await self.js.publish(nats_subject, event_data)
        else:
            # 使用核心 NATS（实时）
            await self.nc.publish(nats_subject, event_data)

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        """订阅主题"""
        if not self._connected:
            raise RuntimeError("Not connected to NATS")

        # 转换主题格式
        nats_subject = f"loom.{topic.replace('/', '.')}"

        # NATS 原生支持通配符
        # * 匹配单个 token
        # > 匹配多个 token
        nats_subject = nats_subject.replace("*", ">")

        # 记录处理器
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)

        # 创建消息处理器
        async def message_handler(msg):
            try:
                # 解析事件
                event = CloudEvent.model_validate_json(msg.data.decode())
                # 调用处理器
                await handler(event)
            except Exception as e:
                logger.error(f"Error handling message: {e}")

        if self.use_jetstream:
            # JetStream 订阅（持久化消费者）
            consumer_name = f"consumer_{topic.replace('/', '_')}"
            sub = await self.js.subscribe(
                nats_subject,
                durable=consumer_name,
                cb=message_handler
            )
        else:
            # 核心 NATS 订阅
            sub = await self.nc.subscribe(nats_subject, cb=message_handler)

        self.subscriptions.append(sub)
```

### 4.2 使用示例

```python
from loom.api.main import LoomApp
from loom.infra.transport.nats import NATSTransport

# 单节点 NATS
nats_transport = NATSTransport(
    servers=["nats://localhost:4222"],
    use_jetstream=False
)

# NATS 集群（高可用）
nats_transport = NATSTransport(
    servers=[
        "nats://nats1:4222",
        "nats://nats2:4222",
        "nats://nats3:4222"
    ],
    use_jetstream=True  # 启用持久化
)

app = LoomApp(transport=nats_transport)
```

### 4.3 性能对比

| 指标 | InMemory | Redis Pub/Sub | Redis Stream | NATS Core | NATS JetStream |
|------|----------|---------------|--------------|-----------|----------------|
| **延迟** | <0.1ms | 1-5ms | 5-10ms | <1ms | 2-5ms |
| **吞吐量** | 无限 | 10万/s | 5万/s | 100万/s | 50万/s |
| **持久化** | ❌ | ❌ | ✅ | ❌ | ✅ |
| **集群支持** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **内存占用** | 低 | 中 | 高 | 极低 | 中 |

**选型建议**：
- **开发/测试**：InMemory
- **小规模生产**：Redis Pub/Sub
- **需要持久化**：Redis Stream 或 NATS JetStream
- **大规模/高性能**：NATS Core 或 JetStream

---

## 五、服务发现与负载均衡

### 5.1 节点注册与发现

**问题**：分布式环境下，如何知道哪些节点在线？

**解决方案**：使用 Redis 或 Consul 实现服务注册

```python
# loom/infra/discovery/redis_registry.py
class RedisServiceRegistry:
    """基于 Redis 的服务注册中心"""

    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.registry_key = "loom:registry"
        self.heartbeat_interval = 5  # 秒

    async def register_node(self, node_id: str, metadata: dict):
        """注册节点"""
        node_info = {
            "node_id": node_id,
            "metadata": metadata,
            "last_heartbeat": time.time()
        }

        # 存储到 Redis Hash
        await self.redis.hset(
            self.registry_key,
            node_id,
            json.dumps(node_info)
        )

        # 设置过期时间（心跳超时）
        await self.redis.expire(self.registry_key, self.heartbeat_interval * 3)

        # 启动心跳任务
        asyncio.create_task(self._heartbeat_loop(node_id, metadata))

    async def _heartbeat_loop(self, node_id: str, metadata: dict):
        """心跳循环"""
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            await self.register_node(node_id, metadata)

    async def discover_nodes(self, node_type: Optional[str] = None) -> List[dict]:
        """发现节点"""
        all_nodes = await self.redis.hgetall(self.registry_key)

        nodes = []
        for node_id, node_data in all_nodes.items():
            node_info = json.loads(node_data)

            # 过滤节点类型
            if node_type and node_info["metadata"].get("type") != node_type:
                continue

            nodes.append(node_info)

        return nodes
```

### 5.2 负载均衡策略

**问题**：同一节点有多个实例时，如何分发请求？

**解决方案**：在传输层实现负载均衡

```python
class LoadBalancedTransport(Transport):
    """带负载均衡的传输层装饰器"""

    def __init__(self, base_transport: Transport, registry: RedisServiceRegistry):
        self.base_transport = base_transport
        self.registry = registry
        self.strategy = "round_robin"  # 或 "random", "least_connections"
        self.counters: Dict[str, int] = {}

    async def publish(self, topic: str, event: CloudEvent) -> None:
        """发布时进行负载均衡"""
        # 如果是请求事件，且目标节点有多个实例
        if event.type == "node.request" and event.subject:
            node_id = event.subject.split("/")[-1]

            # 发现该节点的所有实例
            instances = await self.registry.discover_nodes(node_type=node_id)

            if len(instances) > 1:
                # 选择一个实例
                selected = self._select_instance(instances)
                # 修改目标为具体实例
                event.subject = f"{event.subject}#{selected['instance_id']}"

        # 委托给底层传输
        await self.base_transport.publish(topic, event)

    def _select_instance(self, instances: List[dict]) -> dict:
        """选择实例（轮询策略）"""
        key = instances[0]["node_id"]
        counter = self.counters.get(key, 0)
        selected = instances[counter % len(instances)]
        self.counters[key] = counter + 1
        return selected
```

---

## 六、部署架构示例

### 6.1 单机开发环境

```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  loom-app:
    build: .
    environment:
      - LOOM_TRANSPORT=memory  # 使用内存传输
    ports:
      - "8000:8000"
```

### 6.2 小规模生产环境（Redis）

```yaml
# docker-compose.prod-redis.yml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  loom-agent-1:
    build: .
    environment:
      - LOOM_TRANSPORT=redis
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

  loom-agent-2:
    build: .
    environment:
      - LOOM_TRANSPORT=redis
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis

volumes:
  redis-data:
```

### 6.3 大规模生产环境（NATS 集群）

```yaml
# docker-compose.prod-nats.yml
version: '3.8'
services:
  nats-1:
    image: nats:latest
    command: "-js -cluster nats://0.0.0.0:6222 -routes nats://nats-2:6222,nats://nats-3:6222"
    ports:
      - "4222:4222"

  nats-2:
    image: nats:latest
    command: "-js -cluster nats://0.0.0.0:6222 -routes nats://nats-1:6222,nats://nats-3:6222"

  nats-3:
    image: nats:latest
    command: "-js -cluster nats://0.0.0.0:6222 -routes nats://nats-1:6222,nats://nats-2:6222"

  loom-agent:
    build: .
    environment:
      - LOOM_TRANSPORT=nats
      - NATS_SERVERS=nats://nats-1:4222,nats://nats-2:4222,nats://nats-3:4222
    deploy:
      replicas: 5  # 5 个实例
    depends_on:
      - nats-1
      - nats-2
      - nats-3
```

---

## 七、实现路线图

### 阶段 1：Redis 传输层（1-2周）

**任务**：
1. 实现 `RedisTransport` 基础功能
   - Pub/Sub 模式
   - 连接池管理
   - 通配符订阅

2. 实现 Redis Stream 支持
   - 消息持久化
   - 消费者组

3. 单元测试和集成测试

**验收标准**：
- 通过所有现有测试
- 性能测试：延迟 <5ms，吞吐量 >5万/s

### 阶段 2：NATS 传输层（1-2周）

**任务**：
1. 实现 `NATSTransport` 基础功能
   - 核心 NATS 支持
   - 集群连接

2. 实现 JetStream 支持
   - 持久化消费者
   - At-least-once 语义

3. 性能优化和测试

**验收标准**：
- 延迟 <1ms
- 吞吐量 >50万/s

### 阶段 3：服务发现与负载均衡（1周）

**任务**：
1. 实现服务注册中心
2. 实现负载均衡策略
3. 健康检查和故障转移

**验收标准**：
- 节点自动发现
- 请求均匀分发

---

## 八、总结

通过实现 Redis 和 NATS 传输层，Loom 框架将具备：

✅ **零配置切换**：一行代码从本地切换到分布式
✅ **高可用性**：节点冗余、自动故障转移
✅ **水平扩展**：支持数百个节点的大规模部署
✅ **性能优化**：NATS 提供微秒级延迟
✅ **消息持久化**：Redis Stream 和 NATS JetStream

这将使 Loom 成为真正的**生产级分布式 Agent 框架**。

