<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# loom-agent

**Long Horizon Agents Framework**
*Agents that don't collapse when problems get long.*

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

[English](README_EN.md) | **中文**

[宣言](MANIFESTO.md) | [文档](docs/README.md) | [快速开始](docs/usage/getting-started.md)

</div>

---

## 一个简短的故事

我们构建了许多 Agent。

它们能写代码。
它们能规划任务。
它们能调用工具。

但它们都以同样的方式失败。

不是在第一步。
不是在第五步。

它们悄无声息地失败——
大约在第二十步。

计划还在。
工具还可用。

但没人记得：

* 为什么启动这个任务
* 已经尝试过什么
* 哪些决策是重要的
* 接下来该由谁行动

Agent 没有崩溃。

它只是**忘记了自己是谁**。

那一刻我们意识到：

> 问题不在于智能。
> 而在于时间。

---

## 长时程崩溃 (The Long Horizon Collapse)

真实世界的任务不是 prompt。

它们跨越数十个步骤、数天时间、不断变化的目标。
计划会过期，上下文会爆炸，记忆会碎片化。

这就是**长时程问题 (Long Horizon Problem)**。

大多数 Agent 框架假设任务是短的、目标是稳定的、失败是一次性的。
它们依赖单一规划器、全局记忆、线性执行流。

这在 Demo 里很好看。

但在第 20 步之后，Agent 开始无休止地重新规划、自相矛盾、重复失败的行动。
添加更多工具只会加速崩溃。

**问题不在于推理能力。**

大多数 Agent 失败，是因为它们没有能够在时间中保持稳定的结构。

> 更多 token 解决不了这个问题。
> 更好的 prompt 也解决不了。
> **能解决的，只有结构。**

---

## loom-agent：结构递归的答案

人类从未用"更高智商"解决复杂性。

我们用的是**重复结构**：团队像部门，部门像公司，公司像生态系统。
即使规模增长，结构保持稳定。这就是分形组织。

**loom-agent 让 Agent 以同样的方式工作。**

不是构建"超级 Agent"，而是构建**自相似的 Agent**。
每个 Agent 都包含相同的核心结构：

```
观察 → 决策 → 执行 → 反思 → 演化
```

一个 Agent 可以创建子 Agent，子 Agent 的行为方式完全相同。
任务变成世界，世界包含更小的世界。

**复杂性增长，结构不变。**

这意味着系统可以无限扩展——无需重新设计架构、无需 prompt 膨胀、无需中心化规划器。

---

## Loom 隐喻

织机不是通过智能创造织物的。

它通过**结构**创造织物。

* 线交织
* 模式重复
* 张力保持平衡

loom-agent 中的 Agent 是线。

框架是织机。

出现的不是工作流——
而是一个随时间持续的活结构。

---

## 核心原则

loom-agent 的设计围绕四个核心信念：

**结构优于智能** — 更聪明的推理不能防止崩溃，稳定的结构可以。

**为长时程而生** — 专为持续数小时或数天、需要重试和恢复、涉及演化目标的任务设计。

**默认分形** — 每个 Agent 都可以成为一个系统，每个系统的行为都像一个 Agent。无需重写架构即可扩展。

**身份先于记忆** — Agent 必须始终知道它们是谁、服务什么角色、属于哪个阶段、负责什么。没有身份，记忆就是噪音。

---

## 适用场景

loom-agent 不是 prompt 集合，不是工具编排包装器，不是工作流引擎。

它是为那些需要**在时间中保持稳定**的系统而设计的：

长期运行的自主工作流 • 研究 Agent • 多日任务执行 • 复杂的 RAG 系统 • 基于 Agent 的 SaaS 后端 • AI 操作员和副驾驶

---

## 快速开始

```bash
pip install loom-agent
```

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
    agent_id="architect",
    name="长时程协调器",
    system_prompt="你是一个专注于长期任务执行的 AI 架构师。",
    capabilities=["tool_use", "reflection"],
)

agent = app.create_agent(config)
print(f"Agent 已就绪: {agent.node_id}")
```

> 更多示例请参阅 [快速开始文档](docs/usage/getting-started.md)。

---

## 核心特性

### 分形架构 (Fractal Architecture)
采用 `CompositeNode` 实现真正的递归组合。无论是单个 Agent 还是复杂的协作团队，在 Loom 中都是一致的节点。

### 代谢记忆系统 (Metabolic Memory)
构建了 L1 (工作记忆) 到 L4 (语义知识库) 的完整记忆谱系。系统自动执行信息的摄入、消化和同化过程。

### 强类型事件总线 (Type-Safe Event Bus)
使用严格的 CloudEvents 标准、基于 Protocol 的处理器定义，为分布式 Agent 系统提供工业级的可观测性。

### 公理化系统设计 (Axiomatic Framework)
建立在 5 条基础公理之上的形式化理论框架，确保系统的逻辑一致性和可预测性。

---

## 文档体系

**理论基础**
* [公理框架](docs/concepts/axiomatic-framework.md) - 理解 Loom 背后的 5 条核心法则
* [分形架构](docs/framework/fractal-architecture.md) - 如何对抗空间熵增

**核心机制**
* [上下文管理](docs/framework/context-management.md) - 智能的 Token 优化策略
* [事件总线](docs/framework/event-bus.md) - 系统的神经系统
* [记忆系统](docs/features/memory-system.md) - L1-L4 代谢记忆详解

**功能与模式**
* [编排模式](docs/features/orchestration.md) - 串行、并行与条件路由
* [工具系统](docs/features/tool-system.md) - 安全的工具执行机制
* [搜索与检索](docs/features/search-and-retrieval.md) - 语义知识库集成

---

## 项目状态

loom-agent 正在积极开发中。

框架专注于：

* Agent 身份建模
* 分形 Agent 组合
* 长时程执行循环
* 结构化记忆分层
* 感知失败的任务演化

API 可能会快速演化。

结构不会。

---

## 哲学

> 智能解决问题。
> 结构在时间中存续。

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

---

**欢迎来到长时程 Agent 的世界。**
