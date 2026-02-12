# Loom Agent Framework

Loom 是一个公理驱动的多智能体框架，基于事件驱动架构和分形自相似原则构建。支持四范式自主工作模式：反思、工具使用、规划、协作。

## 核心特性

- **公理驱动设计** — 基于形式化公理体系（A2 事件主权、A3 分形自相似、A4 记忆层次、A6 四范式自主）
- **四范式自主能力** — Agent 自主选择反思、工具使用、规划、协作策略
- **Token-First 记忆系统** — L1-L4 四层记忆，以 token 预算为核心的智能管理
- **分形架构** — 父子节点递归组合，配置继承，记忆层级传递
- **统一事件总线** — 所有通信基于 Task 模型，支持本地/分布式传输
- **渐进式披露配置** — 从零配置到完全自定义的三层配置体系
- **多 LLM 支持** — Anthropic、OpenAI、DeepSeek、Qwen、Gemini、Ollama 等
- **RAG 知识库集成** — 向量检索、图谱检索、关键词检索的混合策略
- **OpenTelemetry 可观测性** — 结构化 Tracing + Metrics 导出

## 快速开始

```python
from loom import Agent
from loom.providers.llm.openai import OpenAIProvider

llm = OpenAIProvider(model="gpt-4o-mini")

# 最简创建
agent = Agent.create(llm, system_prompt="你是一个AI助手")
result = await agent.run("帮我分析这段代码的性能问题")

# Builder 模式
agent = (Agent.builder(llm)
    .with_system_prompt("你是一个代码审查专家")
    .with_tools([...])
    .build())
```

## 模块导航

| 模块 | 说明 | 文档 |
|------|------|------|
| `loom/agent/` | Agent 核心（Mixin 架构、Builder、Factory） | [Agent](Agent.md) |
| `loom/events/` | 事件总线、Task 路由、传输层 | [Events](Events.md) |
| `loom/memory/` | L1-L4 记忆层、压缩、向量存储 | [Memory](Memory.md) |
| `loom/context/` | 上下文编排、预算管理、检索 | [Context](Context.md) |
| `loom/runtime/` | Task 模型、状态管理、拦截器 | [Runtime](Runtime.md) |
| `loom/tools/` | 工具注册、沙盒执行、内置工具 | [Tools](Tools.md) |
| `loom/tools/skills/` | 技能定义、激活、加载 | [Skills](Skills.md) |
| `loom/providers/` | LLM、Knowledge、MCP、Embedding | [Providers](Providers.md) |
| `loom/config/` | 渐进式披露配置体系 | [Config](Config.md) |
| `loom/fractal/` | 分形组合、并行执行、结果聚合 | [Fractal](Fractal.md) |
| `loom/observability/` | Tracing、Metrics、导出器 | [Observability](Observability.md) |

## 架构总览

详见 [Architecture](Architecture.md)。

```
┌─────────────────────────────────────────────────────┐
│                    Agent (Mixin 组合)                 │
│  ┌──────────┬──────────┬──────────┬────────────────┐ │
│  │ToolHandler│SkillHandler│Planner │  Delegator     │ │
│  │  Mixin   │  Mixin   │ Mixin  │   Mixin        │ │
│  └──────────┴──────────┴──────────┴────────────────┘ │
│                  ExecutorMixin + BaseNode             │
├─────────────────────────────────────────────────────┤
│  Context Orchestrator  │  Memory Manager (L1-L4)    │
├─────────────────────────────────────────────────────┤
│  EventBus (Task 路由)  │  Tool System (Sandbox)     │
├─────────────────────────────────────────────────────┤
│  LLM Providers │ Knowledge/RAG │ MCP │ Observability│
└─────────────────────────────────────────────────────┘
```

## 版本

当前版本：**v0.5.6**

许可证：Apache-2.0 with Commons Clause
