# 事件主权 (Event Sovereignty)

## 定义

**事件主权**是指每个节点拥有其事件的完全控制权，外部可以观测但不能干预事件发布。

## 核心思想

在分布式系统中，可观测性有两种方式：
1. **侵入式**: 修改代码添加日志，破坏封装
2. **非侵入式**: 通过外部代理监控，但可能遗漏信息

Loom 的创新是：**事件即状态**。节点发布的事件是其内部状态的权威反映，外部可以订阅但不能干预。

## 主权的含义

### 发布者的主权

```python
class Agent:
    async def execute_task(self, task):
        # 节点自主决定发布什么事件
        await self._publish_event(
            type="node.thinking",
            data={"content": "分析中..."}
        )

        # 外部无法阻止或修改这个事件
        # 这是节点的内部状态，拥有完全主权
```

### 订阅者的权利

```python
class EventLogger:
    async def handle(self, event):
        # 订阅者可以观测事件
        print(f"Event: {event.type}")

        # 但不能修改事件
        # event.data = "modified"  # ✗ 不允许

        # 也不能阻止事件传播
        # return False  # ✗ 不支持
```

## 可观测 vs 可控制

### 传统方式：可控制

```python
class AgentWithCallbacks:
    def __init__(self):
        self.before_callback = None
        self.after_callback = None

    async def execute(self, task):
        # 回调可以干预执行
        if self.before_callback:
            result = self.before_callback(task)
            if result == False:  # 回调可以阻止
                return None

        # 执行任务...
```

**问题**:
- 紧耦合：节点需要知道回调的存在
- 不可预测：回调可能改变行为
- 难以调试：不知道谁修改了什么

### Loom 方式：可观测

```python
class AgentWithEvents:
    async def execute(self, task):
        # 发布事件，但不关心谁在监听
        await self._publish_event(
            type="node.started",
            data={"task": task}
        )

        # 执行任务，不受外部影响
        result = await self._execute_impl(task)

        await self._publish_event(
            type="node.completed",
            data={"result": result}
        )
        return result
```

**优势**:
- 松耦合：节点不知道谁在监听
- 可预测：行为不被外部改变
- 易调试：所有事件都被记录

## 事件不可变

一旦事件发布，就不能被修改：

```python
event = Event(
    type="node.thinking",
    data={"content": "原始内容"}
)

await event_bus.publish(event)

# 以下操作都不允许：
event.data = "修改"           # ✗ 不能修改
event_bus.retract(event)     # ✗ 不能撤回
event_bus.intercept(event)   # ✗ 不能拦截
```

## 拦截器 vs 中间件

### 中间件模式（可控制）

```python
# Express.js 风格
app.use((req, res, next) => {
    if (req.path === "/admin") {
        res.status(403).send("Forbidden")  # 可以阻止
    } else {
        next()  # 继续传递
    }
})
```

### 拦截器模式（可观测）

```python
# Loom 风格
class LoggingInterceptor(Interceptor):
    async def intercept(self, context, next_handler):
        # 记录事件，但不能阻止
        print(f"Before: {context.event}")

        # 调用下一个处理器
        result = await next_handler()

        # 记录结果，但不能修改
        print(f"After: {result}")
        return result
```

## 事件溯源

因为事件不可变，所以可以完整追溯历史：

```python
# 查询节点的所有事件
events = await event_bus.query(
    source="/node/researcher",
    start_time="2024-01-27T00:00:00Z",
    end_time="2024-01-27T23:59:59Z"
)

# 重建执行过程
for event in events:
    if event.type == "node.thinking":
        print(f"Thinking: {event.data['content']}")
    elif event.type == "node.tool_call":
        print(f"Tool: {event.data['tool_name']}")
    elif event.type == "node.tool_result":
        print(f"Result: {event.data['tool_name']} -> {event.data['result']}")
```

## 相关概念

- → [公理系统](Axiomatic-System) (A2: 事件主权公理)
- → [事件总线](Event-Bus) (发布订阅机制)
- → [可观测性](Observability) (监控和调试)
- → [拦截器](Interceptor) (横切关注点)

## 参见

- 📖 [设计文档](design/Event-Sovereignty)
- 🔧 [API 指南]: [事件处理](api/Event)

## 代码位置

- 事件定义: `loom/events/event_bus.py`
- 拦截器: `loom/runtime/interceptor.py`

## 反向链接

被引用于: [事件总线](Event-Bus) | [拦截器](Interceptor) | [可观测性](Observability)
