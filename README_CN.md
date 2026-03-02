<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# loom-agent

**Long Horizon Agents Framework**
*当问题变长时，不会崩溃的 Agent。*

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/kongusen/loom-agent)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

[English](README.md) | **中文**

[Wiki 文档](wiki/Home.md) | [示例代码](examples/demo/) | [v0.6.4](https://pypi.org/project/loom-agent/)

</div>

---

## 一个简短的故事

我们构建了许多 Agent。

它们能写代码。
它们能规划任务。
它们能调用工具。

但它们都以同样的方式失败。

不是因为它们不够聪明。
不是因为它们缺少工具。

它们失败，是因为它们太**僵硬**了。

任务变难时，它们不会拆分。
子任务失败时，它们不会适应。
环境变化时，它们不会感知。

我们从生物学中寻找答案。

变形虫是地球上最简单的生物之一。
但它能感知、移动、分裂、适应——没有大脑。

它不做计划，它**响应**。
它不发号施令，它**自组织**。

那一刻我们意识到：

> 问题不在于智能。
> 而在于缺少一个活的机制。

---

## Amoba 机制

真实世界的任务不是 prompt。

它们会转向、分支、失败、演化。编码任务衍生出调试。研究任务拆分成子问题。失败的尝试需要不同的方法。

大多数 Agent 框架是**静态管道**。固定计划、固定 Agent、固定流程。当现实偏离时，它们就崩溃了。

生物学在数十亿年前就解决了这个问题。

变形虫**感知**环境、**匹配**最佳响应、需要时通过分裂来**扩展**、**执行**、**评估**结果、为下次**适应**。

**loom-agent 的 AmoebaLoop 以同样的方式工作：**

```
SENSE → MATCH → SCALE → EXECUTE → EVALUATE → ADAPT
```

* **SENSE** — 分析任务复杂度，检测领域
* **MATCH** — 在能力节点间拍卖竞标，按需演化新技能
* **SCALE** — 通过有丝分裂拆分复杂任务，创建子 Agent
* **EXECUTE** — 以丰富上下文和 token 预算执行
* **EVALUATE** — 评分结果，通过 EMA 奖励更新能力
* **ADAPT** — 回收不健康的 Agent（凋亡），校准复杂度估计，演化技能

表现好的 Agent 变得更强。失败的 Agent 被回收。新的专家按需涌现。系统是**活的**。

---

## loom-agent：结构 + 生命

织机通过**结构**创造织物——线交织、模式重复、张力平衡。

变形虫通过**适应**创造生命——感知、分裂、演化、回收。

**loom-agent 将两者结合。**

框架是织机——可组合的模块将 Agent 编织在一起。
AmoebaLoop 是生命——一个让 Agent 呼吸的自组织循环。

```
结构 (Loom)  →  Agent · Memory · Tools · Events · Interceptors · Context · Skills
生命 (Amoba) →  Sense · Match · Scale · Execute · Evaluate · Adapt
```

复杂性增长，结构不变。Agent 适应，框架承载。

---

## 核心原则

**自组织优于编排** — 没有中心控制器。Agent 通过 AmoebaLoop 自主感知、竞标、适应。

**组合优于继承** — Agent = provider + memory + tools + context + events + interceptors。按需添加。

**分裂优于单体** — 复杂任务通过有丝分裂拆分，生成子 Agent。简单任务直接执行。

**奖励优于规则** — 能力评分在每次执行后通过 EMA 更新。好的 Agent 变强；差的 Agent 被回收。

---

## 适用场景

loom-agent 不是 prompt 集合，不是工具编排包装器，不是工作流引擎。

它是为那些需要**在时间中保持稳定**的系统而设计的：

长期运行的自主工作流 · 研究 Agent · 多日任务执行 · 复杂的 RAG 系统 · 基于 Agent 的 SaaS 后端 · AI 操作员和副驾驶

---

## 安装

```bash
pip install loom-agent
```

## 快速开始

```python
import asyncio
from loom import Agent, AgentConfig
from loom.providers.openai import OpenAIProvider

provider = OpenAIProvider(AgentConfig(
    api_key="sk-...",
    model="gpt-4o-mini",
))

agent = Agent(
    provider=provider,
    config=AgentConfig(system_prompt="你是一个有帮助的助手。", max_steps=3),
)

async def main():
    result = await agent.run("用一句话介绍 Python")
    print(result.content)

asyncio.run(main())
```

### 流式输出

```python
from loom import TextDeltaEvent, DoneEvent

async for event in agent.stream("用一句话介绍 Rust"):
    if isinstance(event, TextDeltaEvent):
        print(event.text, end="", flush=True)
    elif isinstance(event, DoneEvent):
        print(f"\n完成, steps={event.steps}")
```

### 工具调用

```python
from pydantic import BaseModel
from loom import ToolRegistry, define_tool, ToolContext

class CalcParams(BaseModel):
    expression: str

async def calc_fn(params: CalcParams, ctx: ToolContext) -> str:
    return str(eval(params.expression))

tools = ToolRegistry()
tools.register(define_tool("calc", "计算数学表达式", CalcParams, calc_fn))

agent = Agent(provider=provider, config=AgentConfig(max_steps=5), tools=tools)
result = await agent.run("2的20次方是多少？")
```

### 多 Agent 委派

```python
from loom import EventBus

bus = EventBus(node_id="root")

researcher = Agent(
    provider=provider, name="researcher",
    config=AgentConfig(system_prompt="你是研究员", max_steps=2),
    event_bus=bus.create_child("researcher"),
)
writer = Agent(
    provider=provider, name="writer",
    config=AgentConfig(system_prompt="你是写作者", max_steps=2),
    event_bus=bus.create_child("writer"),
)

r1 = await researcher.run("研究 AI Agent 记忆系统")
r2 = await writer.run("撰写技术文章")
```

> 全部 15 个示例见 [examples/demo/](examples/demo/)。

---

## v0.6.4 新特性

### Blueprint Forge — 自主 Agent 创建
当集群中没有合适的 Agent 能处理某个任务时，系统会通过 LLM **自动设计**一个专门的 Agent 蓝图。蓝图包含定制的 `system_prompt`、筛选后的工具集和领域能力分数。蓝图通过 reward 信号持续进化，表现差的蓝图会被自动淘汰。

```python
from loom.cluster.blueprint_forge import BlueprintForge
from loom.cluster.blueprint_store import BlueprintStore

store = BlueprintStore(persist_path=Path("blueprints.json"))
forge = BlueprintForge(llm=provider, store=store)

# LLM 设计专家蓝图 → 孵化 Agent
blueprint = await forge.forge(task)
node = forge.spawn(blueprint, parent_node)
result = await node.agent.run("分析这个数据集")
```

详见 [Blueprint Forge](wiki/Blueprint.md) 完整生命周期文档。

### ToolContext 扩展 — 动态元数据访问
工具现在可以通过 `AgentConfig.tool_context` 接收任意上下文。在 `ToolContext` 上以属性方式直接访问自定义字段：

```python
agent = Agent(
    provider=provider,
    config=AgentConfig(
        tool_context={"documentContext": ["block-A", "block-B"]},
    ),
    tools=registry,
)

# 在工具函数内部：
async def my_tool(params, ctx: ToolContext) -> str:
    docs = ctx.documentContext  # 通过 metadata 的属性式访问
```

### Thinking Model 支持
全面支持推理/思考模型（DeepSeek、QwQ 等），覆盖所有 Provider。`reasoning_content` 字段在流式和非流式模式下均被捕获，通过 `CompletionResult.reasoning` 和 `ReasoningDeltaEvent` 暴露。

---

## 核心特性

### 组合式架构
Agent 由正交模块组装 — provider、memory、tools、context、event bus、interceptors、skills。按需添加，每个模块都是可选的。

### 三层记忆
L1 `SlidingWindow`（近期对话）→ L2 `WorkingMemory`（关键事实）→ L3 `PersistentStore`（长期存储）。以 token 预算驱动，自动压缩。

### 工具系统
`define_tool` + `ToolRegistry`，Pydantic schema 校验。LLM 通过 ReAct 循环自主决定何时调用工具。

### 事件总线
父子事件传播、模式匹配、类型化事件。所有 Agent 生命周期事件通过 EventBus 流转。

### 拦截器链
中间件管道，在 LLM 调用前后变换消息。审计日志、内容过滤、prompt 注入 — 都以拦截器实现。

### 知识库 (RAG)
文档摄入、分块、向量化、混合检索（关键词 + 向量 RRF 融合）。通过 `KnowledgeProvider` → `ContextOrchestrator` 桥接到 Agent。

### 上下文编排
多源上下文收集，自适应预算分配。记忆、知识库和自定义 Provider 统一在 `ContextOrchestrator` 下。

### 技能系统
关键词 / 正则 / 语义触发器自动激活领域技能，动态注入专家指令到 Agent。

### 集群拍卖
能力评分的 Agent 节点竞标任务。`RewardBus` 通过 EMA 在每次执行后更新评分。`LifecycleManager` 监控健康状态。

### 弹性 Provider
`BaseLLMProvider` 内置指数退避重试 + 熔断器。任何 OpenAI 兼容 API 均可通过 `OpenAIProvider` 接入。

### Runtime 与 AmoebaLoop
`Runtime` 编排集群级任务提交。`AmoebaLoop` 实现 6 阶段自组织循环：SENSE → MATCH → SCALE → EXECUTE → EVALUATE → ADAPT。

---

## 文档

详细文档请参阅 [Wiki](wiki/Home.md)：

| 文档 | 说明 | Demo |
| ---- | ---- | ---- |
| [Agent](wiki/Agent.md) | Agent 核心、AgentConfig、run/stream | 01 |
| [工具系统](wiki/Tools.md) | define_tool、ToolRegistry、ToolContext | 02 |
| [事件系统](wiki/Events.md) | EventBus、父子传播 | 03 |
| [拦截器](wiki/Interceptors.md) | InterceptorChain、中间件管道 | 04 |
| [记忆系统](wiki/Memory.md) | L1/L2/L3 三层记忆 | 05 |
| [知识库](wiki/Knowledge.md) | KnowledgeBase、RAG 混合检索 | 06 |
| [上下文编排](wiki/Context.md) | ContextOrchestrator、多源收集 | 07 |
| [技能系统](wiki/Skills.md) | SkillRegistry、触发式激活 | 08 |
| [集群拍卖](wiki/Cluster.md) | ClusterManager、拍卖、RewardBus | 09-10 |
| [蓝图锻造](wiki/Blueprint.md) | BlueprintForge、自主 Agent 创建 | — |
| [弹性 Provider](wiki/Providers.md) | BaseLLMProvider、重试、熔断器、Thinking Model | 11 |
| [运行时](wiki/Runtime.md) | Runtime、AmoebaLoop 6 阶段循环 | 12-13 |
| [架构总览](wiki/Architecture.md) | 全栈流水线、委派、架构图 | 14-15 |

---

## 项目状态

当前版本：**v0.6.4**。

API 可能会快速演化。

结构不会。

---

## 哲学

> 结构承载形态。
> 生命赋予运动。

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

**欢迎来到活的 Agent 世界。**
