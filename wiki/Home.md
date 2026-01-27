# Loom Agent Framework

**The Controlled Fractal Agent Framework**

Protocol-First • Metabolic Memory • Fractal Nodes

---

## 📖 文档导航

### 按阅读路径

**新手入门** → [快速开始](Getting-Started) | [基础概念](Concepts-Overview) | [示例教程](Examples)

**框架研究者** → [公理系统](Axiomatic-System) | [核心架构](Core-Architecture) | [设计文档](Design-Docs)

**API 开发者** → [Agent API](API-Agent) | [记忆 API](API-Memory) | [工具开发](Tool-Development)

**框架扩展者** → [扩展指南](Extension-Guide) | [插件系统](Plugin-System) | [拦截器](Interceptor)

### 按主题

[🏗️ 架构](#架构) | [💾 记忆系统](#记忆系统) | [⚡ 事件系统](#事件系统) | [🤖 Agent 能力](#agent-能力) | [🔧 工具与扩展](#工具与扩展)

---

## 🎯 框架概览

Loom 是一个**高可靠 (High-Assurance)** 的 AI Agent 框架，基于严格的**公理系统**构建。

### 核心特性

| 特性 | 描述 | 文档 |
|------|------|------|
| **公理化设计** | 5条基础公理确保逻辑一致性 | [公理系统](Axiomatic-System) |
| **分形架构** | O(1) 认知负载的递归组合 | [分形架构](Fractal-Architecture) |
| **代谢记忆** | L1-L4 完整记忆谱系 | [代谢记忆](Metabolic-Memory) |
| **事件总线** | 类型安全的分布式通信 | [事件总线](Event-Bus) |
| **四范式** | Reflection/Tool/Planning/Collaboration | [四范式工作](Four-Paradigms) |

### 版本信息

- **当前版本**: v0.4.3
- **Python 要求**: 3.11+
- **许可证**: Apache 2.0 + Commons Clause

---

## 🏗️ 架构

### 系统分层

```
┌─────────────────────────────────────┐
│         API 层 (loom.api)           │  ← 用户接口
├─────────────────────────────────────┤
│      编排层 (Orchestration)          │  ← Agent, Workflow, Router
├─────────────────────────────────────┤
│      分形层 (Fractal)                │  ← FractalNode, CompositeNode
├─────────────────────────────────────┤
│      记忆层 (Memory)                 │  ← L1-L4 Memory System
├─────────────────────────────────────┤
│      事件层 (Events)                 │  ← EventBus, CloudEvents
├─────────────────────────────────────┤
│      协议层 (Protocol)               │  ← Protocol Definitions
└─────────────────────────────────────┘
```

**详细架构**: [Core-Architecture](Core-Architecture)

---

## 💾 记忆系统

### 四层记忆谱系

| 层级 | 名称 | 容量 | 用途 | 文档 |
|------|------|------|------|------|
| L1 | 工作记忆 | ~50 tasks | 最近任务，FIFO | [Circular-Buffer](Memory-L1-Circular) |
| L2 | 优先级队列 | ~100 tasks | 重要任务，按重要性排序 | [Priority-Queue](Memory-L2-Priority) |
| L3 | 向量存储 | 无限 | 语义检索，长期记忆 | [Vector-Store](Memory-L3-Vector) |
| L4 | 知识图谱 | 无限 | 结构化知识，推理 | [Knowledge-Graph](Memory-L4-Knowledge) |

**记忆管理**: [Context-Management](Context-Management) | [Memory-Scope](Memory-Scope)

---

## ⚡ 事件系统

### 事件驱动架构

- **Event Bus**: 类型安全的发布-订阅总线
- **CloudEvents**: 标准事件格式
- **拦截器**: AOP 风格的横切关注点

**核心事件**:
- `node.thinking` - Agent 思考过程
- `node.tool_call` - 工具调用
- `node.done` - 任务完成

**文档**: [Event-Bus](Event-Bus) | [Interceptor](Interceptor) | [Observability](Observability)

---

## 🤖 Agent 能力

### 四范式工作模式

1. **反思 (Reflection)** - 持续思考和分析
2. **工具使用 (Tool Use)** - 执行具体操作
3. **规划 (Planning)** - 任务分解
4. **协作 (Collaboration)** - 多 Agent 协作

**文档**: [Four-Paradigms](Four-Paradigms) | [Autonomous-Capabilities](Autonomous-Capabilities)

---

## 🔧 工具与扩展

### 工具系统

- **工具注册**: 动态注册工具到 Agent
- **工具执行**: 安全的工具调用机制
- **元工具**: Planning, Delegation 等高阶工具

**文档**: [Tool-System](Tool-System) | [Meta-Tools](Meta-Tools)

### 扩展机制

- **Skills**: Progressive Disclosure 能力加载
- **拦截器**: 自定义事件处理
- **自定义 LLM Provider**: 支持任意 LLM 后端

**文档**: [Skills](Skills) | [Extension-Guide](Extension-Guide)

---

## 📚 完整文档索引

### 概念文档

[公理系统](Axiomatic-System) | [协议优先](Protocol-First) | [事件主权](Event-Sovereignty) | [分形递归](Fractal-Recursion)

[分形架构](Fractal-Architecture) | [分形节点](Fractal-Node) | [组合节点](Composite-Node) | [执行策略](Execution-Strategy)

[代谢记忆](Metabolic-Memory) | [记忆分层](Memory-Layers) | [记忆作用域](Memory-Scope) | [上下文管理](Context-Management)

[事件总线](Event-Bus) | [CloudEvents](CloudEvents) | [事件拦截器](Event-Interceptor) | [可观测性](Observability)

[四范式工作](Four-Paradigms) | [自主能力](Autonomous-Capabilities) | [工具系统](Tool-System) | [Skills](Skills)

### API 文档

[Agent API](API-Agent) | [记忆 API](API-Memory) | [事件 API](API-Event) | [工具 API](API-Tool)

### 设计文档

[公理系统设计](design/Axiomatic-System) | [分形架构设计](design/Fractal-Architecture) | [记忆系统设计](design/Memory-System)

### 示例代码

[快速开始示例](examples/Quick-Start) | [研究小组示例](examples/Research-Team) | [工具开发示例](examples/Tool-Development)

---

## 🔗 外部资源

- **GitHub 仓库**: [https://github.com/kongusen/loom-agent](https://github.com/kongusen/loom-agent)
- **PyPI 包**: [https://pypi.org/project/loom-agent](https://pypi.org/project/loom-agent)
- **DeepWiki**: [https://deepwiki.com/kongusen/loom-agent](https://deepwiki.com/kongusen/loom-agent)

---

**最后更新**: v0.4.3
