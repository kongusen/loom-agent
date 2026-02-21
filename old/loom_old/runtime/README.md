# Runtime - 运行时支持

运行时基础设施，支持框架的运行。

## 设计理念

Runtime层提供运行时支持，包括事件调度、拦截器链等基础设施。

## 核心组件

### 1. Dispatcher (`dispatcher.py`)
事件调度器：
- `register_node()`: 注册节点
- `unregister_node()`: 注销节点
- `dispatch()`: 调度任务

### 2. Interceptor (`interceptor.py`)
拦截器基类：
- `before()`: 任务执行前拦截
- `after()`: 任务执行后拦截

### 3. InterceptorChain (`interceptor.py`)
拦截器链：
- `add()`: 添加拦截器
- `execute()`: 执行拦截器链

## 使用示例

```python
from loom.runtime import Dispatcher, InterceptorChain, Interceptor
from loom.events import EventBus

# 创建调度器
bus = EventBus()
dispatcher = Dispatcher(bus)
dispatcher.register_node(node)

# 使用拦截器
chain = InterceptorChain()
chain.add(logging_interceptor)
result = await chain.execute(task, executor)
```
