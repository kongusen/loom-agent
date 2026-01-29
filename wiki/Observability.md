# 可观测性 (Observability)

## 定义

**可观测性**是通过观察系统的外部输出理解内部状态的能力。

## 三大支柱

### 1. 日志 (Logging)

```python
import logging

logger = logging.getLogger("loom")

logger.info("Task started", extra={"task_id": task.task_id})
logger.error("Task failed", extra={"error": str(e)})
```

### 2. 指标 (Metrics)

```python
from prometheus_client import Counter, Histogram

task_counter = Counter("tasks_total", "Total tasks")
task_duration = Histogram("task_duration_seconds", "Task duration")

task_counter.inc()
task_duration.observe(duration)
```

### 3. 追踪 (Tracing)

```python
from opentelemetry import trace

tracer = trace.get_tracer("loom")

with tracer.start_as_current_span("execute_task"):
    # 执行任务
    result = await agent.execute_task(task)
```

## Loom 的可观测性

### 事件流

```python
async for event in event_bus.stream():
    print(f"Event: {event.type}")
    print(f"Data: {event.data}")
```

### 思考流式输出

```python
async for chunk in agent.stream_thinking():
    print(chunk.content, end="", flush=True)
```

### 工具调用追踪

```python
@event_bus.subscribe("node.tool_call")
async def track_tool_call(event):
    print(f"Tool: {event.data['tool_name']}")
    print(f"Args: {event.data['tool_args']}")

@event_bus.subscribe("node.tool_result")
async def track_tool_result(event):
    print(f"Result: {event.data['tool_name']} -> {event.data['result']}")
```

## 相关概念

- → [事件总线](Event-Bus)
- → [事件拦截器](Event-Interceptor)

## 代码位置

- `loom/events/`
- `loom/runtime/`

## 反向链接

被引用于: [事件总线](Event-Bus) | [事件拦截器](Event-Interceptor)
