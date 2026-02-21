# Events

EventBus 提供类型化事件系统，支持实时监控 Agent 执行、父子事件传播。

## 基础监控

```python
from loom import Agent, AgentConfig, EventBus, TextDeltaEvent

bus = EventBus(node_id="monitor")
metrics = {"text_deltas": 0, "events": []}

async def collect(e):
    metrics["events"].append(e.type)
    if isinstance(e, TextDeltaEvent):
        metrics["text_deltas"] += 1

bus.on_all(collect)

agent = Agent(
    provider=provider,
    config=AgentConfig(system_prompt="你是助手", max_steps=3),
    event_bus=bus,
)

result = await agent.run("用一句话解释事件驱动架构")
print(f"总事件数: {len(metrics['events'])}")
print(f"事件类型: {sorted(set(metrics['events']))}")
# ['done', 'step_end', 'step_start', 'text_delta']
```

## 父子传播

子 EventBus 的事件自动冒泡到父级，适用于多 Agent 场景：

```python
parent = EventBus(node_id="parent")
parent_log = []
async def on_parent(e):
    parent_log.append(e.type)
parent.on_all(on_parent)

child_bus = parent.create_child("child")
child_agent = Agent(
    provider=provider,
    config=AgentConfig(max_steps=2),
    event_bus=child_bus,
)
await child_agent.run("hi")
print(f"父节点收到: {len(parent_log)} 个事件")
```

## API 参考

```python
bus = EventBus(node_id="name")
bus.on(event_type, handler)       # 监听特定事件
bus.on_all(handler)               # 监听所有事件
bus.create_child(node_id) -> EventBus  # 创建子总线
await bus.emit(event)             # 发射事件
```

## 事件类型一览

| 事件 | 字段 | 触发时机 |
|------|------|---------|
| `TextDeltaEvent` | `text` | 每个流式 token |
| `StepStartEvent` | `step` | 步骤开始 |
| `StepEndEvent` | `step` | 步骤结束 |
| `ToolCallStartEvent` | `name, arguments` | 工具调用开始 |
| `ToolCallEndEvent` | `name, result` | 工具调用结束 |
| `ErrorEvent` | `error` | 错误发生 |
| `DoneEvent` | `content, steps, usage` | 执行完成 |

> 完整示例：[`examples/demo/03_event_bus.py`](../examples/demo/03_event_bus.py)
