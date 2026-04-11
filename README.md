<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# Loom

**Build stateful agents with context control, safety boundaries, and extensible runtime capabilities.**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/kongusen/loom-agent)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

**English** | [中文](README_CN.md)

[Wiki](wiki/Home.md) | [Quick Start](wiki/01-getting-started/README.md) | [PyPI](https://pypi.org/project/loom-agent/)

</div>

---

Loom exposes one public API centered on `Agent`. You configure an agent once, then use `run()`, `stream()`, and `session()` to build applications with multi-step execution, tools, heartbeat monitoring, safety rules, and session-scoped state.

## Quick Start

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


@tool(description="Search documentation", read_only=True)
async def search_docs(query: str) -> str:
    return f"Results for: {query}"


async def main():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a concise coding assistant",
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

    result = await agent.run("Summarize this repository")
    print(result.output)


asyncio.run(main())
```

Import rule:

- Use `from loom import ...` for the primary application path.
- Use `from loom.config import ...` for advanced configuration objects.
- Use `from loom.runtime import ...` for runtime states, runs, and sessions when you need them directly.

## Sessions

Use `session()` when the application needs continuity across runs.

```python
session = agent.session(SessionConfig(id="demo-user"))

first = await session.run("List three qualities of a good API")
second = await session.run(
    "Summarize the previous answer in one sentence",
    context=RunContext(inputs={"previous_answer": first.output}),
)

print(second.output)
```

## Knowledge Evidence

Use `KnowledgeQuery` to resolve stable evidence, then attach it to one run through `RunContext`.

```python
from loom import KnowledgeQuery

knowledge = agent.resolve_knowledge(
    KnowledgeQuery(
        text="What are the production deployment rules?",
        goal="Summarize deployment policy",
        top_k=3,
    )
)

result = await agent.run(
    "Summarize deployment policy",
    context=RunContext(knowledge=knowledge),
)
```

## Streaming, Events, and Artifacts

```python
run = agent.session(SessionConfig(id="stream-demo")).start("Inspect the project layout")

async for event in run.events():
    print(event.type, event.payload)

result = await run.wait()
artifacts = await run.artifacts()
```

---

## Harness — Long-Running Agent Orchestration

Loom implements the **Harness pattern** for long-running, quality-controlled agent tasks. Three mechanisms work together:

### 1 · Context Reset with Structured Handoff

Every time the context pressure (ρ) reaches the renewal threshold, `ContextRenewer` performs a full context reset and produces a `HandoffArtifact` — a structured document that cold-starts the next sprint with full situational awareness.

```python
from loom.types import HandoffArtifact

# HandoffArtifact is produced automatically by ContextManager.renew()
# and is accessible via context_manager.last_handoff
handoff = context_manager.last_handoff

print(handoff.goal)            # original goal, never compressed
print(handoff.sprint)          # which renewal this is
print(handoff.progress_summary)
print(handoff.open_tasks)      # remaining plan steps carried forward

# Inject into the next sprint's system prompt
system_msg = handoff.to_system_prompt()
```

Unlike plain context compression, `HandoffArtifact` explicitly separates what was accomplished, what still needs to be done, and the goal that never changes — so the agent never loses its bearings after a context reset.

### 2 · Generator–Evaluator Loop (GAN-style)

`GeneratorEvaluatorLoop` separates generation from judgment to eliminate self-praise bias. The Evaluator first negotiates verifiable success criteria (`SprintContract`), then scores the Generator's output in each round. The loop continues until `PASS` or `max_sprints` is exhausted.

```python
from loom.orchestration import GeneratorEvaluatorLoop, SprintContract

loop = GeneratorEvaluatorLoop(
    generator=gen_manager,
    evaluator=eval_manager,
    event_bus=bus,          # optional — publishes sprint.passed / sprint.failed
)

results = await loop.run("Build a REST API for user authentication", max_sprints=5)

for r in results:
    print(f"Sprint {r.sprint}: {'PASS' if r.passed else 'FAIL'}")
    print(f"  Criteria: {r.contract.criteria}")
    print(f"  Critique: {r.critique}")
```

Each `SprintResult` carries:
- `contract` — the `SprintContract` with criteria agreed before this sprint
- `output` — what the Generator produced
- `critique` — the Evaluator's judgment (fed into the next sprint's prompt on FAIL)
- `passed` — whether this sprint cleared the bar

### 3 · Sprint Contract — Negotiated Success Criteria

Before each sprint, the Evaluator generates explicit, verifiable criteria. This prevents the Generator from gaming the evaluation, and makes quality gates inspectable and auditable.

```python
from loom.orchestration import SprintContract

contract = SprintContract(
    sprint=1,
    goal="Build a REST API for user auth",
    criteria=[
        "POST /register returns 201 with a user ID",
        "POST /login returns a signed JWT on success",
        "Invalid credentials return 401, not 500",
    ],
    eval_tools=["pytest", "httpx"],
)
```

### AgentHarness — One-Stop Entry Point

`AgentHarness` wires all three mechanisms into a single call: an optional Planner expands the brief into a spec, then the Generator–Evaluator loop refines the output.

```python
from loom.orchestration import AgentHarness, HarnessResult

harness = AgentHarness(
    generator=gen_manager,
    evaluator=eval_manager,   # omit for single-shot mode
    planner=plan_manager,     # omit to skip spec expansion
    max_sprints=5,
    event_bus=bus,
)

result: HarnessResult = await harness.run(
    "Build a CLI tool that converts CSV to JSON with streaming support"
)

print(result.spec)          # planner-expanded specification
print(result.output)        # final generator output
print(result.passed)        # did the evaluator approve?
print(result.sprints)       # how many rounds were needed
print(result.critique)      # last evaluator feedback
```

**HarnessResult fields:**

| Field | Type | Description |
|-------|------|-------------|
| `spec` | `str` | Planner-expanded brief, or original brief if no planner |
| `output` | `str` | Final Generator output |
| `passed` | `bool` | True if Evaluator approved the last sprint |
| `sprints` | `int` | Total sprints executed |
| `critique` | `str` | Last Evaluator feedback |
| `sprint_results` | `list[SprintResult]` | Full per-sprint history |

---

## Extensible Configuration

Loom keeps configuration extensible through stable config objects on the public API:

- `AgentConfig`: top-level stable entry for one agent
- `knowledge`: reusable knowledge sources for evidence and retrieval
- `policy`: tool access controls, context-specific governance, rate limits
- `memory`: session-level memory options
- `heartbeat`: watch sources, interval, entropy threshold
- `safety_rules`: veto rules for dangerous operations
- `runtime`: engine-level limits and features

Example:

```python
agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions="You are a deployment assistant",
        knowledge=[
            KnowledgeSource.inline(
                "deployment-docs",
                [
                    KnowledgeDocument(content="Staging deploys are automatic.", title="Staging"),
                    KnowledgeDocument(content="Production deploys require approval.", title="Production"),
                ],
                description="Internal deployment notes",
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
                reason="Production deployment is blocked",
                tool_name="deploy",
                argument="env",
                value="production",
            )
        ],
    )
)
```

## Architecture

```text
loom/agent.py           ← Public agent API
loom/runtime/           ← Sessions, runs, loop (Reason→Act→Observe→Δ), heartbeat
loom/context/           ← Context partitions, compression, renewal + HandoffArtifact
loom/memory/            ← Session, working, semantic, persistent memory
loom/tools/             ← Tool registry, executor, governance pipeline
loom/orchestration/     ← Task planning, multi-agent coordination,
│                         GeneratorEvaluatorLoop, AgentHarness, SprintContract
loom/safety/            ← Permissions, hooks, veto authority
loom/ecosystem/         ← Skills, plugins, MCP bridge, activation
loom/evolution/         ← Self-improvement strategies
loom/providers/         ← Anthropic, OpenAI, Gemini, Qwen, Ollama
loom/types/             ← Core types incl. HandoffArtifact, SprintContract
```

## Capabilities

| Category | What Loom provides |
|----------|--------------------|
| **Execution loop** | Structured Reason → Act → Observe → Δ with automatic state transitions |
| **Context management** | Five-partition context, pressure-based compression (snip / micro / collapse / auto), forced renewal at ρ ≥ 1.0 |
| **Structured handoff** | `HandoffArtifact` carries goal, progress, open tasks, and context snapshot across context resets |
| **Quality iteration** | `GeneratorEvaluatorLoop` runs GAN-style sprints with negotiated `SprintContract` criteria |
| **Harness** | `AgentHarness` wires Planner → Generator ⇌ Evaluator into one `await harness.run(brief)` call |
| **Multi-agent** | `SubAgentManager`, `Coordinator`, `TaskPlanner` for parallel and sequential task graphs |
| **Event bus** | `CoordinationEventBus` with entropy-gated publish, sprint events, topic subscriptions |
| **Safety** | Veto authority, permission guards, pre/post tool hooks, `safety_rules` |
| **Heartbeat** | Background filesystem, resource, and MF-events monitoring with urgency classification |
| **Knowledge** | Evidence packs, semantic retrieval, citation tracking across context resets |
| **Sessions** | Scoped state, streaming events, artifact collection |
| **Providers** | Anthropic, OpenAI, Gemini, Qwen, Ollama with shared client pooling |
| **Ecosystem** | Skills, plugins, MCP server bridge |

## Runtime Reliability

- Hierarchical errors make failures easier to classify and handle:
  - `ProviderError` → `ProviderUnavailableError` / `RateLimitError`
  - `ToolError` → `ToolNotFoundError` / `ToolPermissionError` / `ToolExecutionError`
  - `ContextError` → `ContextOverflowError`
- Runtime engine emits `tool_result` events; evolution feedback subscribes via `FeedbackLoop.subscribe_to_engine(...)` for decoupled reliability tracking.
- OpenAI, Anthropic, and Gemini providers support shared client pooling to reuse SDK clients under concurrent load.

## License

Apache 2.0 with Commons Clause. See [LICENSE](LICENSE).
