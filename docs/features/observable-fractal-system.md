# 可观测分形系统实现方案

> **版本**: v0.5.0
> **基于**: Loom公理系统
> **状态**: 设计完成，待实现

## 摘要

本文档描述了基于公理系统的**可观测分形系统**实现方案，实现了分形节点思考过程的实时流式输出。

**核心特性**：
1. **扁平化观测** - 任何节点都可以直接向观测者发布事件
2. **无层级负担** - 父节点不需要转发子节点事件
3. **实时流式** - 思考过程实时推送给前端
4. **分形兼容** - 完全兼容现有的分形结构

---

## 公理依据

### 核心公理

**公理A2（事件主权）**：
```
∀communication ∈ System: communication = Task
```
所有通信都是Task，天然支持可观测性。

**定理T2（完全可观测性）**：
```
Given: A2 (事件主权)
Prove: ∀behavior ∈ System: behavior is observable
```
系统中的所有行为都是可观测的。

**公理A3（分形自相似）**：
```
∀node ∈ System: structure(node) ≅ structure(System)
```
节点可以递归组合，保持接口一致。

**公理A5（认知调度）**：
```
Cognition = Orchestration(N1, N2, ..., Nk)
```
认知是节点间编排交互的涌现属性，"思考"即是"调度"。

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                         前端观测者                            │
│                    (Browser / Dashboard)                     │
└────────────────────────┬────────────────────────────────────┘
                         │ SSE (Server-Sent Events)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      Stream API                              │
│                  (HTTP/SSE Endpoints)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                 EventStreamConverter                         │
│              (Task → SSE 格式转换)                           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     EventBus                                 │
│                  (事件发布/订阅)                             │
└─────┬──────────────────┴──────────────────┬────────────────┘
      │                                      │
      │ publish events                       │ publish events
      │ (fire-and-forget)                    │ (fire-and-forget)
      │                                      │
┌─────▼──────────────┐              ┌───────▼─────────────────┐
│  ObservableAgent   │              │  ObservableAgent        │
│   (Parent Node)    │              │   (Child Node)          │
│                    │              │                         │
│  - LLM streaming   │              │  - LLM streaming        │
│  - Event publish   │              │  - Event publish        │
└────────────────────┘              └─────────────────────────┘
         │                                   │
         │ wrapped by                        │
         │                                   │
         └──────────► NodeContainer ◄────────┘
                     (Fractal Structure)
```

### 关键特性

#### 1. 扁平化观测（Flat Observation）

**传统层级模型**（不推荐）：
```
前端 ← 父节点 ← 子节点 ← 孙节点
     (转发)   (转发)   (产生事件)
```
问题：父节点需要转发所有子节点事件，增加负担。

**扁平化模型**（推荐）：
```
前端 ←─────────┐
               │
EventBus ←─────┼─── 父节点（直接发布）
               │
               ├─── 子节点（直接发布）
               │
               └─── 孙节点（直接发布）
```
优势：所有节点直接发布到事件总线，无需层级转发。

---

## 实现细节

### Phase 1: 节点执行事件发布

**文件**: `loom/orchestration/observable_node.py`

**核心类**: `ObservableNode`

**功能**：
- 继承自 `BaseNode`
- 在生命周期钩子中发布事件
- 提供 `publish_thinking()`、`publish_tool_call()` 和 `publish_tool_result()` 方法

**事件类型**：
- `node.start` - 节点开始执行
- `node.thinking` - 节点思考过程
- `node.tool_call` - 工具调用
- `node.tool_result` - 工具执行结果
- `node.complete` - 节点执行完成
- `node.error` - 节点执行错误

**示例**：
```python
class ObservableNode(BaseNode):
    async def on_start(self, task: Task) -> None:
        await super().on_start(task)
        await self._publish_event(
            action="node.start",
            parameters={"action": task.action},
            task_id=task.task_id,
        )
```

---

### Phase 2: LLM思考过程捕获

**文件**: `loom/orchestration/observable_agent.py`

**核心类**: `ObservableAgent`

**功能**：
- 继承自 `ObservableNode`
- 使用LLM流式输出
- 捕获并发布思考过程

**实现原理**：
```python
async def _execute_impl(self, task: Task) -> Task:
    async for chunk in self.llm_provider.stream_chat(messages):
        if chunk.type == "text":
            # 发布思考内容
            await self.publish_thinking(
                content=chunk.content,
                task_id=task.task_id,
            )
        elif chunk.type == "tool_call_complete":
            # 发布工具调用
            await self.publish_tool_call(
                tool_name=chunk.content["name"],
                tool_args=chunk.content["arguments"],
                task_id=task.task_id,
            )
```

---

### Phase 3: 事件流式转换

**文件**: `loom/events/stream_converter.py`

**核心类**: `EventStreamConverter`

**功能**：
- 订阅事件总线的事件
- 转换为SSE格式
- 流式推送给前端

**实现原理**：
```python
async def subscribe_and_stream(
    self,
    action_pattern: str,
) -> AsyncIterator[str]:
    # 创建事件队列
    queue: asyncio.Queue[Task] = asyncio.Queue()

    # 注册处理器
    async def event_handler(task: Task) -> Task:
        await queue.put(task)
        return task

    self.event_bus.register_handler(action_pattern, event_handler)

    # 持续从队列读取并转换
    while True:
        task = await queue.get()
        sse_message = self._convert_task_to_sse(task)
        yield sse_message
```

---

### Phase 4: 前端API端点

**文件**: `loom/api/stream_api.py`

**核心类**: `StreamAPI`

**功能**：
- 提供HTTP/SSE端点
- 支持按节点ID、事件类型过滤
- 保持长连接

**API端点**：
- `GET /stream/nodes/{node_id}` - 订阅特定节点的所有事件
- `GET /stream/thinking` - 订阅所有思考过程事件
- `GET /stream/events` - 订阅所有节点事件

**FastAPI集成示例**：
```python
@app.get("/stream/nodes/{node_id}")
async def stream_node(node_id: str):
    return StreamingResponse(
        stream_api.stream_node_events(node_id),
        media_type="text/event-stream",
    )
```

---

## 与分形结构的集成

### 现有分形组件

**NodeContainer** (`loom/fractal/container.py`):
- 实现分形组合
- 委托给子节点执行
- 保持接口一致

**集成方式**：

```python
# 1. 创建可观测子节点
child_agent = ObservableAgent(
    node_id="child-agent",
    llm_provider=provider,
    event_bus=event_bus,  # 关键：注入事件总线
)

# 2. 包装在分形容器中
container = NodeContainer(
    node_id="fractal-container",
    agent_card=agent_card,
    child=child_agent,  # 子节点会直接发布事件
)

# 3. 执行任务
result = await container.execute_task(task)
# 子节点的思考过程会自动发布到事件总线
```

**关键点**：
- 子节点通过 `event_bus` 直接发布事件
- 容器不需要转发事件
- 父节点不需要知道子节点的事件发布

---

## 事件流示例

### 执行流程

```
1. 用户发起任务
   └─> Task(action="execute", target="parent-agent")

2. 父Agent开始执行
   └─> 发布: node.start (parent-agent)

3. 父Agent LLM思考
   └─> 发布: node.thinking (parent-agent, "Let me analyze...")

4. 父Agent调用工具（委托给子Agent）
   └─> 发布: node.tool_call (parent-agent, "delegate_task")

5. 子Agent开始执行（通过容器）
   └─> 发布: node.start (child-agent)

6. 子Agent LLM思考
   └─> 发布: node.thinking (child-agent, "Processing subtask...")

7. 子Agent完成
   └─> 发布: node.complete (child-agent)

8. 父Agent完成
   └─> 发布: node.complete (parent-agent)
```

### 前端接收

```javascript
const eventSource = new EventSource('/stream/events');

eventSource.addEventListener('node.start', (e) => {
    const data = JSON.parse(e.data);
    console.log(`[${data.parameters.node_id}] Started`);
});

eventSource.addEventListener('node.thinking', (e) => {
    const data = JSON.parse(e.data);
    const nodeId = data.parameters.node_id;
    const content = data.parameters.content;
    console.log(`[${nodeId}] 💭 ${content}`);
});

eventSource.addEventListener('node.complete', (e) => {
    const data = JSON.parse(e.data);
    console.log(`[${data.parameters.node_id}] Completed`);
});
```

---

## 公理符合性验证

### ✅ A2（事件主权）

**要求**: 所有通信都是Task

**验证**:
- ✓ 节点事件通过Task发布
- ✓ 使用EventBus统一管理
- ✓ 符合标准Task模型

### ✅ 定理T2（完全可观测性）

**要求**: 所有行为都可观测

**验证**:
- ✓ 节点执行过程发布事件
- ✓ LLM思考过程发布事件
- ✓ 工具调用发布事件
- ✓ 前端可以订阅所有事件

### ✅ A3（分形自相似）

**要求**: 节点结构与系统结构同构

**验证**:
- ✓ ObservableAgent实现NodeProtocol
- ✓ 可以被NodeContainer包装
- ✓ 保持接口一致性

### ✅ A5（认知调度）

**要求**: 认知是编排交互的涌现

**验证**:
- ✓ LLM思考过程通过事件发布
- ✓ 工具调用（委托）通过事件发布
- ✓ 认知过程完全可观测

---

## 性能考虑

### 事件发布开销

**策略**: Fire-and-forget
```python
await self.event_bus.publish(event_task, wait_result=False)
```

**优势**:
- 不阻塞节点执行
- 异步发布，零等待
- 观测者订阅不影响性能

### 事件过滤

**策略**: 在订阅端过滤
```python
# 只订阅特定节点
async for event in converter.stream_node_events("agent-1"):
    ...

# 只订阅思考过程
async for event in converter.stream_thinking_events():
    ...
```

**优势**:
- 减少网络传输
- 降低前端处理负担
- 支持多观测者独立过滤

---

## 使用指南

### 1. 创建可观测Agent

```python
from loom.orchestration.observable_agent import ObservableAgent
from loom.events import EventBus

event_bus = EventBus()

agent = ObservableAgent(
    node_id="my-agent",
    llm_provider=provider,
    event_bus=event_bus,  # 注入事件总线
)
```

### 2. 创建分形结构

```python
from loom.fractal.container import NodeContainer

# 创建子Agent
child = ObservableAgent(
    node_id="child-agent",
    llm_provider=provider,
    event_bus=event_bus,  # 同一个事件总线
)

# 包装在容器中
container = NodeContainer(
    node_id="container",
    agent_card=agent_card,
    child=child,
)
```

### 3. 启动流式API

```python
from loom.api.stream_api import StreamAPI
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()
stream_api = StreamAPI(event_bus)

@app.get("/stream/events")
async def stream_events():
    return StreamingResponse(
        stream_api.stream_all_events(),
        media_type="text/event-stream",
    )
```

### 4. 前端订阅

```javascript
const eventSource = new EventSource('/stream/events');

eventSource.addEventListener('node.thinking', (e) => {
    const data = JSON.parse(e.data);
    displayThinking(data.parameters.content);
});
```

---

## 下一步

### 短期（1-2周）

1. **实现基础组件**
   - ✅ ObservableNode
   - ✅ ObservableAgent
   - ✅ EventStreamConverter
   - ✅ StreamAPI

2. **集成测试**
   - 单元测试
   - 集成测试
   - 性能测试

3. **文档完善**
   - API文档
   - 使用示例
   - 最佳实践

### 中期（1-2月）

1. **前端集成**
   - 恢复loom-studio
   - 实现事件订阅UI
   - 可视化思考过程

2. **性能优化**
   - 事件聚合
   - 采样机制
   - 缓存策略

3. **功能增强**
   - 事件回放
   - 历史查询
   - 实时分析

---

## 总结

本实现方案完全基于Loom公理系统，实现了：

1. **扁平化观测** - 符合公理A2和定理T2
2. **分形兼容** - 符合公理A3
3. **认知可观测** - 符合公理A5
4. **零负担设计** - 父节点不需要转发事件

**核心优势**：
- 架构简洁优雅
- 性能开销极小
- 完全符合公理系统
- 易于扩展和维护

**下一步行动**：
1. 运行演示示例验证设计
2. 编写单元测试和集成测试
3. 集成到现有的分形系统中
