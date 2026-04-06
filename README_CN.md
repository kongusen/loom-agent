<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# loom-agent

**面向复杂任务与长链路执行的 Agent Runtime Framework**
*当任务不再能被一轮 prompt 解决时，Agent 需要的是运行时结构。*

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/kongusen/loom-agent)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

[English](README.md) | **中文**

[Wiki 首页](wiki/Home.md) | [文档索引](wiki/README.md) | [PyPI](https://pypi.org/project/loom-agent/)

</div>

---

## 产品定位

Loom 不是 prompt 包装器，也不是把工具简单串起来的 workflow 壳。

它更准确的定位是：

> 面向复杂任务、长周期执行和可控协作场景的 Agent Runtime Framework。

我们关心的不是“怎么再包一层模型调用”，而是“怎么给 Agent 一个更稳、更清晰、更可控的运行时结构”。

当任务开始变长，系统真正遇到的问题通常不是模型不会回答，而是：

- 上下文快速膨胀，质量开始漂移
- 工具越来越多，但治理、边界和审计缺位
- 一旦进入多步骤执行，状态、重试、审批、产物很快退化成脚本堆叠
- 需要子任务拆解和协作时，系统结构变得脆弱

Loom 想解决的是这一层基础设施问题。

---

## Loom 能提供什么

Loom 的核心价值，不是“再造一个 Agent”，而是给 Agent 系统一套更像运行时的骨架。

- **运行时对象模型**：用 `AgentRuntime -> Session -> Task -> Run` 组织执行生命周期
- **上下文控制**：把上下文分区、压缩、续写从业务逻辑中拆出来
- **执行闭环**：让 loop、state machine、decision、heartbeat 成为独立模块
- **工具与治理**：不仅能接工具，还为约束、资源分配、执行治理预留明确位置
- **协作能力**：为 sub-agent、事件驱动协同和 cluster 扩展提供结构骨架
- **安全边界**：把 permissions、constraints、hooks、veto 放进显式模块，而不是散落在业务代码里

这意味着 Loom 更适合“持续运行的 Agent 系统”，而不是“单次对话的模型封装”。

---

## 当前代码事实

这份 README 按当前 `loom/` 和 `wiki/` 的真实实现来写，不把设计目标说成既成事实。

| 能力 | 状态 | 代码依据 |
|---|---|---|
| Runtime API 与对象模型 | 已实现 | `loom/api/` |
| `Session / Task / Run` 句柄接口 | 已实现基础版 | `loom/api/handles.py` |
| 上下文与记忆模块 | 已实现基础版 | `loom/context/`、`loom/memory/` |
| 执行闭环与状态模块 | 已实现基础版 | `loom/execution/` |
| 工具注册与执行层 | 已实现基础版 | `loom/tools/` |
| 多 Agent / 协作模块 | 部分实现 | `loom/orchestration/`、`loom/cluster/` |
| Skill / Plugin / MCP 生态 | 部分实现 | `loom/ecosystem/`、`loom/capabilities/` |
| 权限、约束、安全边界 | 已实现基础版 | `loom/safety/` |

一句话总结现在的状态：

> Loom 已经有清晰的运行时骨架和公开对象模型，更深的执行整合与高级协同能力仍在持续收敛。

---

## 为什么这套结构值得做

很多 Agent 项目都能快速做出 demo，但很难继续长大。

因为真正决定系统上限的，不只是模型能力，而是这些问题有没有被认真设计：

- 运行时对象是否清晰
- 状态迁移是否可观察
- 外部动作是否可治理
- 协作是否有边界
- 安全策略是否有落点
- 模块扩展是否不依赖“大改一遍”

Loom 的宣传点，本质上不是“我们功能特别多”，而是：

> 我们在用更像系统工程的方式，构建 Agent Runtime。

---

## 快速开始

### 安装

```bash
pip install loom-agent
```

### 从 Runtime API 开始

如果你是要把 Loom 接进一个真实系统，建议先从 `loom/api` 开始，而不是直接钻进底层细节。

```python
import asyncio

from loom.api import AgentProfile, AgentRuntime


async def main():
    profile = AgentProfile.from_preset("default")
    runtime = AgentRuntime(profile=profile)

    session = runtime.create_session(metadata={"project": "demo"})
    task = session.create_task(
        goal="分析当前仓库结构",
        context={"repo": "loom-agent"},
    )

    run = task.start()
    result = await run.wait()

    print(result.state.value)
    print(result.summary)


asyncio.run(main())
```

### 需要更深控制时再往下走

- `loom/api/`：给接入方的运行时对象与句柄接口
- `loom/agent/`：更底层的 Agent 内核骨架
- `loom/context/`、`loom/execution/`、`loom/memory/`：执行内核
- `loom/tools/`、`loom/orchestration/`、`loom/safety/`：扩展与控制层

---

## 架构一览

```text
接口层      -> loom/api
核心层      -> loom/agent, loom/context, loom/execution, loom/memory
能力层      -> loom/tools, loom/orchestration, loom/ecosystem, loom/capabilities
保障层      -> loom/safety
外围层      -> loom/providers, loom/evolution, loom/utils
```

从仓库形态上看，Loom 已经不是“几个 helper 的集合”，而是一套边界逐渐清晰的运行时系统。

---

## 适合什么场景

Loom 更适合这些任务：

- 代码开发、重构、审查这类需要长期上下文和多工具联动的工作
- 研究分析这类需要证据、记忆和多轮推进的工作
- Agent 后台或服务端这类需要 `Session / Task / Run / Event / Artifact` 生命周期对象的系统
- 需要 Skill、Plugin、MCP 等生态扩展能力的产品

如果你只是做一次简单问答，或者只需要一层轻量模型封装，Loom 可能比你需要的更重。

---

## 对外表达建议

如果要把 Loom 对外介绍清楚，建议统一用下面这套话术：

- Loom 是面向复杂任务的 Agent Runtime Framework
- 它强调上下文控制、运行时控制、工具治理、多 Agent 协作和安全边界
- 它已经具备清晰的代码骨架与公开对象模型，部分高级能力仍在持续收敛

这套表达的好处是：

- 有宣传张力
- 不会脱离当前代码事实
- 能让外部读者快速理解它和普通 Agent SDK 的差异

---

## 文档入口

- [Wiki 首页](wiki/Home.md)
- [快速开始](wiki/04-开发说明/快速开始.md)
- [Agent 与 Run](wiki/04-开发说明/Agent与Run.md)
- [总体架构](wiki/03-架构说明/总体架构.md)
- [代码能力矩阵](wiki/05-参考资料/代码能力矩阵.md)
- [产品定位](wiki/02-战略表达/产品定位.md)

---

## 当前阶段的最准确定义

Loom 现在最准确的描述不是“一个已经完全成熟的大一统 Agent 平台”，而是：

> 一个以 `loom/api` 为公开入口、以运行时对象模型为主线、在复杂任务与可控协作方向上持续收敛的 Agent Runtime Framework。

这也是它最值得被关注的地方。
