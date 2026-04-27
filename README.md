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

Loom is an embeddable Agent SDK. It is not a gateway product, cron service, dashboard, or skill marketplace. The kernel gives application developers a stable language for building agent runtimes:

```text
Agent + Runtime + Capability
    -> Run / Session
    -> RuntimeTask / RuntimeSignal
    -> Context / Continuity / Harness / Quality / Governance / Feedback
```

The `0.8.0` line stabilizes this runtime kernel. Legacy 0.x compatibility imports remain available through `0.8.x` and are scheduled for removal in `0.9.0`.

## Install

```bash
pip install loom-agent
export ANTHROPIC_API_KEY=sk-ant-...
```

## Quick Start

```python
import asyncio

from loom import Agent, Capability, Generation, Model, Runtime, tool


@tool(description="Search documentation", read_only=True)
async def search_docs(query: str) -> str:
    return f"Results for: {query}"


async def main():
    agent = Agent(
        model=Model.anthropic("claude-sonnet-4"),
        instructions="You are a concise coding assistant.",
        tools=[search_docs],
        capabilities=[
            Capability.files(read_only=True),
            Capability.web(),
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

- `AgentConfig`, `ModelRef`, `GenerationConfig`, and `create_agent()` remain available through `0.8.x`.
- New docs and examples prefer `Agent`, `Model`, `Generation`, `Runtime`, and `Capability`.
- `loom.compat.v0` is the explicit legacy compatibility surface and is planned for removal in `0.9.0`.

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
    ContextProtocol,
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
    context=ContextProtocol.manager(max_tokens=120000),
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
```

## Capabilities

`Capability` is the user-side language for what an agent can do. Built-in capabilities compile into the same governed tool path as explicit function tools.

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
            content="# Review\nCheck diffs, risks, and test results.",
            when_to_use="review,diff",
        ),
    ],
    runtime=Runtime.long_running(criteria=["tests stay green"]),
)
```

Capability use is checked by `GovernancePolicy`, including permission, veto, rate-limit, read-only, and destructive-operation boundaries.

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

## Hooks And Events

Runtime hooks expose semantic lifecycle points for logging, UI updates, audit trails, or custom feedback:

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

Resolve stable evidence first, then attach it to a run:

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
loom/agent.py              public Agent API and compatibility factory
loom/config.py             public config facade and 0.8 aliases
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
| `ContextProtocol` | Context partitioning, rendering, compaction, renewal |
| `ContinuityPolicy` | Continuation after reset or compaction |
| `Harness` | Long-task execution strategy |
| `QualityGate` | Acceptance criteria and PASS/FAIL evaluation |
| `DelegationPolicy` | Subtask and sub-agent dispatch boundary |
| `Capability` | Tools, Toolsets, MCP, skills, and future ability sources |
| `GovernancePolicy` | Permission, veto, rate limit, read-only/destructive checks |
| `FeedbackPolicy` | Runtime feedback collection and evolution input |

## Version Policy

- `0.8.0` is the public API stabilization line for the SDK runtime kernel.
- `0.8.x` keeps compatibility exports for existing applications.
- `loom.compat.v0` is the explicit legacy compatibility namespace.
- `0.9.0` removes the legacy compatibility surface.

## Validation

The current kernel docs and examples are expected to stay aligned with:

```bash
poetry run ruff check loom tests examples
poetry run mypy loom
poetry run pytest -q
```

Latest full suite during the 0.8.0 hardening pass: `540 passed`.

## License

Apache 2.0 with Commons Clause. See [LICENSE](LICENSE).
