<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# loom-agent

**Long Horizon Agents Framework**
*当问题变长时，不会崩溃的 Agent。*

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

[English](README.md) | **中文**

[Wiki 文档](wiki/Home.md) | [示例代码](examples/demo/)

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

长期运行的自主工作流 · 研究 Agent · 多日任务执行 · 复杂的 RAG 系统 · 基于 Agent 的 SaaS 后端 · AI 操作员和副驾驶

---

## 安装

```bash
# 核心安装（pydantic + numpy + tiktoken）
pip install loom-agent

# 搭配 OpenAI-compatible LLM（DeepSeek, Qwen, Kimi 等）
pip install loom-agent[llm]

# 搭配 Anthropic Claude
pip install loom-agent[anthropic]

# 全部可选依赖
pip install loom-agent[all]
```

## 快速开始

### 创建你的第一个 Agent

```python
import os
import asyncio
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig

async def main():
    # 1. 配置模型服务
    config = LLMConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ.get("OPENAI_BASE_URL"),  # 可选
    )
    llm = OpenAIProvider(config)

    # 2. 创建 Agent
    agent = Agent.create(
        llm=llm,
        system_prompt="你是一个有帮助的助手。",
        max_iterations=5,
    )

    # 3. 运行任务
    result = await agent.run("请用一句话介绍 Python 语言。")
    print(f"结果: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 使用其他 LLM

```python
from loom.providers.llm import DeepSeekProvider, AnthropicProvider
from loom.config.llm import LLMConfig

# DeepSeek
llm = DeepSeekProvider(LLMConfig(api_key="sk-..."))

# Anthropic Claude
llm = AnthropicProvider(LLMConfig(
    provider="anthropic",
    model="claude-3-5-sonnet-20241022",
    api_key="sk-ant-...",
))

# 任何 OpenAI 兼容 API
from loom.providers.llm import OpenAICompatibleProvider
llm = OpenAICompatibleProvider(LLMConfig(
    api_key="sk-...",
    base_url="http://localhost:8000/v1",
    model="my-model",
))
```

### 分形组合：多 Agent 协作

Agent 可以通过 `delegate_task` 元工具自动创建子 Agent，也可以使用 `NodeContainer` 手动组合：

```python
from loom.fractal.container import NodeContainer
from loom.agent.card import AgentCard

# 将 Agent 包装为容器节点
container = NodeContainer(
    node_id="research_team",
    agent_card=AgentCard(
        agent_id="research_team",
        name="Research Team",
        description="研究团队",
        capabilities=["research", "writing"],
    ),
    child=researcher_agent,
)

# 对调用者来说，容器的行为和普通 Agent 一样
await container.execute_task(task)
```

> 更多示例请参阅 [示例代码](examples/demo/)。

---

## 核心特性

### 公理驱动设计
建立在 4 条形式化公理之上：A2 事件主权、A3 分形自相似、A4 记忆层次、A6 四范式自主。所有模块的实现都可追溯到这些公理。

### 分形架构
基于 `NodeContainer` 和 `ParallelExecutor` 实现递归组合。无论是单个 Agent 还是复杂的协作团队，在 Loom 中都是一致的节点。Agent 自动支持 `create_plan`（规划）和 `delegate_task`（委派）两种分形模式。

### Token-First 记忆系统
L1 (8K) → L2 (16K) → L3 (32K) → L4 (100K) 四层记忆，以 token 预算为核心。自动迁移、智能压缩、关键事实提取、语义向量检索。

### 统一事件总线
所有通信基于 Task 模型通过 EventBus 路由。支持内存传输（单机）和 NATS 传输（分布式），层级事件传播，多 Agent 并行 SSE 输出。

### 四范式自主能力
Agent 自主选择执行策略：反思（LLM streaming）、工具使用（ReAct 循环）、规划（create_plan）、协作（delegate_task）。

### 上下文编排
基于 Anthropic Context Engineering 思想的 ContextOrchestrator，多源收集、自适应预算分配、统一检索（记忆 + RAG 知识库）。

### 多 LLM 支持
OpenAI · Anthropic · DeepSeek · Qwen · Gemini · Ollama · Kimi · 豆包 · 智谱 · vLLM · GPUStack，以及任何 OpenAI 兼容 API。

### 渐进式披露配置
从零配置到完全自定义的三层配置体系。Skill 系统遵循 Anthropic 标准格式，支持发现、激活、实例化三阶段。

---

## 文档

详细文档请参阅 [Wiki](wiki/Home.md)：

| 文档 | 说明 |
| ---- | ---- |
| [架构总览](wiki/Architecture.md) | 公理体系、四范式模型、数据流 |
| [Agent](wiki/Agent.md) | Mixin 架构、创建方式、执行接口 |
| [事件系统](wiki/Events.md) | EventBus、动作枚举、传输层 |
| [记忆系统](wiki/Memory.md) | L1-L4 四层记忆、压缩与迁移 |
| [上下文编排](wiki/Context.md) | ContextOrchestrator、预算管理 |
| [运行时](wiki/Runtime.md) | Task 模型、拦截器、Session 隔离 |
| [工具系统](wiki/Tools.md) | SandboxToolManager、内置工具 |
| [技能系统](wiki/Skills.md) | Skill 定义、渐进式披露、激活 |
| [提供者](wiki/Providers.md) | LLM、Knowledge、MCP、Embedding |
| [配置体系](wiki/Config.md) | 渐进式披露配置 |
| [分形架构](wiki/Fractal.md) | 递归组合、继承规则 |
| [可观测性](wiki/Observability.md) | Tracing、Metrics、OTLP 导出 |

---

## 项目状态

loom-agent 正在积极开发中。当前版本：**v0.5.7**。

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
