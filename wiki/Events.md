# 事件系统

`loom/events/` 实现了基于公理 A2（事件主权）的事件驱动架构。所有 Agent 间通信都通过 Task 对象经 EventBus 路由。

## 文件结构

```
loom/events/
├── event_bus.py         # EventBus - 事件总线（核心）
├── actions.py           # 类型安全的动作枚举
├── handlers.py          # 处理器协议定义
├── transport.py         # Transport 抽象接口
├── memory_transport.py  # MemoryTransport - 内存传输（单机/测试）
├── nats_transport.py    # NATSTransport - NATS 传输（分布式）
├── session.py           # Session 管理
├── context_controller.py# ContextController
├── output_collector.py  # OutputCollector - 多 Agent 并行 SSE
├── sse_formatter.py     # SSE 格式化
└── stream_converter.py  # 流转换器
```

## EventBus

事件总线是所有通信的中枢，负责 Task 的发布、订阅和路由。

```python
from loom.events import EventBus, MemoryTransport

# 创建（默认内存传输）
bus = EventBus(debug_mode=True)

# 使用 NATS 传输（分布式）
bus = EventBus(transport=NATSTransport(url="nats://localhost:4222"))

# 注册处理器
bus.register("execute", handler_func)

# 发布任务
result = await bus.publish(task, wait_result=True)   # 等待结果
await bus.publish(task, wait_result=False)            # fire-and-forget
```

### 层级结构

EventBus 支持父子层级，子节点事件自动向父节点传播：

```python
parent_bus = EventBus(node_id="root")
child_bus = parent_bus.create_child_bus(node_id="child-1")
# child_bus 发布的事件会自动传播到 parent_bus
```

### 调试模式

`debug_mode=True` 时保留最近 100 条事件，可通过 `query_recent()` 和 `query_by_task()` 查询。

## 动作类型

框架定义了四组类型安全的动作枚举：

### TaskAction
```python
class TaskAction(StrEnum):
    EXECUTE = "execute"
    PLAN = "plan"
    DELEGATE = "delegate"
    OBSERVE = "observe"
    QUERY = "query"
```

### MemoryAction
```python
class MemoryAction(StrEnum):
    STORE = "memory.store"
    RETRIEVE = "memory.retrieve"
    COMPRESS = "memory.compress"
    MIGRATE = "memory.migrate"
```

### AgentAction
```python
class AgentAction(StrEnum):
    THINKING = "node.thinking"
    TOOL_CALL = "node.tool_call"
    TOOL_RESULT = "node.tool_result"
    PLANNING = "node.planning"
    START = "node.start"
    COMPLETE = "node.complete"
    ERROR = "node.error"
    MESSAGE = "node.message"
```

### KnowledgeAction
```python
class KnowledgeAction(StrEnum):
    SEARCH = "knowledge.search"
    INDEX = "knowledge.index"
```

## 传输层

Transport 是可插拔的传输抽象，支持两种实现：

| 传输层 | 场景 | 依赖 |
|--------|------|------|
| `MemoryTransport` | 单机、测试 | 无 |
| `NATSTransport` | 分布式、生产 | `nats-py` |

```python
class Transport(ABC):
    async def publish(self, topic: str, data: bytes) -> None: ...
    async def subscribe(self, topic: str, handler: Callable) -> None: ...
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
```

## Session

Session 管理会话状态：

```python
class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Session:
    session_id: str
    status: SessionStatus
    created_at: datetime
    metadata: dict
```

## OutputCollector

支持多 Agent 并行执行时的 SSE（Server-Sent Events）输出收集：

```python
class OutputStrategy(StrEnum):
    INTERLEAVED = "interleaved"  # 交错输出
    SEQUENTIAL = "sequential"    # 顺序输出
    GROUPED = "grouped"          # 按 Agent 分组

collector = OutputCollector(strategy=OutputStrategy.INTERLEAVED)
```

## SSEFormatter

将 Task 事件格式化为标准 SSE 消息，用于 Web API 的流式输出。
