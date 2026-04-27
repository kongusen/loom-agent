<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# Loom

**面向 Python 应用的 Agent SDK：状态化运行、上下文控制、安全边界和可扩展能力。**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/kongusen/loom-agent)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

[English](README.md) | **中文**

[Wiki](wiki/Home.md) | [快速开始](wiki/01-getting-started/README.md) | [PyPI](https://pypi.org/project/loom-agent/) | [Changelog](CHANGELOG.md)

</div>

---

Loom 是一个可嵌入应用的 Agent SDK，不是 Hermes 那类完整 Agent 产品。它不内建 gateway 产品层、cron 服务、dashboard 或 skill market；这些外部系统应该通过 adapter 把事件归一成 runtime signal，再交给内核处理。

`0.8.0` 稳定的是 SDK runtime kernel：

```text
Agent + Runtime + Capability
    -> Run / Session
    -> RuntimeTask / RuntimeSignal
    -> Context / Continuity / Harness / Quality / Governance / Feedback
```

旧 0.x 兼容接口会保留到 `0.8.x`，计划在 `0.9.0` 移除。

## 安装

```bash
pip install loom-agent
export ANTHROPIC_API_KEY=sk-ant-...
```

## 快速开始

```python
import asyncio

from loom import Agent, Capability, Generation, Model, Runtime, tool


@tool(description="搜索文档", read_only=True)
async def search_docs(query: str) -> str:
    return f"结果: {query}"


async def main():
    agent = Agent(
        model=Model.anthropic("claude-sonnet-4"),
        instructions="你是一个简洁的代码助手。",
        tools=[search_docs],
        capabilities=[
            Capability.files(read_only=True),
            Capability.web(),
        ],
        generation=Generation(max_output_tokens=512),
        runtime=Runtime.sdk(),
    )

    result = await agent.run("概括这个仓库")
    print(result.output)


asyncio.run(main())
```

## 公共 API 形状

常规应用代码从 `loom` 导入：

```python
from loom import (
    Agent,
    Capability,
    Model,
    Runtime,
    RuntimeSignal,
    RuntimeTask,
    SessionConfig,
    SignalAdapter,
    RunContext,
    tool,
)
```

推荐的应用结构：

```text
Agent(...)
    -> run(...)
    -> stream(...)
    -> receive(...)
    -> session(SessionConfig(...))
          -> Session
                -> start(...) / run(...) / stream(...) / receive(...)
```

兼容和高级配置路径仍然存在：

- `AgentConfig`、`ModelRef`、`GenerationConfig`、`create_agent()` 会保留到 `0.8.x`
- 新文档和示例优先使用 `Agent`、`Model`、`Generation`、`Runtime`、`Capability`
- `loom.compat.v0` 是显式旧兼容命名空间，计划在 `0.9.0` 移除

## Runtime 语言

简单调用可以直接传字符串：

```python
result = await agent.run("列出这次变更的主要风险")
```

任务需要成功标准、结构化输入或元数据时，用 `RuntimeTask`：

```python
from loom import RuntimeTask

result = await agent.run(
    RuntimeTask(
        goal="重构 runtime API",
        input={"scope": "agent + runtime kernel"},
        criteria=["保持公共 API 兼容", "测试通过"],
    )
)
```

长任务机制通过 `Runtime` 组合：

```python
from loom import Capability, Model, Runtime

agent = Agent(
    model=Model.openai("gpt-5.1"),
    capabilities=[
        Capability.files(read_only=True),
        Capability.web(),
        Capability.shell(require_approval=True),
    ],
    runtime=Runtime.long_running(criteria=["tests stay green"]),
)
```

常用 preset：

```python
Runtime.sdk()
Runtime.long_running(criteria=["tests stay green"])
Runtime.supervised(criteria=["release 前需要人工审批"])
Runtime.autonomous(max_depth=5, max_iterations=200)
```

## Capability

`Capability` 是用户侧描述 agent 能力来源的语言。工具、Toolset、MCP、skill 都会收敛到同一条受治理的工具路径：

```python
agent = Agent(
    model=Model.openai("gpt-5.1"),
    capabilities=[
        Capability.files(read_only=True),
        Capability.web(),
        Capability.shell(require_approval=True),
        Capability.mcp("github", command="github-mcp", connect=False),
        Capability.skill(
            "repo-review",
            content="# Review\n检查 diff、风险和测试结果。",
            when_to_use="review,diff",
        ),
    ],
)
```

Capability 使用会统一经过 `GovernancePolicy`，包括权限、veto、限流、只读和破坏性操作边界。

## RuntimeSignal

gateway、cron、heartbeat、webhook 和应用回调都应该归一成 `RuntimeSignal`。内核不区分 signal 来源，只接收信号，再由 `AttentionPolicy` 判断 observe、run 或 interrupt。

```python
from loom import RuntimeSignal, SessionConfig

session = agent.session(SessionConfig(id="ops"))

await session.receive(
    RuntimeSignal.create(
        "部署健康检查到期",
        source="cron",
        type="job",
        urgency="normal",
        payload={"job_id": "deployment-health"},
    )
)
```

外部事件用 `SignalAdapter` 在应用边界标准化：

```python
from loom import SignalAdapter

slack = SignalAdapter(
    source="gateway:slack",
    type="message",
    summary=lambda event: event["text"],
    payload=lambda event: {"channel": event["channel"]},
    dedupe_key=lambda event: event["event_id"],
)

await agent.receive(
    {
        "event_id": "evt-support-1",
        "text": "客户询问部署状态",
        "channel": "support",
    },
    adapter=slack,
    session_id="ops",
)
```

Signal 会进入任务仪表盘上下文 `C_working`，作为 pending events 和 active risks 被 runtime 使用。

## Session 和恢复

多轮状态使用 `session()`：

```python
from loom import RunContext, SessionConfig

session = agent.session(SessionConfig(id="demo-user"))

first = await session.run("列出一个好 API 的三个特征")
second = await session.run(
    "把上一条答案压缩成一句话",
    context=RunContext(inputs={"previous_answer": first.output}),
)
```

需要持久化时，接入 session store 和恢复策略：

```python
from loom import Agent, FileSessionStore, Model, Runtime, SessionRestorePolicy

agent = Agent(
    model=Model.openai("gpt-5.1"),
    runtime=Runtime.long_running(
        session_restore=SessionRestorePolicy.window(
            max_transcripts=4,
            max_messages=12,
            max_runtime_items=8,
            max_chars=8000,
        )
    ),
    session_store=FileSessionStore(".loom/sessions.json"),
)
```

`FileSessionStore` 持久化 session metadata、run summaries、transcripts、events、artifacts 和 run context。`SessionRestorePolicy` 决定哪些历史进入下一次 run。

## 内核概念

| 概念 | 含义 |
|---|---|
| `Agent` | 用户侧智能体规格 |
| `Runtime` | 执行机制组合 |
| `Run` / `Session` | 单次执行 / 多轮状态边界 |
| `RuntimeTask` | 结构化任务请求 |
| `RuntimeSignal` | gateway、cron、heartbeat、应用回调等外部输入 |
| `AttentionPolicy` | 判断 signal 如何影响执行 |
| `ContextProtocol` | 上下文分区、渲染、压缩、续写 |
| `ContinuityPolicy` | reset/compact 后如何延续任务 |
| `Harness` | 长任务执行策略 |
| `QualityGate` | 验收标准和 PASS/FAIL |
| `DelegationPolicy` | 子任务和子 agent 派发边界 |
| `Capability` | tools、Toolset、MCP、skill 等能力来源 |
| `GovernancePolicy` | 权限、veto、限流、只读/破坏性检查 |
| `FeedbackPolicy` | 运行反馈和演化数据 |

## 版本策略

- `0.8.0` 是当前 SDK runtime kernel 的公共 API 稳定线
- `0.8.x` 保留旧兼容导出
- `loom.compat.v0` 是显式 legacy namespace
- `0.9.0` 计划移除旧兼容层

## 验证

当前内核文档和示例以这些检查为准：

```bash
poetry run ruff check loom tests examples
poetry run mypy loom
poetry run pytest -q
```

`0.8.0` hardening 阶段最新全量结果：`540 passed`。

## License

Apache 2.0 with Commons Clause. See [LICENSE](LICENSE).
