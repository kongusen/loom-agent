# API Reference

Loom exposes one public SDK path for application developers:

```text
Agent + Model + Runtime
    + capabilities=[Files/Web/Shell/MCP]
    + skills=[Skill]
    -> Run / Session
    -> RuntimeTask / RuntimeSignal
```

If you are integrating Loom for the first time, focus on these steps:

1. Assemble an `Agent(...)`
2. Select a model with `Model.openai(...)`, `Model.anthropic(...)`, or another provider constructor
3. Choose a `Runtime` profile
4. Declare abilities with `Files`, `Web`, `Shell`, `MCP`, and `Skill`
5. Use `agent.run()` for simple flows
6. Use `agent.session()` when you need stateful multi-run workflows
7. Use `agent.receive()` or `session.receive()` for external signal input

## Design Principles

- There is one main application API, centered on `Agent`.
- Runtime behavior is composed through policy objects, not through product-specific gateway or cron classes.
- Gateway, cron, heartbeat, webhook, and app events normalize into `RuntimeSignal`.
- Tools, file/web/shell/MCP abilities, and skills normalize into runtime capability specs.
- Governance is applied at the runtime boundary before tools execute.
- Advanced configuration remains under `loom.config`.

## 30-Second Start

```python
import asyncio

from loom import Agent, Model, Runtime


async def main():
    agent = Agent(
        model=Model.openai("gpt-5.1"),
        instructions="You are a concise, reliable technical assistant.",
        runtime=Runtime.sdk(),
    )

    result = await agent.run("Explain Loom's API design in three sentences.")
    print(result.output)


asyncio.run(main())
```

## Import Rules

Most application code should import from `loom`:

```python
from loom import (
    Agent,
    Capability,
    Model,
    Runtime,
    RunContext,
    RuntimeSignal,
    RuntimeTask,
    SessionConfig,
    SignalAdapter,
    tool,
)
```

Use `loom.config` for advanced config internals. Use `loom.runtime` when directly testing or extending runtime mechanism contracts.

## Common Development Paths

### 1. Single Run

```python
result = await agent.run("Summarize this request.")
print(result.output)
```

Good for chat endpoints, one-off analysis, generation, extraction, and classification.

### 2. Multi-Run Session

```python
from loom import RunContext, SessionConfig

session = agent.session(SessionConfig(id="demo"))

first = await session.run("List three principles of good API design.")
second = await session.run(
    "Compress the previous answer into one sentence.",
    context=RunContext(inputs={"previous_answer": first.output}),
)
```

Good for multi-turn assistants and workflows that need run history.

### 3. Capabilities

```python
from loom import Agent, Files, Model, Runtime, Shell, Web

agent = Agent(
    model=Model.openai("gpt-5.1"),
    capabilities=[
        Files(read_only=True),
        Web.enabled(),
        Shell.approval_required(),
    ],
    runtime=Runtime.long_running(criteria=["tests stay green"]),
)
```

Good for governed file, web, shell, MCP, and skill access.

### 4. Function Tools

```python
from loom import Agent, Model, tool


@tool(description="Get the weather for a city", read_only=True)
def get_weather(city: str) -> str:
    return f"{city}: 22C, sunny"


agent = Agent(
    model=Model.openai("gpt-5.1"),
    instructions="You are a weather assistant.",
    tools=[get_weather],
)
```

### 5. Runtime Signals

```python
from loom import RuntimeSignal, SessionConfig

session = agent.session(SessionConfig(id="ops"))

await session.receive(
    RuntimeSignal.create(
        "CPU usage exceeded 90%",
        source="heartbeat",
        type="alert",
        urgency="high",
        payload={"host": "api-1"},
    )
)
```

### 6. Explicit Knowledge Context

```python
from loom import KnowledgeQuery, RunContext

knowledge = agent.resolve_knowledge(
    KnowledgeQuery(
        text="How does Loom runtime work?",
        goal="Summarize the Loom runtime design",
        top_k=3,
    )
)

result = await agent.run(
    "Explain the Loom runtime based on the provided knowledge.",
    context=RunContext(knowledge=knowledge),
)
```

## Recommended Reading Order

- [Public API System](public-api-system.md): active API shape, object boundaries, and maintenance rules
- [Public User API Taxonomy](public-user-api-taxonomy.md): user-facing naming categories and supported constructor shape
- [Agent API](agent-api.md): `Agent`, `Session`, `Run`, `RunContext`, `SessionConfig`
- [Providers](providers.md): provider selection, environment variables, base URLs, fallback behavior
- [Configuration](configuration.md): advanced config objects

## Quick Map

| Goal | Start Here |
|---|---|
| Understand the active API system | [Public API System](public-api-system.md) |
| Understand user-facing API names | [Public User API Taxonomy](public-user-api-taxonomy.md) |
| Get an agent running fast | [Agent API](agent-api.md) |
| Connect to OpenAI-compatible or other providers | [Providers](providers.md) |
| Browse runnable examples | [examples directory](https://github.com/kongusen/loom-agent/tree/main/examples) |
| Use advanced config objects | [Configuration](configuration.md) |

## Public Contract

- `Agent.model` should be a `Model`
- `Agent.runtime` should be a `Runtime` profile or custom runtime config
- `Agent.capabilities` should contain `Capability` declarations
- `Agent.tools` should contain explicit `ToolSpec` or `@tool` functions
- `RuntimeSignal` is the normalized external input contract
- `RunContext` is the run-scoped structured input contract

## Example Index

- [00_agent_overview.py](https://github.com/kongusen/loom-agent/blob/main/examples/00_agent_overview.py): public API overview
- [01_hello_agent.py](https://github.com/kongusen/loom-agent/blob/main/examples/01_hello_agent.py): minimal single-run flow
- [02_provider_config.py](https://github.com/kongusen/loom-agent/blob/main/examples/02_provider_config.py): providers and environment variables
- [03_events_and_artifacts.py](https://github.com/kongusen/loom-agent/blob/main/examples/03_events_and_artifacts.py): run events and artifacts
- [04_multi_task_session.py](https://github.com/kongusen/loom-agent/blob/main/examples/04_multi_task_session.py): multi-run sessions
- [12_heartbeat_and_safety.py](https://github.com/kongusen/loom-agent/blob/main/examples/12_heartbeat_and_safety.py): heartbeat and safety rules
- [16_signal_adapters.py](https://github.com/kongusen/loom-agent/blob/main/examples/16_signal_adapters.py): gateway/cron/heartbeat-style adapters
