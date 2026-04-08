<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# Loom

**用统一的 Agent API 构建具备上下文控制、安全边界和扩展能力的状态化 Agent。**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/kongusen/loom-agent)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

[English](README.md) | **中文**

[Wiki 首页](wiki/Home.md) | [PyPI](https://pypi.org/project/loom-agent/)

</div>

---

Loom 现在只有一套公开 API：`Agent`。你用它来定义模型、工具、策略和运行约束，再通过 `run()`、`stream()`、`session()` 构建上层应用。

## 快速开始

```bash
pip install loom-agent
export ANTHROPIC_API_KEY=sk-ant-...
```

```python
import asyncio
from loom import (
    AgentConfig,
    GenerationConfig,
    ModelRef,
    RunContext,
    SessionConfig,
    create_agent,
    tool,
)
from loom.config import (
    MemoryBackend,
    MemoryConfig,
    PolicyConfig,
    PolicyContext,
    RuntimeConfig,
    RuntimeFeatures,
    RuntimeLimits,
    ToolAccessPolicy,
    ToolPolicy,
    ToolRateLimitPolicy,
)


@tool(description="搜索文档", read_only=True)
async def search_docs(query: str) -> str:
    return f"结果: {query}"


async def main():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="你是一个简洁的代码助手",
            tools=[search_docs],
            policy=PolicyConfig(
                tools=ToolPolicy(
                    access=ToolAccessPolicy(
                        allow=["search_docs"],
                        read_only_only=True,
                    ),
                    rate_limits=ToolRateLimitPolicy(max_calls_per_minute=60),
                ),
                context=PolicyContext.named("repo"),
            ),
            memory=MemoryConfig(backend=MemoryBackend.in_memory()),
            generation=GenerationConfig(max_output_tokens=512),
            runtime=RuntimeConfig(
                limits=RuntimeLimits(max_iterations=32),
                features=RuntimeFeatures(enable_safety=True),
            ),
        )
    )

    result = await agent.run("概括这个仓库")
    print(result.output)


asyncio.run(main())
```

导入规则：

- 主应用路径用 `from loom import ...`
- 进阶配置对象用 `from loom.config import ...`
- 直接操作运行态句柄或状态时，用 `from loom.runtime import ...`

## Session

需要多轮状态时，直接使用 `session()`：

```python
session = agent.session(SessionConfig(id="demo-user"))

first = await session.run("列出一个好 API 的三个特征")
second = await session.run(
    "把上一条答案压缩成一句话",
    context=RunContext(inputs={"previous_answer": first.output}),
)
```

## 知识证据

使用 `KnowledgeQuery` 先解析稳定证据，再通过 `RunContext` 附加到单次运行。

```python
from loom import KnowledgeQuery

knowledge = agent.resolve_knowledge(
    KnowledgeQuery(
        text="生产发布规则是什么？",
        goal="概括发布策略",
        top_k=3,
    )
)

result = await agent.run(
    "概括发布策略",
    context=RunContext(knowledge=knowledge),
)
```

## 事件与产物

```python
run = agent.session(SessionConfig(id="stream-demo")).start("分析项目结构")

async for event in run.events():
    print(event.type, event.payload)

result = await run.wait()
artifacts = await run.artifacts()
```

## 扩展配置能力

Loom 保留了可扩展的配置入口，统一通过配置对象挂在 `Agent` API 上：

- `AgentConfig`：单个 agent 的顶层稳定配置对象
- `knowledge`：可复用知识源
- `policy`：工具访问控制、上下文治理、限流
- `memory`：session 记忆配置
- `heartbeat`：监控源、轮询间隔、阈值
- `safety_rules`：危险操作 veto 规则
- `runtime`：执行引擎限制与特性开关

```python
agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions="你是一个发布助手",
        knowledge=[
            KnowledgeSource.inline(
                "deployment-docs",
                [
                    KnowledgeDocument(content="staging 可以自动发布", title="staging"),
                    KnowledgeDocument(content="production 发布需要审批", title="production"),
                ],
                description="内部发布说明",
            )
        ],
        policy=PolicyConfig(
            context=PolicyContext.named("deployment"),
            tools=ToolPolicy(
                access=ToolAccessPolicy(allow=["deploy"]),
                rate_limits=ToolRateLimitPolicy(max_calls_per_minute=10),
            ),
        ),
        memory=MemoryConfig(backend=MemoryBackend.in_memory()),
        heartbeat=HeartbeatConfig(
            interval=5.0,
            interrupt_policy=HeartbeatInterruptPolicy(),
            watch_sources=[
                WatchConfig.filesystem(
                    paths=["./src"],
                    method=FilesystemWatchMethod.HASH,
                ),
                WatchConfig.resource(
                    thresholds=ResourceThresholds(cpu_pct=80.0),
                ),
            ],
        ),
        runtime=RuntimeConfig(
            limits=RuntimeLimits(max_iterations=24, max_context_tokens=120000),
        ),
        safety_rules=[
            SafetyRule.when_argument_equals(
                name="no_prod_deploy",
                reason="禁止生产环境发布",
                tool_name="deploy",
                argument="env",
                value="production",
            )
        ],
    )
)
```

## 模块结构

```text
loom/agent.py        ← 公开 Agent API
loom/runtime/        ← session、run、loop、heartbeat、engine
loom/context/        ← 上下文分区、压缩、续写、dashboard
loom/memory/         ← session / working / semantic / persistent memory
loom/tools/          ← 工具注册、执行、治理
loom/orchestration/  ← 规划与多 agent 协作
loom/safety/         ← 权限、hooks、veto
loom/ecosystem/      ← skill、plugin、MCP 集成
loom/evolution/      ← 自演化策略
loom/providers/      ← Anthropic、OpenAI、Gemini、Qwen、Ollama
```

## Loom 的特点

- 结构化的 Reason → Act → Observe → Δ 执行环
- 上下文压力管理与续写
- 后台 heartbeat 感知
- 工具治理与 veto 安全边界
- Session 级 run / event / artifact
- Skill / Plugin / MCP 扩展能力

## License

Apache 2.0 with Commons Clause. See [LICENSE](LICENSE).
