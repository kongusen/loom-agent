<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# Loom

**The Controlled Fractal Agent Framework**

Protocol-First • Metabolic Memory • Fractal Nodes

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

[English](README_EN.md) | **中文**

[文档索引](docs/README.md) | [公理框架](docs/concepts/axiomatic-framework.md) | [快速开始](docs/usage/getting-started.md)

</div>

---

## 概览

Loom 是一个**高可靠 (High-Assurance)** 的 AI Agent 框架，旨在解决构建复杂**认知生命体 (Cognitive Organisms)** 时的核心挑战。

不同于专注于快速原型的实验性框架，Loom 建立在严格的**公理系统**之上。它通过**分形架构**解决空间复杂度的无限增长，通过**代谢记忆**对抗时间跨度上的认知熵增。Loom 不是为了写一个 Demo，而是为了构建能够在生产环境中长期稳定运行、自我演进的智能系统。

### 核心特性 (v0.4.2)

#### 1. 公理化系统设计 (Axiomatic Framework)
建立在 5 条基础公理之上的形式化理论框架，确保系统的逻辑一致性和可预测性。从统一接口到事件主权，每一个设计决策都有理论支撑，而非临时拼凑。

#### 2. 分形架构与无限组合 (Fractal Architecture)
采用 `CompositeNode` 实现真正的递归组合。无论是单个 Agent 还是复杂的协作团队，在 Loom 中都是一致的节点。这种架构保证了无论系统多复杂，任意局部的认知负载始终保持常数级别 (O(1))。

#### 3. 代谢记忆系统 (Metabolic Memory)
模仿生物认知机制，构建了 L1 (工作记忆) 到 L4 (语义知识库) 的完整记忆谱系。系统自动执行信息的摄入、消化和同化过程，结合 pgvector/Qdrant 向量检索，让 Agent 拥有越用越聪明的长期记忆。

#### 4. 强类型事件总线 (Type-Safe Event Bus)
拒绝"魔术字符串"和不可靠的隐式调用。Loom 使用严格的 CloudEvents 标准、基于 Protocol 的处理器定义和类型安全的 Action 枚举，为分布式 Agent 系统提供工业级的可观测性和稳定性。

#### 5. 现代化的开发体验
基于 FastAPI 风格的声明式 API，集成 Pydantic 全链路数据验证。内置对 OpenAI, Anthropic, Gemini, DeepSeek 等主流模型的原生支持，开箱即用 SSE 流式输出和结构化响应。

---

## 安装

```bash
pip install loom-agent
```

## 快速上手

### 创建你的第一个 Agent

Loom 提供了极简的声明式 API：

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 1. 初始化应用
app = LoomApp()

# 2. 配置模型服务
llm = OpenAIProvider(api_key="your-api-key")
app.set_llm_provider(llm)

# 3. 定义 Agent
config = AgentConfig(
    agent_id="assistant",
    name="智能助手",
    system_prompt="你是一个专业、严谨的 AI 助手。",
    capabilities=["tool_use", "reflection"],
)

agent = app.create_agent(config)
print(f"Agent 已就绪: {agent.node_id}")
```

### 构建分形小队

通过组合模式，将多个 Agent 封装为一个单一的逻辑节点：

```python
from loom.fractal.composite import CompositeNode
from loom.fractal.strategies import ParallelStrategy

# 将研究员和撰稿人组合成一个"研究小组"
team_node = CompositeNode(
    node_id="research_team",
    children=[researcher_agent, writer_agent],
    strategy=ParallelStrategy() # 并行执行
)

# 对调用者而言，这个小组就像一个普通的 Agent
await team_node.execute_task(task)
```

> 更多示例请参阅 [快速开始文档](docs/usage/getting-started.md)。

---

## 文档体系

我们提供了从理论基础到工程实践的完整文档：

**理论基础**
*   [公理框架](docs/concepts/axiomatic-framework.md) - 理解 Loom 背后的 5 条核心法则
*   [分形架构](docs/framework/fractal-architecture.md) - 如何对抗空间熵增

**核心机制**
*   [上下文管理](docs/framework/context-management.md) - 智能的 Token 优化策略
*   [事件总线](docs/framework/event-bus.md) - 系统的神经系统
*   [记忆系统](docs/features/memory-system.md) - L1-L4 代谢记忆详解

**功能与模式**
*   [编排模式](docs/features/orchestration.md) - 串行、并行与条件路由
*   [工具系统](docs/features/tool-system.md) - 安全的工具执行机制
*   [搜索与检索](docs/features/search-and-retrieval.md) - 语义知识库集成

---

## 社区与联系

欢迎加入 Loom 开发者社区，与我们共同探讨下一代 Agent 架构。

<img src="QRcode.jpg" width="200" alt="Loom Community WeChat"/>

---

## 许可证

**Apache License 2.0 with Commons Clause**.

本软件允许免费用于学术研究、个人学习和内部商业使用。
**严禁未经授权的商业销售**（包括但不限于将本软件打包收费、提供托管服务等）。
详情请见 [LICENSE](LICENSE)。
