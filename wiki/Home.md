# Loom

> Build stateful agents with a stable `Agent + Runtime + Capability` SDK.

Loom's `0.8.0` public contract is centered on the runtime kernel:

```text
Agent
    + Runtime
    + Capability
    -> Run / Session
    -> RuntimeTask / RuntimeSignal
```

Application developers should start from `Agent(...)`, select a `Model`, choose a `Runtime` profile, and declare tool/MCP/skill access through `Capability`.

## Quick Start

```python
import asyncio

from loom import Agent, Capability, Model, Runtime


async def main():
    agent = Agent(
        model=Model.anthropic("claude-sonnet-4"),
        instructions="You are a concise coding assistant.",
        capabilities=[
            Capability.files(read_only=True),
            Capability.web(),
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

Use `from loom.config import ...` only for advanced configuration internals. `AgentConfig`, `ModelRef`, `GenerationConfig`, and `create_agent()` remain available through `0.8.x`, but they are no longer the recommended starting point for new applications.

## Runtime Concepts

| Concept | Meaning |
|---|---|
| `Agent` | User-side intelligent agent specification |
| `Runtime` | Execution mechanism composition |
| `Run` / `Session` | Single execution / multi-run state boundary |
| `RuntimeTask` | Structured work request |
| `RuntimeSignal` | External input from gateways, cron, heartbeat, or apps |
| `AttentionPolicy` | Decides whether a signal is observed, queued, or interrupts |
| `ContextProtocol` | Context partitioning, rendering, compaction, renewal |
| `ContinuityPolicy` | Continuation after reset or compaction |
| `Harness` | Long-task execution strategy |
| `QualityGate` | Acceptance criteria and PASS/FAIL evaluation |
| `DelegationPolicy` | Subtask and sub-agent dispatch boundary |
| `Capability` | Tools, Toolsets, MCP, skills, and future ability sources |
| `GovernancePolicy` | Permission, veto, rate limit, read-only/destructive checks |
| `FeedbackPolicy` | Runtime feedback collection and evolution input |

## Navigation

| I want to... | Start here |
|---|---|
| Get running quickly | [Getting Started](01-getting-started/README.md) |
| Understand the public API | [API Reference](07-api-reference/README.md) |
| Configure providers and env vars | [Providers](07-api-reference/providers.md) |
| Understand runtime internals | [Runtime](03-runtime/README.md) |
| Copy app-ready patterns | [Cookbook](09-cookbook/README.md) |
| Understand architecture | [Architecture](Architecture.md) |
| Compare against other frameworks | [Comparison](08-reference/comparison.md) |
| Read historical design material | [hernss-agent-framework.md](hernss-agent-framework.md) |

## Version Policy

- `0.8.0` is the public API stabilization line for the SDK runtime kernel.
- `0.8.x` keeps compatibility exports for existing applications.
- `loom.compat.v0` is the explicit legacy compatibility namespace.
- `0.9.0` removes the legacy compatibility surface.

## Historical Note

If you see `AgentRuntime`, `SessionHandle`, `TaskHandle`, `RunHandle`, or `create_agent(AgentConfig(...))` presented as the main path, treat that page as older material. The supported `0.8.x` application path is `Agent + Model + Runtime/Capability + Session/RunContext`.
