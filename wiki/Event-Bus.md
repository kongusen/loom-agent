# 事件总线 (Event Bus)

## 定义

**事件总线**是 Loom 的神经系统，提供类型安全的发布-订阅机制，实现节点间的松耦合通信和可观测性。

## 核心思想

传统系统的组件通信方式有两种：
1. **直接调用**: 紧耦合，难以扩展
2. **消息队列**: 复杂，需要额外的消息中间件

Loom 采用**事件总线**作为第三条路：
- **同步执行**: 像直接调用一样简单
- **松耦合**: 发布者和订阅者互不依赖
- **类型安全**: 基于 Protocol 的严格类型检查
- **可观测**: 自动记录所有事件

## CloudEvents 标准

Loom 使用 [CloudEvents](https://cloudevents.io/) 规范，确保互操作性：

```python
{
    "specversion": "1.0",
    "type": "loom.node.thinking",        # 事件类型
    "source": "/node/researcher",        # 事件源
    "id": "evt-123456",                  # 唯一 ID
    "time": "2024-01-27T10:00:00Z",      # 时间戳
    "data": {                            # 事件数据
        "content": "Let me analyze...",
        "task_id": "task-789"
    }
}
```

## 核心事件类型

### 节点生命周期事件

| 事件类型 | 触发时机 | 用途 |
|---------|---------|------|
| `node.created` | 节点创建 | 初始化日志 |
| `node.started` | 节点开始执行 | 性能监控 |
| `node.completed` | 节点完成任务 | 结果收集 |
| `node.failed` | 节点失败 | 错误处理 |

### 认知过程事件

| 事件类型 | 触发时机 | 用途 |
|---------|---------|------|
| `node.thinking` | LLM 生成思考 | 实时流式输出 |
| `node.tool_call` | 调用工具 | 工具使用追踪 |
| `node.done` | 任务完成 | 结果确认 |

### 记忆事件

| 事件类型 | 触发时机 | 用途 |
|---------|---------|------|
| `memory.read` | 读取记忆 | 记忆访问分析 |
| `memory.write` | 写入记忆 | 记忆增长追踪 |
| `memory.evict` | 淘汰记忆 | 记忆策略优化 |

## 发布-订阅机制

### 发布事件

```python
from loom.events import Event, EventBus

# 发布事件
event = Event(
    type="node.thinking",
    source="/node/researcher",
    data={"content": "Analyzing..."}
)

await event_bus.publish(event)
```

### 订阅事件

```python
from loom.events import EventHandler

# 定义事件处理器
class ThinkingLogger(EventHandler):
    protocol = NodeThinkingProtocol

    async def handle(self, event: Event) -> None:
        print(f"Thinking: {event.data['content']}")

# 注册订阅
event_bus.subscribe(ThinkingLogger())
```

## 可观测性

事件总线的最大价值是**可观测性**：

### 1. 思考流式输出

```python
async for event in event_bus.stream():
    if event.type == "node.thinking":
        print(event.data["content"], end="", flush=True)
```

### 2. 工具调用追踪

```python
async for event in event_bus.stream():
    if event.type == "node.tool_call":
        print(f"Tool: {event.data['tool_name']}")
        print(f"Args: {event.data['tool_args']}")
```

### 3. 性能分析

```python
start_time = None

async def track_performance(event):
    nonlocal start_time
    if event.type == "node.started":
        start_time = time.time()
    elif event.type == "node.completed":
        duration = time.time() - start_time
        print(f"Duration: {duration}s")
```

## 查询能力

EventBus 提供事件查询功能：

```python
from loom.events import EventBus

event_bus = EventBus()

# 查询特定节点的思考事件
events = event_bus.query_by_node(
    node_id="researcher",
    action_filter="node.thinking",
    limit=100
)

# 查询最近事件
events = event_bus.query_recent(limit=50)
```

## 事件拦截器

通过拦截器模式，可以在不修改节点代码的情况下添加横切关注点：

```python
from loom.runtime import Interceptor

class LoggingInterceptor(Interceptor):
    async def intercept(self, context, next_handler):
        print(f"Before: {context.event}")
        result = await next_handler()
        print(f"After: {result}")
        return result

# 注册拦截器
event_bus.register_interceptor(LoggingInterceptor())
```

参见: [Interceptor](Interceptor)

## 相关概念

- → [公理系统](Axiomatic-System) (A2: 事件主权公理)
- → [CloudEvents](CloudEvents) (事件标准格式)
- → [事件拦截器](Event-Interceptor) (横切关注点)
- → [可观测性](Observability) (监控和调试)

## 参见

- 📖 [设计文档](design/Event-System)
- 🔧 [API 指南]: [事件 API](api/Event)
- 💡 [示例代码]: [事件流处理](examples/event-stream)

## 代码位置

- 事件总线: `loom/events/event_bus.py`
- 可查询总线: `loom/events/event_bus.py`
- 协议定义: `loom/protocol/events.py`

## 反向链接

被引用于: [分形架构](Fractal-Architecture) | [拦截器](Interceptor) | [可观测性](Observability) | [Agent API](API-Agent)
