# Loom

> Build stateful agents with a stable `Agent + Model + Runtime` SDK.

Loom's `0.8.0` public contract is centered on the runtime kernel:

```text
Agent
    + Model
    + Runtime
    + capabilities=[Files/Web/Shell/MCP]
    + skills=[Skill]
    -> Run / Session
    -> RuntimeTask / RuntimeSignal
```

Application developers should start from `Agent(...)`, select a `Model`, choose a `Runtime` profile, and declare access through direct user API entries such as `Files`, `Web`, `Shell`, `MCP`, and `Skill`.

## Quick Start

```python
import asyncio

from loom import Agent, Files, Model, Runtime, Web


async def main():
    agent = Agent(
        model=Model.anthropic("claude-sonnet-4"),
        instructions="You are a concise coding assistant.",
        capabilities=[
            Files(read_only=True),
            Web.enabled(),
        ],
        runtime=Runtime.sdk(),
    )

    result = await agent.run("Summarize this repository")
    print(result.output)


asyncio.run(main())
```

## Public Shape

```text
Agent(...)
    ├── run(prompt_or_task, context=RunContext(...))
    ├── stream(prompt_or_task, context=RunContext(...))
    ├── receive(event_or_signal, adapter=SignalAdapter(...))
    └── session(SessionConfig(...)) -> Session
                                      ├── start(...)
                                      ├── run(...)
                                      ├── stream(...)
                                      └── receive(...)
```

## Main Imports

```python
from loom import (
    Agent,
    Files,
    Model,
    Runtime,
    RuntimeSignal,
    RuntimeTask,
    SessionConfig,
    SignalAdapter,
    RunContext,
    tool,
    Web,
)
```

Use `from loom.config import ...` only for advanced configuration internals.

## Runtime Concepts

| Concept | Meaning |
|---|---|
| `Agent` | User-side intelligent agent specification |
| `Runtime` | Execution mechanism composition |
| `Run` / `Session` | Single execution / multi-run state boundary |
| `RuntimeTask` | Structured work request |
| `RuntimeSignal` | External input from gateways, cron, heartbeat, or apps |
| `AttentionPolicy` | Decides whether a signal is observed, queued, or interrupts |
| `ContextPolicy` | Context partitioning, rendering, compaction, renewal |
| `ContinuityPolicy` | Continuation after reset or compaction |
| `Harness` | Long-task execution strategy |
| `QualityGate` | Acceptance criteria and PASS/FAIL evaluation |
| `DelegationPolicy` | Subtask and sub-agent dispatch boundary |
| `Files` / `Web` / `Shell` / `MCP` / `Skill` | User-facing ability and skill declarations |
| `GovernancePolicy` | Permission, veto, rate limit, read-only/destructive checks |
| `FeedbackPolicy` | Runtime feedback collection and evolution input |

## Navigation

| I want to... | Start here |
|---|---|
| Get running quickly | [Getting Started](01-getting-started/README.md) |
| Understand the public API system | [Public API System](07-api-reference/public-api-system.md) |
| Understand user-facing API names | [Public User API Taxonomy](07-api-reference/public-user-api-taxonomy.md) |
| Browse the API reference | [API Reference](07-api-reference/README.md) |
| Configure providers and env vars | [Providers](07-api-reference/providers.md) |
| Understand runtime internals | [Runtime](03-runtime/README.md) |
| Copy app-ready patterns | [Cookbook](09-cookbook/README.md) |
| Understand architecture | [Architecture](Architecture.md) |
| Compare against other frameworks | [Comparison](08-reference/comparison.md) |

## Version Policy

- `0.8.0` is the public API stabilization line for the SDK runtime kernel.
- `0.8.x` now centers the active API on `Agent + Model + Runtime` with direct user-facing ability declarations.
