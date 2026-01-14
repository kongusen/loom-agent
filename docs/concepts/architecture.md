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
└── CrewNode (团队)
```

**特点**：
- **统一接口**：所有 Node 都实现 `process()` 方法
- **递归组合**：Crew 可以包含 Agent，也可以包含其他 Crew
- **自相似性**：在不同层级使用相同的模式

## 统一处理架构（Unified Processing Architecture）

loom-agent 采用**统一的ReAct循环处理机制**，所有查询都通过相同的处理流程，根据查询特征自适应调整上下文大小和策略。

### 处理流程（v0.3.7+）

系统使用统一的处理流程，根据查询特征动态调整上下文策略：

```
用户输入 → 添加到记忆 → ReAct循环处理
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
              上下文组装          工具调用
            (根据特征调整)      (按需执行)
                    ↓                   ↓
               LLM调用 ←──────────────┘
                    ↓
              流式输出/完整响应
```

**查询特征提取**（基于QueryFeatureExtractor）：
- 查询长度分析
- 代码检测
- 多步骤识别
- 工具需求检测

**自适应上下文策略**：
- 根据查询特征动态调整上下文大小
- 简单查询：较小的上下文窗口，快速响应
- 复杂查询：完整的上下文窗口，深度分析
- 所有查询使用统一的ReAct循环处理

## 模块分层架构

loom-agent 采用清晰的分层架构，每层职责明确：

```
┌─────────────────────────────────────┐
│         Node Layer (节点层)          │
│   AgentNode, ToolNode, CrewNode     │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│      Cognition Layer (认知层)       │
│   Classifier, Confidence, Features   │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│       Memory Layer (记忆层)         │
│   LoomMemory, Context, Strategy     │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│      Protocol Layer (协议层)        │
│   CloudEvents, MCP, Delegation      │
└─────────────────────────────────────┘
```

### Protocol 层（协议层）

定义跨模块的接口契约和标准化消息格式：

**核心协议**：
- `CloudEvents`: 事件格式标准
- `MCP`: Model Context Protocol（工具定义）
- `Delegation`: Fractal 架构委托协议
- `MemoryOperations`: Memory 系统接口契约

**职责**：
- 统一消息格式
- 定义接口契约
- 支持协议扩展

### Cognition 层（认知层）

负责智能路由和决策：

**核心组件**：
- `QueryFeatureExtractor`: 特征提取器（统一特征提取，包括代码检测、多步骤识别、工具需求等）
- `ConfidenceEstimator`: 置信度评估器（评估响应质量）
- `ContextAssembler`: 上下文组装器（根据特征动态调整上下文）

**职责**：
- 查询特征提取和分析
- 动态上下文策略调整
- 响应质量评估

### Memory 层（记忆层）

管理上下文和记忆：

**核心组件**：
- `LoomMemory`: 4层分层存储（L1/L2/L3/L4）
- `ContextManager`: 上下文管理器
- `ContextAssembler`: 上下文组装器
- `CurationStrategy`: 策展策略（根据查询特征动态选择）
- `L4Compressor`: L4知识库压缩器（自动压缩相似facts）
- `Projection`: 上下文投影系统（支持多种投影模式）

**职责**：
- 分层记忆存储
- 上下文策展
- Token 预算管理
- 异步查询和检索
- L4自动压缩（防止知识库膨胀）
- 智能上下文投影（支持子节点上下文传递）

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

## 相关文档 (Deep Dives)

- [🧠 **自适应处理机制**](dual-system.md) - 查询特征分析与上下文策略
- [💾 **记忆与上下文控制**](memory.md) - L1-L4 记忆层级与新陈代谢
- [🧬 **Agent 模式与节点机制**](agent-node.md) - 分形递归与 Agent 架构
- [🛡️ **协议与事件总线**](protocol.md) - CloudEvents 与协议优先设计
- [认知动力学 (旧版参考)](cognitive-dynamics.md)
- [设计哲学](design-philosophy.md)
