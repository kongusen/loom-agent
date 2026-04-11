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

Loom 只有一套公开 API：`Agent`。你用它来定义模型、工具、策略和运行约束，再通过 `run()`、`stream()`、`session()` 构建上层应用。

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

---

## Harness — 长任务 Agent 编排

Loom 实现了面向长任务、质量可控的 **Harness 模式**，三个机制协同工作：

### 1 · 上下文重置 + 结构化交接（Context Reset + Handoff）

每当上下文压力 ρ 到达续写阈值，`ContextRenewer` 执行完整的上下文重置，并产出一份 `HandoffArtifact` —— 一个结构化交接文档，用于在下一个 sprint 冷启动时保留完整的情境感知。

```python
from loom.types import HandoffArtifact

# HandoffArtifact 由 ContextManager.renew() 自动生成
# 通过 context_manager.last_handoff 获取
handoff = context_manager.last_handoff

print(handoff.goal)             # 原始目标，永不压缩
print(handoff.sprint)           # 这是第几次续写
print(handoff.progress_summary) # 已完成内容摘要
print(handoff.open_tasks)       # 剩余计划步骤

# 注入到下一个 sprint 的 system prompt
system_msg = handoff.to_system_prompt()
```

与普通上下文压缩不同，`HandoffArtifact` 显式分离了"已完成什么"、"还剩什么"和"永远不变的目标"，确保 Agent 在上下文重置后不会迷失方向。

### 2 · Generator–Evaluator 迭代环（GAN 风格）

`GeneratorEvaluatorLoop` 将生成与评判分离，消除自我表扬偏差（self-praise bias）。Evaluator 先协商出可验证的成功标准（`SprintContract`），再在每轮中评分 Generator 的产出。循环持续到 `PASS` 或耗尽 `max_sprints`。

```python
from loom.orchestration import GeneratorEvaluatorLoop, SprintContract

loop = GeneratorEvaluatorLoop(
    generator=gen_manager,
    evaluator=eval_manager,
    event_bus=bus,  # 可选 — 发布 sprint.passed / sprint.failed 事件
)

results = await loop.run("构建用户认证 REST API", max_sprints=5)

for r in results:
    print(f"Sprint {r.sprint}: {'PASS' if r.passed else 'FAIL'}")
    print(f"  标准: {r.contract.criteria}")
    print(f"  评语: {r.critique}")
```

每个 `SprintResult` 包含：
- `contract` — 本轮前协商的 `SprintContract`（含评判标准）
- `output` — Generator 的输出
- `critique` — Evaluator 的评语（FAIL 时带入下一轮 prompt）
- `passed` — 本轮是否通过

### 3 · Sprint Contract — 协商成功标准

每轮 sprint 开始前，Evaluator 生成明确、可验证的通过条件。这使 Generator 无法钻评估的空子，质量门槛可被检查和审计。

```python
from loom.orchestration import SprintContract

contract = SprintContract(
    sprint=1,
    goal="构建用户认证 REST API",
    criteria=[
        "POST /register 返回 201 和用户 ID",
        "POST /login 成功时返回签名 JWT",
        "错误凭证返回 401 而非 500",
    ],
    eval_tools=["pytest", "httpx"],
)
```

### AgentHarness — 统一入口

`AgentHarness` 将三个机制串联成一次调用：可选的 Planner 将 brief 扩写为详细 spec，随后 Generator–Evaluator 循环迭代精化输出。

```python
from loom.orchestration import AgentHarness, HarnessResult

harness = AgentHarness(
    generator=gen_manager,
    evaluator=eval_manager,   # 省略则退化为单轮模式
    planner=plan_manager,     # 省略则跳过 spec 扩写
    max_sprints=5,
    event_bus=bus,
)

result: HarnessResult = await harness.run(
    "构建一个支持流式输出的 CSV 转 JSON CLI 工具"
)

print(result.spec)      # planner 扩写后的 spec
print(result.output)    # 最终 Generator 输出
print(result.passed)    # Evaluator 是否认可
print(result.sprints)   # 总共跑了几轮
print(result.critique)  # 最后一轮 Evaluator 评语
```

**HarnessResult 字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `spec` | `str` | planner 扩写后的规格，无 planner 时等于原始 brief |
| `output` | `str` | 最终 Generator 输出 |
| `passed` | `bool` | 最后一轮是否通过 Evaluator |
| `sprints` | `int` | 总执行轮数 |
| `critique` | `str` | 最后一轮 Evaluator 评语 |
| `sprint_results` | `list[SprintResult]` | 完整的逐轮历史 |

---

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
loom/agent.py           ← 公开 Agent API
loom/runtime/           ← session、run、loop (Reason→Act→Observe→Δ)、heartbeat
loom/context/           ← 上下文分区、压缩、续写 + HandoffArtifact 生成
loom/memory/            ← session / working / semantic / persistent memory
loom/tools/             ← 工具注册、执行、治理
loom/orchestration/     ← 规划、多 Agent 协作、
│                         GeneratorEvaluatorLoop、AgentHarness、SprintContract
loom/safety/            ← 权限、hooks、veto
loom/ecosystem/         ← skill、plugin、MCP 集成
loom/evolution/         ← 自演化策略
loom/providers/         ← Anthropic、OpenAI、Gemini、Qwen、Ollama
loom/types/             ← 核心类型，含 HandoffArtifact、SprintContract
```

## 能力全景

| 能力类别 | Loom 提供的机制 |
|---------|----------------|
| **执行环** | 结构化 Reason → Act → Observe → Δ，状态自动转换 |
| **上下文管理** | 五分区上下文，压力分级压缩（snip / micro / collapse / auto），ρ ≥ 1.0 强制续写 |
| **结构化交接** | `HandoffArtifact` 跨续写携带目标、进度、待办任务和快照 |
| **质量迭代** | `GeneratorEvaluatorLoop` 以协商好的 `SprintContract` 标准驱动 GAN 风格迭代 |
| **Harness** | `AgentHarness` 将 Planner → Generator ⇌ Evaluator 封装为一次 `await harness.run(brief)` |
| **多 Agent** | `SubAgentManager`、`Coordinator`、`TaskPlanner` 支持并行和串行任务图 |
| **事件总线** | `CoordinationEventBus` 熵门控发布，支持 sprint 事件、主题订阅 |
| **安全边界** | Veto 权限、工具钩子、`safety_rules` |
| **Heartbeat** | 后台文件系统、资源、MF 事件监控，带紧迫度分类 |
| **知识证据** | 证据包、语义检索、跨续写的 citation 追踪 |
| **Session** | 作用域状态、事件流、产物收集 |
| **Provider** | Anthropic、OpenAI、Gemini、Qwen、Ollama，支持共享连接池 |
| **生态扩展** | Skill、Plugin、MCP Server 桥接 |

## 运行时可靠性

- 分层错误体系，便于分类处理失败场景：
  - `ProviderError` → `ProviderUnavailableError` / `RateLimitError`
  - `ToolError` → `ToolNotFoundError` / `ToolPermissionError` / `ToolExecutionError`
  - `ContextError` → `ContextOverflowError`
- Runtime Engine 发出 `tool_result` 事件，evolution 通过 `FeedbackLoop.subscribe_to_engine(...)` 订阅，实现解耦的可靠性反馈。
- OpenAI、Anthropic、Gemini Provider 支持共享客户端池，在高并发下复用 SDK client。

## License

Apache 2.0 with Commons Clause. See [LICENSE](LICENSE).
