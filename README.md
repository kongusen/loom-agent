<div align="center">

<img src="loom.svg" alt="Loom Agent" width="300"/>

# Loom

**A Python Agent SDK for stateful runtime execution, context control, safety boundaries, and extensible capabilities.**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/kongusen/loom-agent)
[![License: Apache 2.0 + Commons Clause](https://img.shields.io/badge/License-Apache_2.0_with_Commons_Clause-red.svg)](LICENSE)

**English** | [中文](README_CN.md)

[Wiki](wiki/Home.md) | [Quick Start](wiki/01-getting-started/README.md) | [PyPI](https://pypi.org/project/loom-agent/) | [Changelog](CHANGELOG.md)

</div>

---

Loom is an embeddable Agent SDK that helps developers build agent platform capabilities similar to [Hermes](https://github.com/nousresearch/hermes-agent) and [OpenClaw](https://github.com/openclaw/openclaw) with less overhead. It is not a gateway product, cron service, dashboard, or skill marketplace. The kernel gives application developers a stable language for building agent runtimes:

```text
Agent + Model + Runtime
    + capabilities=[Files/Web/Shell/MCP]
    + skills=[Skill]
    -> Run / Session
    -> RuntimeTask / RuntimeSignal
    -> Context / Continuity / Harness / Quality / Governance / Feedback
```

The `0.8.x` line centers the public SDK on this runtime kernel and its subsystem shortcuts for orchestration, knowledge, cron, and `MemorySource`.

## Search Keywords

Loom is designed for teams searching for:

- Python agent SDK
- agent runtime framework
- embeddable AI agent framework
- Hermes alternative architecture
- OpenClaw-style agent platform composition

## Loom Vs Hermes / OpenClaw

- Loom is an SDK/runtime kernel, not a full hosted agent product.
- You compose gateway, cron, dashboard, and skill market with adapters.
- This separation helps teams ship custom agent platforms with less lock-in.
- Existing Hermes/OpenClaw-style event flows can be normalized into `RuntimeSignal`.

## FAQ

**Is Loom a full agent platform like Hermes or OpenClaw?**
No. Loom focuses on the runtime kernel and SDK contracts used to build those platform capabilities inside your own product.

**Can I still build gateway, cron, and dashboard experiences with Loom?**
Yes. Loom is designed for that: external systems are adapted into runtime signals and governed capability paths.

**Can I migrate existing Hermes/OpenClaw-style flows?**
Usually yes. Event-driven orchestration can be mapped to `RuntimeSignal`, and policy decisions can be centralized in `Runtime`.

**Who is Loom best for?**
Teams that need an embeddable Python agent SDK with modular orchestration, memory, tools, and safety boundaries.

## Use Cases

- Build a customer support agent platform with your own gateway, routing, and quality controls.
- Build an internal engineering copilot with governed tool use, code search, and memory continuity.
- Build workflow automation agents that react to cron schedules and external runtime signals.
- Build enterprise knowledge agents that combine retrieval, citations, and policy-driven execution.

## Runtime Kernel And Subsystems

The runtime kernel is the shared execution boundary for Loom subsystems. Loom keeps a strict three-layer shape:

```text
Public SDK Layer
    Agent / Session / Run / RuntimeTask / RuntimeSignal

Assembly Layer
    config normalization / provider resolution / tool compilation / ecosystem activation

Runtime Kernel
    AgentEngine / Context / L* loop / governed tools / policies / state
```

Each subsystem is configured from the user-side `Agent(...)` API, normalized into `Runtime`, `Capability`, and source objects, and then executed through the same run/session loop:

```text
Agent(...)
    -> RuntimeConfig + CapabilitySpec + source configs
    -> AgentEngine
    -> Context partitions + RuntimeSignal + governed capability path
    -> Harness / Quality / Continuity / Feedback
```

The user-facing subsystems depend on the kernel in different ways:

| Subsystem | Kernel dependency | Capability provided |
|---|---|---|
| Tool Use | `Capability`, tool registry, `GovernancePolicy` | Exposes Python tools, shell, files, web, MCP, and builtin tools behind permission, read-only, rate-limit, and veto checks. |
| Memory | `ContextPolicy`, memory partition, session restore, `MemorySource` lifecycle | Recalls durable application memory at run start and writes extracted memories at run end, separate from session history. |
| Skills | `Skill`, ecosystem loader, tool registry | Loads task-specific instructions and tools progressively without making every skill part of the base prompt. |
| Harness | `Runtime.harness`, `HarnessRequest`, `HarnessOutcome`, `QualityGate` | Controls how a run is attempted: single pass, generator/evaluator loops, custom candidate generation, human gates, or external workflows. |
| Gateway / Orchestration | `RuntimeSignal`, `AttentionPolicy`, `DelegationPolicy`, coordinator | Normalizes external events and subtask delegation into the same signal and runtime decision path. |
| Knowledge | `KnowledgeSource`, `KnowledgeResolver`, `C_working.knowledge_surface` | Injects run-scoped evidence, active questions, citations, and on-demand retrieval without polluting long-term memory. |
| Cron | `ScheduleConfig`, `ScheduledJob`, `RuntimeSignal(source="cron")` | Turns due scheduled prompts into runtime signals so attention policy decides whether they run, queue, or get ignored. |

At run time these subsystems cooperate through the same loop:

1. The agent receives a `RuntimeTask` or `RuntimeSignal`.
2. Runtime policies decide context shape, attention behavior, allowed capabilities, and harness strategy.
3. Memory and knowledge populate the context partitions before the model call.
4. Tool use, skills, MCP, and delegation execute through the governed capability path.
5. Harness, quality, continuity, and feedback decide whether the run is complete, should continue, or should renew context.
6. Session history and long-term memory are written back through their separate stores.

This keeps integrations modular: new gateways, schedulers, retrievers, memory stores, or skills do not bypass the kernel; they adapt into the kernel contracts.

The governed capability path is intentionally explicit:

```text
Tool request -> Hook -> Permission -> Veto -> Rate limit -> Execute -> Observe
```

`tools` are precise Python function tools. `capabilities` are higher-level declarations such as files, web, shell, MCP, skills, or plugins. Both compile into the same governed tool path.

## Install

```bash
pip install loom-agent
export ANTHROPIC_API_KEY=sk-ant-...
```

## Quick Start

```python
import asyncio

from loom import Agent, Files, Generation, Model, Runtime, Web, tool


@tool(description="Search documentation", read_only=True)
async def search_docs(query: str) -> str:
    return f"Results for: {query}"


async def main():
    agent = Agent(
        model=Model.anthropic("claude-sonnet-4"),
        instructions="You are a concise coding assistant.",
        tools=[search_docs],
        capabilities=[
            Files(read_only=True),
            Web.enabled(),
        ],
        generation=Generation(max_output_tokens=512),
        runtime=Runtime.sdk(),
    )

    result = await agent.run("Summarize this repository")
    print(result.output)


asyncio.run(main())
```

## Public API Shape

Use `from loom import ...` for normal application code:

```python
from loom import (
    Agent,
    Cron,
    Files,
    Gateway,
    Harness,
    HarnessCandidate,
    HarnessOutcome,
    HarnessRequest,
    Instructions,
    Knowledge,
    KnowledgeResolver,
    KnowledgeSource,
    MCP,
    Memory,
    MemoryConfig,
    MemoryExtractor,
    MemoryQuery,
    MemoryRecord,
    MemoryResolver,
    MemorySource,
    MemoryStore,
    Model,
    OrchestrationConfig,
    Runtime,
    RuntimeSignal,
    RuntimeTask,
    ScheduleConfig,
    ScheduledJob,
    SessionConfig,
    Shell,
    SignalAdapter,
    Skill,
    RunContext,
    Web,
    tool,
)
```

The recommended application shape is:

```text
Agent(...)
    -> run(...)
    -> stream(...)
    -> receive(...)
    -> session(SessionConfig(...))
          -> Session
                -> start(...) / run(...) / stream(...) / receive(...)
```

Advanced configuration objects still live behind the same public facade or `loom.config`:

- Application code should start from `Agent(...)`.
- New docs and examples use `Agent`, `Model`, `Generation`, `Runtime`, `Memory`,
  `Knowledge`, `Skill`, `Gateway`, `Cron`, and capability entries such as
  `Files`, `Web`, `Shell`, and `MCP`.
- Lower-level configuration objects remain available through `loom.config`.

## Runtime Language

Strings work for simple runs:

```python
result = await agent.run("List the main risks in this change")
```

Use `RuntimeTask` when the task needs criteria, structured input, or metadata:

```python
from loom import RuntimeTask

result = await agent.run(
    RuntimeTask(
        goal="Refactor the runtime API",
        input={"scope": "agent + runtime kernel"},
        criteria=["preserve public API", "keep tests green"],
    )
)
```

Runtime policies are composed through `Runtime`:

```python
from loom import (
    ContextPolicy,
    ContinuityPolicy,
    DelegationPolicy,
    FeedbackPolicy,
    GovernancePolicy,
    Harness,
    QualityGate,
    Runtime,
    SessionRestorePolicy,
)

runtime = Runtime(
    context=ContextPolicy.manager(max_tokens=120000),
    continuity=ContinuityPolicy.handoff(),
    harness=Harness.single_run(),
    quality=QualityGate.criteria(["tests stay green"]),
    delegation=DelegationPolicy.depth_limited(5),
    governance=GovernancePolicy.default(),
    feedback=FeedbackPolicy.collector(),
    session_restore=SessionRestorePolicy.window(max_chars=12000),
)
```

Or start from conservative presets:

```python
Runtime.sdk()
Runtime.long_running(criteria=["tests stay green"])
Runtime.supervised(criteria=["human approval before release"])
Runtime.autonomous(max_depth=5, max_iterations=200)
Runtime.orchestrated(max_depth=3)
Runtime.scheduled()
```

## Harness

`Harness` is the execution strategy for a run. It is separate from `QualityGate`: the harness decides how work is attempted, while the quality gate defines how an answer is judged.

The default strategy is a single raw runtime loop:

```python
from loom import Harness, Runtime

runtime = Runtime.sdk(harness=Harness.single_run())
```

Custom harnesses can generate multiple possibilities, evaluate them with application logic, and return the selected output:

```python
from loom import Harness, HarnessCandidate, HarnessOutcome, HarnessRequest, Runtime


async def choose_best(request: HarnessRequest) -> HarnessOutcome:
    baseline = await request.run_once()
    candidates = [
        HarnessCandidate(
            id="baseline",
            content=str(baseline["output"]),
            score=0.4,
            rationale="raw runtime output",
        ),
        HarnessCandidate(
            id="expanded",
            content=f"{baseline['output']}\n\nChecked against release criteria.",
            score=0.9,
            rationale="application-specific evaluator preferred this candidate",
        ),
    ]
    return HarnessOutcome(
        output=candidates[1].content,
        candidates=candidates,
        selected_candidate_id="expanded",
    )


runtime = Runtime.long_running(
    criteria=["tests stay green"],
    harness=Harness.custom(choose_best, name="release-review"),
)
```

## Orchestration

Use `orchestration=True` when an agent should be allowed to plan and delegate without manually wiring coordinator internals:

```python
from loom import Agent, Model, OrchestrationConfig

agent = Agent(
    model=Model.openai("gpt-4o"),
    orchestration=True,
)

advanced = Agent(
    model=Model.openai("gpt-4o"),
    orchestration=OrchestrationConfig(max_depth=5, gen_eval=True),
)
```

`orchestration=` is a shortcut for an orchestrated runtime profile with depth-limited delegation and lazy sub-agent wiring. It is mutually exclusive with `runtime=`.

## Capabilities

Use direct capability entries for common ability surfaces. They compile into the
same governed tool path as explicit function tools.

```python
agent = Agent(
    model=Model.openai("gpt-5.1"),
    capabilities=[
        Files(read_only=True),
        Web.enabled(),
        Shell.approval_required(),
        MCP.server("github", command="github-mcp", connect=False),
    ],
    skills=[
        Skill.inline(
            "repo-review",
            content="# Review\nCheck diffs, risks, and test results.",
            when_to_use="review,diff",
        ),
    ],
    runtime=Runtime.long_running(criteria=["tests stay green"]),
)
```

Capability use is checked by `GovernancePolicy`, including permission, veto, rate-limit, read-only, and destructive-operation boundaries.

Use `tools=` when you already have a concrete Python callable to register. Use `capabilities=` when you want to grant a class of abilities that Loom compiles into tools at runtime.

| Input | User intent | Runtime result |
|---|---|---|
| `tools=[fn]` | Add one exact function tool | `ToolSpec -> ToolRegistry` |
| `Files(read_only=True)` | Grant file access | Built-in file toolset |
| `Web.enabled()` | Grant web research | Built-in web toolset |
| `Shell.approval_required()` | Grant shell execution | Shell toolset with approval policy |
| `MCP.server("github")` | Attach external MCP tools | MCP activation + scoped tools |
| `Skill.inline("review", ...)` | Add task-specific behavior | Skill activation + optional tools/context |

`Capability` remains available from `loom.runtime` for advanced architecture-level
declarations, but the documented user path uses the direct domain names above.

## Runtime Signals

Gateway events, cron jobs, heartbeat alerts, webhooks, and application callbacks should all enter the kernel as `RuntimeSignal`. The runtime does not distinguish producers; `AttentionPolicy` decides whether a signal is observed, queued for a run, or treated as an interrupt.

```python
from loom import RuntimeSignal, SessionConfig

session = agent.session(SessionConfig(id="ops"))

await session.receive(
    RuntimeSignal.create(
        "Deployment health check is due",
        source="cron",
        type="job",
        urgency="normal",
        payload={"job_id": "deployment-health"},
    )
)
```

Adapters normalize external event shapes at the application boundary:

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
        "text": "Customer asks for deployment status",
        "channel": "support",
    },
    adapter=slack,
    session_id="ops",
)
```

Signals are projected into the runtime dashboard context (`C_working`) as pending events and active risks.

## Scheduling

Declare scheduled prompts on the agent, then explicitly start and stop the in-process scheduler:

```python
from loom import Agent, Model, ScheduleConfig

agent = Agent(model=Model.openai("gpt-4o"))

agent.every(id="ci", prompt="Check CI status", minutes=30)
agent.once("2026-04-29T09:00:00", id="daily", prompt="Summarize inbox")
agent.schedule(
    "custom",
    prompt="Run scheduled maintenance",
    every=ScheduleConfig.interval(hours=1),
)

agent.start_scheduler()
# ...
agent.stop_scheduler()
```

Scheduled jobs are converted to `RuntimeSignal(source="cron", type="scheduled_job")` before execution. The runtime attention policy decides whether a due job should run, be observed, or be ignored. `Agent(...)` never starts background work by itself.

## Sessions And Restore

Use `session()` when the application needs continuity across runs:

```python
from loom import RunContext, SessionConfig

session = agent.session(SessionConfig(id="demo-user"))

first = await session.run("List three qualities of a good API")
second = await session.run(
    "Summarize the previous answer in one sentence",
    context=RunContext(inputs={"previous_answer": first.output}),
)
```

For durable state, attach a session store and choose a restore policy:

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

`FileSessionStore` persists session metadata, run summaries, transcripts, events, artifacts, and run context. `SessionRestorePolicy` controls what enters the next run.

## Memory

Memory has two separate responsibilities:

- `SessionStore` + `SessionRestorePolicy` persist and restore runtime history.
- `MemorySource` retrieves and updates long-term application memory.

For new integrations, prefer `MemorySource`, `MemoryResolver`, `MemoryExtractor`, and `MemoryStore`:

```python
from loom import (
    Agent,
    MemoryConfig,
    MemoryExtractor,
    MemoryQuery,
    MemoryRecord,
    MemorySource,
    MemoryStore,
    Model,
)


class VectorMemoryStore(MemoryStore):
    def search(self, query: MemoryQuery) -> list[MemoryRecord]:
        hits = vector_db.search(
            query.text,
            top_k=query.top_k,
            filter={"session_id": query.session_id},
        )
        return [
            MemoryRecord(
                key=hit.id,
                content=hit.text,
                score=hit.score,
                metadata=hit.metadata,
            )
            for hit in hits
        ]

    def upsert(self, record: MemoryRecord, query: MemoryQuery | None = None) -> None:
        vector_db.upsert(
            id=record.key or None,
            text=record.content,
            metadata={**record.metadata, "session_id": query.session_id if query else None},
        )


memory = MemorySource.long_term(
    "project",
    store=VectorMemoryStore(),
    extractor=MemoryExtractor.callable(
        lambda user, assistant, session_id=None: [
            MemoryRecord(
                content=f"{user} -> {assistant}",
                metadata={"session_id": session_id},
            )
        ]
    ),
    instructions="Use durable project memory when relevant.",
)

agent = Agent(
    model=Model.openai("gpt-4o"),
    memory=MemoryConfig(sources=[memory]),
)
```

At run start, each `MemorySource` retrieves records and injects them into the memory partition. At run end, its extractor can produce records and write them through the store. `MemorySource` is the single public extension point for durable memory integrations.

## Hooks And Events

Runtime hooks expose semantic lifecycle points for logging, UI updates, audit trails, or custom feedback.

> **Hooks vs Feedback** — hooks are the *control plane*: `before_*` hooks can
> `DENY` or `ASK` to block/confirm an action, while `after_*`/`on_*` hooks
> observe without intervention.  `FeedbackPolicy` is the *data plane*: it
> records execution events for metrics, evolution, and audit but never alters
> the runtime flow.  Use hooks when you need to *influence* behaviour; use
> feedback when you need to *observe* it.

```python
agent.on("before_run", lambda **event: print("starting", event["run_id"]))
agent.on("before_llm", lambda **event: print("llm", event["iteration"]))
agent.on("before_tool", lambda **event: print("tool", event["tool_name"]))
agent.on("after_tool", lambda **event: print(event["tool_name"], event["success"]))
agent.on("on_context_compact", lambda **event: print("compact", event["strategy"]))
agent.on("after_run", lambda **event: print("finished", event["result"]["status"]))
```

For run event streams:

```python
run = agent.session(SessionConfig(id="stream-demo")).start("Inspect the project layout")

async for event in run.events():
    print(event.type, event.payload)

result = await run.wait()
artifacts = await run.artifacts()
```

## Knowledge

Declare knowledge sources on the agent and they are automatically resolved and injected at run time:

```python
from loom import Agent, KnowledgeSource, Model

agent = Agent(
    model=Model.anthropic("claude-sonnet-4"),
    knowledge=[
        KnowledgeSource.inline("docs", ["Deployment must use release controls."]),
        KnowledgeSource.from_directory("repo-docs", "./docs", glob="**/*.md"),
    ],
)
result = await agent.run("Summarize deployment policy")
```

For custom retrieval, provide a `KnowledgeResolver`:

```python
from loom import (
    KnowledgeEvidence,
    KnowledgeEvidenceItem,
    KnowledgeQuery,
    KnowledgeResolver,
    KnowledgeSource,
)


def retrieve_docs(query: KnowledgeQuery) -> KnowledgeEvidence:
    hits = search_index.search(query.text, top_k=query.top_k)
    return KnowledgeEvidence(
        query=query,
        items=[
            KnowledgeEvidenceItem(
                source_name="search",
                title=hit.title,
                content=hit.text,
                uri=hit.url,
                score=hit.score,
            )
            for hit in hits
        ],
    )


source = KnowledgeSource.dynamic(
    "search",
    KnowledgeResolver.callable(retrieve_docs),
)
```

For advanced one-off use cases, resolve knowledge manually and pass it via `RunContext`:

```python
from loom import KnowledgeQuery, RunContext

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

## Architecture

```text
loom/agent.py              public Agent API
loom/config.py             public advanced config facade
loom/runtime/              runs, sessions, engine, signals, policies
loom/context/              partitions, compression, renewal, handoff
loom/tools/                tool registry, execution, governance path
loom/ecosystem/            skills, plugins, MCP bridge
loom/providers/            request-native provider adapters
loom/memory/               session, working, semantic, persistent memory
loom/safety/               veto authority, permission guards, safety rules
loom/orchestration/        planner, coordinator, gen/eval adapters
```

The kernel concepts are:

| Concept | Role |
|---|---|
| `Agent` | User-side intelligent agent specification |
| `Runtime` | Execution mechanism composition |
| `Run` / `Session` | Single execution / multi-run state boundary |
| `RuntimeTask` | Structured work request |
| `RuntimeSignal` | External input from gateways, cron, heartbeat, apps |
| `AttentionPolicy` | Decides how signals affect execution |
| `ContextPolicy` | Context partitioning, rendering, compaction, renewal |
| `ContinuityPolicy` | Continuation after reset or compaction |
| `Harness` | Long-task execution strategy |
| `QualityGate` | Acceptance criteria and PASS/FAIL evaluation |
| `DelegationPolicy` | Subtask and sub-agent dispatch boundary |
| `Files` / `Web` / `Shell` / `MCP` / `Skill` | User-facing ability and skill declarations |
| `GovernancePolicy` | Permission, veto, rate limit, read-only/destructive checks |
| `FeedbackPolicy` | Runtime feedback collection and evolution input |

## Version Policy

- `0.8.0` is the public API stabilization line for the SDK runtime kernel.
- `0.8.1` completes the seven subsystem integration layer: Tool Use, Memory, Skills, Harness, Gateway/Orchestration, Knowledge, and Cron.
- `0.8.2` separates the intuitive public user API from runtime mechanism APIs and removes the old compat layer.
- Public docs and examples stay centered on `Agent + Model + Runtime` with direct user-facing ability declarations.

## Validation

The current kernel docs and examples are expected to stay aligned with:

```bash
poetry run ruff check loom tests examples
poetry run mypy loom
poetry run pytest -q
```

Latest full suite during the 0.8.2 API convergence pass: `588 passed`.

## License

Apache 2.0 with Commons Clause. See [LICENSE](LICENSE).
