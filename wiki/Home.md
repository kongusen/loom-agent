# Loom

> Build stateful agents with one public `Agent` API.

Loom's public developer contract is centered on four ideas:

- `AgentConfig` is the only top-level assembly object
- `Agent` is the only top-level execution object
- `SessionConfig` and `RunContext` are the only runtime input objects
- tools, knowledge, policy, memory, heartbeat, runtime, and generation are all stable config objects

## Import Rule

- Import the main application path from `loom`
- Import advanced config objects from `loom.config`
- Import runtime handles and states from `loom.runtime`

In other words, `loom` stays narrow on purpose; extension depth lives in submodules.

## Quick Start

```python
import asyncio
from loom import AgentConfig, ModelRef, create_agent


async def main():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a concise coding assistant.",
        )
    )

    result = await agent.run("Summarize this repository")
    print(result.output)


asyncio.run(main())
```

## Public Shape

```text
AgentConfig
    └── Agent
            ├── run(prompt, context=RunContext(...))
            ├── stream(prompt, context=RunContext(...))
            └── session(SessionConfig(...)) -> Session
                                              └── start/run/stream(...)
```

## Stable Config Surface

- `model`: `ModelRef`
- `generation`: `GenerationConfig`
- `tools`: `list[ToolSpec]`
- `knowledge`: `list[KnowledgeSource]`
- `policy`: `PolicyConfig`
- `memory`: `MemoryConfig`
- `heartbeat`: `HeartbeatConfig`
- `safety_rules`: `list[SafetyRule]`
- `runtime`: `RuntimeConfig`

## Knowledge Flow

Loom exposes a stable knowledge contract even before retrieval is fully wired into the execution engine:

```python
from loom import KnowledgeQuery, RunContext

knowledge = agent.resolve_knowledge(
    KnowledgeQuery(
        text="What are the deployment rules?",
        goal="Summarize deployment policy",
        top_k=3,
    )
)

result = await agent.run(
    "Summarize deployment policy",
    context=RunContext(knowledge=knowledge),
)
```

## Navigation

| I want to... | Start here |
|---|---|
| Get running quickly | [Getting Started](01-getting-started/README.md) |
| Understand the public API | [API Reference](07-api-reference/README.md) |
| See all config objects | [Configuration](07-api-reference/configuration.md) |
| Configure providers and env vars | [Providers](07-api-reference/providers.md) |
| Understand internal architecture | [Architecture](Architecture.md) |
| Learn runtime internals | [Runtime](03-runtime/README.md) |
| Learn orchestration | [Multi-Agent](04-multi-agent/README.md) |
| Learn extension surfaces | [Ecosystem](05-ecosystem/README.md) |
| Copy app-ready patterns | [Cookbook](09-cookbook/README.md) |
| Compare against other frameworks | [Comparison](08-reference/comparison.md) |
| Read the design spec | [hernss-agent-framework.md](hernss-agent-framework.md) |

## Note on Older Runtime Docs

If you still see references to `AgentRuntime`, `SessionHandle`, `TaskHandle`, or `RunHandle`, treat them as historical design material rather than the current public API.
