# Event System (The Nervous System)

Loom is an **Event-Driven System**. If the Fractal Architecture is the skeletal structure, the Event System is the nervous system that connects everything.

## Axiom 2: Event Sovereignty

The second axiom of Loom states: **"All communication must happen via Tasks (Events)."**

This means there are no backdoor function calls between isolated agents. Every interaction—requests, responses, signals, errors—is encapsulated in a standardized event object.

## Type-Safe Routing

In earlier versions, Loom relied on string-based routing, which was prone to errors (typos, schema mismatches). The current version introduces a **Type-Safe Event Bus**.

### 1. Task Actions
Instead of magic strings, we use Enums (`loom.events.actions`) to define all possible operations:

```python
from loom.events.actions import TaskAction

# Good: Type-safe
event_bus.publish(action=TaskAction.EXECUTE, payload=task)

# Bad: String typo
event_bus.publish(action="executes", ...) # Error
```

Supported Action Categories:
- **`TaskAction`**: `EXECUTE`, `CANCEL`, `QUERY`
- **`MemoryAction`**: `READ`, `WRITE`, `SYNC`
- **`AgentAction`**: `START`, `STOP`, `HEARTBEAT`

### 2. Protocol-based Handlers
Event handlers are now defined by a strict Protocol, ensuring that any function registered to handle an event matches the expected signature.

```python
class TaskHandler(Protocol):
    async def __call__(self, task: Task) -> Task:
        ...
```

## CloudEvents Standard

Loom strictly adheres to the **CNCF CloudEvents 1.0** specification. This ensures interoperability with external tools, monitoring systems, and other microservices.

### Event Structure
Every event in Loom contains:
- `id`: Unique identifier.
- `source`: URI of the sender (e.g., `node://agent-1`).
- `type`: The kind of event (e.g., `com.loom.task.created`).
- `data`: The payload (the task details, result, etc.).

## The Universal Bus

All events flow through a **Universal Event Bus**. This architecture decouples senders from receivers, allowing for:

1.  **Observability**: A monitoring tool can subscribe to the bus and see "thoughts" flowing in real-time.
2.  **Replayability**: Events can be logged and replayed for debugging or training.
3.  **Distribution**: Events can be routed over HTTP, WebSocket, or MQTT, allowing nodes to live on different physical machines.

---

## 消息传递机制架构图 (Message Passing Architecture)

本节展示基于 EventBus 的完整消息传递机制，包括所有设计场景。

### 1. 核心架构图 (Core Architecture)

整体架构展示了节点层、事件总线核心和传输层的关系：

```mermaid
graph TB
    subgraph "节点层 Node Layer"
        BaseNode[BaseNode<br/>基础节点]
        Agent[Agent<br/>智能代理]
        Container[NodeContainer<br/>容器节点]

        BaseNode --> Agent
        BaseNode --> Container
    end

    subgraph "事件总线核心 EventBus Core"
        EB[EventBus<br/>事件总线]
        Registry[Handler Registry<br/>处理器注册表]
        History[Event History<br/>事件历史 max:1000]
    end

    subgraph "传输层 Transport Layer"
        Memory[MemoryTransport<br/>内存传输-本地]
        NATS[NATSTransport<br/>NATS传输-分布式]
    end

    Agent --> |publish| EB
    Container --> |publish| EB
    EB --> Registry
    EB --> History
    EB --> Memory
    EB --> NATS
```

### 2. 多索引系统 (Multi-Index System)

EventBus 使用多索引系统实现高效的事件查询：

```mermaid
graph LR
    EB[EventBus<br/>事件总线]

    subgraph "索引系统 Index System"
        IdxNode[events_by_node<br/>按节点ID索引]
        IdxAction[events_by_action<br/>按动作类型索引]
        IdxTask[events_by_task<br/>按任务ID索引]
        IdxTarget[events_by_target<br/>按目标代理/节点索引]
    end

    EB --> |record_event| IdxNode
    EB --> |record_event| IdxAction
    EB --> |record_event| IdxTask
    EB --> |record_event| IdxTarget

    IdxNode --> |query_by_node| Result[查询结果]
    IdxAction --> |query_by_action| Result
    IdxTask --> |query_by_task| Result
    IdxTarget --> |query_by_target| Result
```

### 3. 消息传递场景 (Message Passing Scenarios)

#### 场景 1: 本地执行 (Local Execution)

同步等待模式，适用于需要立即获取结果的场景：

```mermaid
sequenceDiagram
    participant Node as 节点 Node
    participant EB as 事件总线 EventBus
    participant Registry as 处理器注册表
    participant Handler as 处理器 Handler
    participant History as 事件历史

    Node->>EB: publish(task, wait_result=True)
    EB->>Registry: 查找处理器 lookup handler
    Registry-->>EB: 返回处理器 return handler
    EB->>Handler: 执行处理器 execute handler
    Handler-->>EB: 返回结果 return result
    EB->>History: 记录事件 record event
    EB-->>Node: 返回结果 return result
```

#### 场景 2: 分布式执行 (Distributed Execution)

跨机器的消息传递，通过传输层实现：

```mermaid
sequenceDiagram
    participant Node1 as 节点1 Node1
    participant EB1 as 事件总线1 EventBus1
    participant Transport as 传输层 Transport
    participant EB2 as 事件总线2 EventBus2
    participant Node2 as 节点2 Node2

    Node1->>EB1: publish(task)
    EB1->>Transport: publish(topic, message)
    Transport->>EB2: 订阅消息 subscribed message
    EB2->>Node2: 执行处理器 execute handler
    Node2-->>EB2: 返回结果 return result
    EB2->>Transport: 发布响应 publish response
    Transport->>EB1: 响应消息 response message
    EB1-->>Node1: 返回结果 return result
```

#### 场景 3: Fire-and-Forget 模式

异步非阻塞模式，适用于不需要等待结果的场景：

```mermaid
sequenceDiagram
    participant Node as 节点 Node
    participant EB as 事件总线 EventBus
    participant Async as 异步任务 Async Task
    participant Handler as 处理器 Handler

    Node->>EB: publish(task, wait_result=False)
    EB->>Async: asyncio.create_task()
    EB-->>Node: 立即返回 RUNNING 状态
    Note over Node: 节点继续执行<br/>不等待结果
    Async->>Handler: 后台执行 background execution
    Handler-->>Async: 完成 complete
    Async->>EB: 记录事件 record event
```

#### 场景 4: 点对点消息传递 (Point-to-Point Messaging)

带优先级和 TTL 的定向消息传递：

```mermaid
sequenceDiagram
    participant NodeA as 节点A Node A
    participant EB as 事件总线 EventBus
    participant Index as 目标索引 Target Index
    participant NodeB as 节点B Node B

    NodeA->>EB: publish_message(target_agent, content, ttl, priority)
    EB->>Index: 记录到 events_by_target
    Note over Index: 存储: target_agent<br/>TTL: 过期时间<br/>Priority: 优先级
    NodeB->>EB: query_by_target(target_agent)
    EB->>Index: 查询消息 query messages
    Index->>Index: 过滤过期消息 filter by TTL
    Index->>Index: 按优先级排序 sort by priority
    Index-->>NodeB: 返回消息列表 return messages
```

#### 场景 5: 任务委托 (Task Delegation)

代理间的任务委托，带超时机制：

```mermaid
sequenceDiagram
    participant AgentA as 代理A Agent A
    participant EB as 事件总线 EventBus
    participant DH as 委托处理器 DelegationHandler
    participant AgentB as 代理B Agent B

    AgentA->>DH: delegate_task(target_agent_id, subtask)
    DH->>DH: 创建 Future 对象
    DH->>EB: publish(delegation_request)
    Note over DH: 等待响应<br/>超时: 30秒
    EB->>AgentB: 转发委托请求
    AgentB->>AgentB: 执行子任务
    AgentB->>EB: publish(delegation_response)
    EB->>DH: 接收响应
    DH->>DH: 解析 Future
    DH-->>AgentA: 返回结果或超时错误
```

### 4. 查询模式 (Query Patterns)

#### 集体记忆查询 (Collective Memory Query)

节点可以查询其他节点的思考过程和工具调用，形成"集体无意识"：

```mermaid
graph TB
    QueryNode[查询节点<br/>Query Node]
    EB[事件总线<br/>EventBus]

    subgraph "集体记忆 Collective Memory"
        Node1Thinking[节点1思考过程]
        Node1Tools[节点1工具调用]
        Node2Thinking[节点2思考过程]
        Node2Tools[节点2工具调用]
        Node3Thinking[节点3思考过程]
        Node3Tools[节点3工具调用]
    end

    QueryNode -->|query_collective_memory| EB
    EB --> Node1Thinking
    EB --> Node1Tools
    EB --> Node2Thinking
    EB --> Node2Tools
    EB --> Node3Thinking
    EB --> Node3Tools

    Node1Thinking --> Result[聚合结果<br/>按节点分组]
    Node1Tools --> Result
    Node2Thinking --> Result
    Node2Tools --> Result
    Node3Thinking --> Result
    Node3Tools --> Result
    Result --> QueryNode
```

### 5. 错误处理与边界情况 (Error Handling & Edge Cases)

#### 错误处理流程

```mermaid
graph TB
    Start[发布任务] --> HasHandler{是否有处理器?}

    HasHandler -->|否| NoHandler[状态: FAILED<br/>错误: No handler found]
    HasHandler -->|是| Execute[执行处理器]

    Execute --> Success{执行成功?}
    Success -->|是| Record[记录事件到历史]
    Success -->|否| Error[状态: FAILED<br/>捕获异常信息]

    Error --> Record
    NoHandler --> Record
    Record --> CheckHistory{历史大小 > max?}

    CheckHistory -->|是| RemoveOld[移除最旧事件<br/>更新所有索引]
    CheckHistory -->|否| Done[完成]
    RemoveOld --> Done
```

#### 边界情况处理

| 边界情况 | 处理策略 |
|---------|---------|
| **无处理器** | 状态设为 FAILED，记录错误信息 |
| **处理器异常** | 捕获异常，状态设为 FAILED，记录错误详情 |
| **Fire-and-Forget 异常** | 使用 `contextlib.suppress` 抑制异常，不影响调用方 |
| **历史大小超限** | 移除最旧事件，更新所有索引，防止内存膨胀 |
| **TTL 过期消息** | 查询时过滤，基于 UTC 时间检查 |
| **委托超时** | 默认 30 秒超时，返回错误信息，清理待处理请求 |
| **容器递归深度** | 跟踪 `_container_depth`，默认最大深度 100，防止栈溢出 |
| **优先级消息排序** | 先按优先级 (0-1，高优先)，再按时间戳 (新优先) |

### 6. 关键特性总结 (Key Features)

#### 核心能力

1. **类型安全路由** - 使用枚举而非字符串，避免拼写错误
2. **多索引系统** - 支持按节点、动作、任务、目标多维度查询
3. **双模式发布** - 同步等待 vs 异步非阻塞
4. **分布式支持** - 通过传输层抽象支持本地和分布式部署
5. **点对点消息** - 带 TTL 和优先级的定向消息传递
6. **任务委托** - 代理间异步任务委托，带超时保护
7. **集体记忆** - 跨节点的思考过程和工具调用共享
8. **事件历史** - 完整的事件记录，支持回放和调试
9. **CloudEvents 标准** - 符合 CNCF CloudEvents 1.0 规范
10. **流式转换** - 支持 SSE 格式的实时事件流

#### 动作类型参考 (Action Types Reference)

**TaskAction** (任务动作):
- `EXECUTE` - 执行任务
- `CANCEL` - 取消任务
- `QUERY` - 查询任务状态
- `STREAM` - 流式任务执行

**MemoryAction** (内存动作):
- `READ` - 读取内存
- `WRITE` - 写入内存
- `SEARCH` - 搜索内存
- `SYNC` - 同步内存

**AgentAction** (代理动作):
- `START` - 启动代理
- `STOP` - 停止代理
- `STATUS` - 查询代理状态
- `HEARTBEAT` - 代理心跳

**Node-Specific Actions** (节点特定动作):
- `node.thinking` - 思考过程事件
- `node.tool_call` - 工具调用事件
- `node.tool_result` - 工具执行结果
- `node.message` - 点对点消息
- `node.start` - 任务开始事件
- `node.complete` - 任务完成事件
- `node.error` - 错误事件
- `node.planning` - 规划阶段事件
- `node.tool_call_request` - 工具调用审批钩子
- `node.delegation_request` - 委托请求

### 7. 使用示例 (Usage Examples)

#### 基本发布订阅

```python
from loom.events import EventBus, Task
from loom.events.actions import TaskAction

# 创建事件总线
event_bus = EventBus()

# 注册处理器
async def handle_task(task: Task) -> Task:
    # 处理任务逻辑
    task.status = "completed"
    return task

event_bus.register_handler(TaskAction.EXECUTE, handle_task)

# 发布任务 (同步等待)
task = Task(action=TaskAction.EXECUTE, data={"input": "test"})
result = await event_bus.publish(task, wait_result=True)

# 发布任务 (异步非阻塞)
result = await event_bus.publish(task, wait_result=False)
```

#### 点对点消息传递

```python
# 节点 A 发送消息给节点 B
await node_a.publish_message(
    target_agent="agent-b",
    content="Hello from A",
    priority=0.8,
    ttl_seconds=60
)

# 节点 B 查询消息
messages = event_bus.query_by_target(
    target_agent="agent-b",
    limit=10
)
```

#### 查询集体记忆

```python
# 查询所有节点的思考过程和工具调用/结果
collective_memory = event_bus.get_collective_memory(
    action_types=["node.thinking", "node.tool_call", "node.tool_result"],
    limit=100
)

# 结果按节点分组
for node_id, events in collective_memory.items():
    print(f"Node {node_id}: {len(events)} events")
```

---

**相关文档**:
- [Fractal Architecture](./fractal-architecture.md) - 分形架构设计
- [Memory System](../features/memory-system.md) - 内存系统
- [Orchestration](../features/orchestration.md) - 编排系统
