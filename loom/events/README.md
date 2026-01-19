# A2: 事件主权公理 (Event Sovereignty Axiom)

> **公理陈述**: ∀communication ∈ System: communication = Task

## 设计理念

A2层实现基于Task模型的事件系统，使用SSE（Server-Sent Events）传输。
符合**Google A2A协议标准**，支持实时任务通信。

## 核心组件

### 1. EventBus (`event_bus.py`)
事件总线 - 任务路由和分发：
- `register_handler()`: 注册任务处理器
- `publish()`: 发布任务
- `get_task()`: 获取任务状态

### 2. SSETransport (`sse_transport.py`)
SSE传输层 - 任务序列化和传输：
- `serialize_task()`: 任务序列化
- `deserialize_task()`: 任务反序列化
- `format_sse_message()`: SSE消息格式化

## 与公理系统的关系

- **A2（事件主权）**: Task是通信的唯一格式
- **A2A协议**: 使用SSE实现实时传输
- **任务生命周期**: pending → running → completed/failed

## 传输协议

**SSE (Server-Sent Events)**:
- ✓ 基于HTTP协议
- ✓ 服务器主动推送
- ✓ 自动重连机制
- ✓ 轻量级高效

## 使用示例

```python
from loom.events import EventBus
from loom.protocol import Task

# 创建事件总线
bus = EventBus()

# 注册处理器
async def handle_execute(task: Task) -> Task:
    # 处理任务
    task.result = {"status": "ok"}
    return task

bus.register_handler("execute", handle_execute)

# 发布任务
task = Task(
    source_agent="agent1",
    target_agent="agent2",
    action="execute",
    parameters={"data": "test"}
)
result = await bus.publish(task)
```
