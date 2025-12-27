# 架构设计

> **理解导向** - 深入理解 loom-agent 的核心架构

## 概述

loom-agent 是一个基于事件驱动的 Agent 框架，采用分形（Fractal）设计理念，所有组件都遵循统一的协议。

## 核心设计原则

### 1. 事件驱动架构

所有组件通过事件进行通信，而不是直接调用：

```
Agent A → Event Bus → Agent B
```

**优势**：
- **解耦**：组件之间无直接依赖
- **可观测**：所有交互都可以被监控
- **可扩展**：易于添加拦截器和中间件
- **分布式**：支持跨进程、跨机器部署

### 2. 分形设计（Fractal Design）

所有组件都是 Node，遵循相同的接口：

```
Node (基类)
├── AgentNode (Agent)
├── ToolNode (工具)
├── CrewNode (团队)
└── RouterNode (路由器)
```

**特点**：
- **统一接口**：所有 Node 都实现 `process()` 方法
- **递归组合**：Crew 可以包含 Agent，也可以包含其他 Crew
- **自相似性**：在不同层级使用相同的模式

## 双系统架构（Dual-Process Architecture）

loom-agent 借鉴认知心理学的双系统理论，实现了两个并行的处理系统：

### System 1：反应式系统（Fast Path）

**特点**：快速、直觉、流式输出

```
用户输入 → EventBus → Agent → LLM Stream → StreamChunks → 实时输出
```

**实现机制**：
- 使用流式 API（`stream_chat()`）
- 发出 `agent.stream.chunk` 事件
- 提供即时反馈和响应

**适用场景**：
- 对话交互
- 快速问答
- 实时反馈

### System 2：审慎式系统（Slow Path）

**特点**：深度、理性、思考过程

```
用户输入 → EventBus → Agent → 生成 Thought → 深度思考 → Projection → 洞察输出
```

**实现机制**：
- 创建临时思考节点（Ephemeral Node）
- 维护认知状态空间（CognitiveState）
- 通过投影算子（ProjectionOperator）输出洞察

**适用场景**：
- 复杂推理
- 多步骤规划
- 深度分析

### 双系统协作

两个系统并行工作，互相补充：

```
┌─────────────────────────────────────────┐
│           用户输入 → EventBus            │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
   System 1         System 2
   (快速流)         (深度思考)
       │               │
   StreamChunks    Thoughts
       │               │
       └───────┬───────┘
               │
         投影合并 (Projection)
               │
           最终输出
```

**协作机制**：
- System 2 在 System 1 开始前或并行启动
- System 2 的洞察可以通过 `thought_injection` 注入到 System 1 的流中
- 认知状态（CognitiveState）维护两个系统的共享上下文

**认知状态空间（S）**：
- 高维内部状态：包含所有活跃的思考、记忆、洞察
- 通过投影算子 π 将 S 投影到低维可观测输出 O
- 实现了"内部混沌 → 外部有序"的转换

## 核心组件

### Dispatcher（调度器）

事件调度的核心，负责：
- 管理事件总线（EventBus）
- 路由事件到正确的 Node
- 处理拦截器（Interceptors）

### EventBus（事件总线）

发布-订阅模式的实现：
- Node 订阅特定主题的事件
- 发布事件到订阅者
- 支持异步事件传递

### Node（节点）

所有组件的基类：
- `node_id`：唯一标识符
- `source_uri`：事件源 URI
- `process(event)`：处理事件的核心方法
- `call(target, data)`：调用其他 Node

### AgentNode（Agent 节点）

具有 LLM 能力的智能节点：
- 调用 LLM 生成响应
- 管理工具调用
- 维护对话记忆

### ToolNode（工具节点）

封装具体功能的节点：
- 执行特定任务（计算、文件操作等）
- 提供工具定义（Tool Definition）
- 返回执行结果

### CrewNode（团队节点）

编排多个节点的协作：
- 管理 Agent 列表
- 实现协作模式（sequential, parallel）
- 聚合执行结果

## 事件流程

### 基本调用流程

```
1. 用户调用 → app.run(agent, task)
2. 创建请求事件 → CloudEvent(type="node.request")
3. 发布到事件总线 → EventBus.publish()
4. Agent 接收事件 → agent.process(event)
5. Agent 处理任务 → LLM 调用 + 工具调用
6. 返回响应事件 → CloudEvent(type="node.response")
7. 用户接收结果 ← 返回响应数据
```

### 工具调用流程

当 Agent 需要使用工具时：

```
1. LLM 返回工具调用请求
2. Agent 通过事件总线调用 Tool
3. Tool 执行并返回结果
4. Agent 将结果传回 LLM
5. LLM 生成最终响应
```

## 协议设计

### CloudEvents 标准

loom-agent 使用 CloudEvents 作为事件格式：

```python
{
    "specversion": "1.0",
    "type": "node.request",
    "source": "/node/agent-1",
    "id": "unique-event-id",
    "datacontenttype": "application/json",
    "data": {
        "task": "用户任务"
    }
}
```

**优势**：
- **标准化**：遵循 CNCF CloudEvents 规范
- **互操作性**：易于与其他系统集成
- **可追踪**：支持分布式追踪（traceparent）

### 协议优先（Protocol-First）

所有组件都实现 `NodeProtocol` 接口：

```python
class NodeProtocol(Protocol):
    node_id: str
    source_uri: str

    async def process(self, event: CloudEvent) -> Any:
        ...
```

这确保了组件的可替换性和可测试性。

## 总结

loom-agent 的架构设计体现了以下特点：

1. **事件驱动**：解耦组件，提高可观测性
2. **分形设计**：统一接口，递归组合
3. **协议优先**：标准化通信，易于集成
4. **简单优雅**：最小化复杂度，最大化灵活性

## 相关文档

- [认知动力学](cognitive-dynamics.md) - 理解 Agent 的认知过程
- [设计哲学](design-philosophy.md) - 深入了解设计理念
