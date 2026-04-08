# API Reference

Loom exposes one public API.

Its stable application-facing path is:

```text
AgentConfig -> Agent -> Session -> Run
```

If you are integrating Loom for the first time, focus on these four steps:

1. Assemble an agent with `AgentConfig`
2. Construct an `Agent` with `create_agent()`
3. Use `agent.run()` for simple single-run flows
4. Use `agent.session()` when you need stateful multi-run workflows

## Design Principles

- There is only one public agent API. There is no separate "Simple API" or "Advanced API".
- `policy`, `memory`, `heartbeat`, and `runtime` are stable config objects, not loose dictionaries.
- `loom` stays intentionally narrow.
- Deeper configuration lives in `loom.config`.
- Runtime objects live in `loom.runtime`.
- Older names such as `loom.api`, `AgentRuntime`, `SessionHandle`, `TaskHandle`, and `RunHandle` are no longer public usage guidance.

## 30-Second Start

```python
import asyncio

from loom import AgentConfig, ModelRef, create_agent


async def main():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.openai("gpt-4.1-mini"),
            instructions="You are a concise, reliable technical assistant.",
        )
    )

    result = await agent.run("Explain Loom's API design in three sentences.")
    print(result.output)


asyncio.run(main())
```

## Import Rules

Most application code should import from only three layers:

```python
from loom import AgentConfig, ModelRef, RunContext, SessionConfig, create_agent, tool
from loom.config import GenerationConfig, MemoryConfig, PolicyConfig, RuntimeConfig
from loom.runtime import Run, RunEvent, RunResult, RunState, Session
```

Import layering:

- `loom`: primary application-facing API
- `loom.config`: stable configuration vocabulary
- `loom.runtime`: sessions, runs, events, results, and states

## Common Development Paths

### 1. Single Run

```python
result = await agent.run("Summarize this request.")
print(result.output)
```

Good for:

- chat endpoints
- one-off analysis
- text generation
- extraction and classification

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

Good for:

- multi-turn assistants
- step-by-step workflows
- flows that need run history

### 3. Tool Calling

```python
from loom import AgentConfig, ModelRef, create_agent, tool


@tool(description="Get the weather for a city", read_only=True)
def get_weather(city: str) -> str:
    return f"{city}: 22C, sunny"


agent = create_agent(
    AgentConfig(
        model=ModelRef.openai("gpt-4.1-mini"),
        instructions="You are a weather assistant.",
        tools=[get_weather],
    )
)
```

### 4. Explicit Knowledge Context

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

This is the clearest and most stable knowledge usage pattern today.

## Recommended Reading Order

- [Agent API](agent-api.md): `Agent`, `Session`, `Run`, `RunContext`, `SessionConfig`
- [Configuration](configuration.md): `AgentConfig` and all stable config objects
- [Providers](providers.md): provider selection, environment variables, base URLs, and fallback behavior

## Quick Map

| Goal | Start Here |
|---|---|
| Get an agent running fast | [Agent API](agent-api.md) |
| Configure model, tools, policy, memory, heartbeat | [Configuration](configuration.md) |
| Connect to OpenAI-compatible or other providers | [Providers](providers.md) |
| Browse runnable examples | [examples directory](https://github.com/kongusen/loom-agent/tree/main/examples) |

## Public Contract

- `AgentConfig.model` must be a `ModelRef`
- `generation`, `policy`, `memory`, `heartbeat`, and `runtime` must be config objects
- `tools` must contain `ToolSpec`
- `knowledge` must contain `KnowledgeSource`
- `safety_rules` must contain `SafetyRule`

Loom no longer supports a "pass in a loose dict and infer the rest" API style.

## Example Index

- [00_agent_overview.py](https://github.com/kongusen/loom-agent/blob/main/examples/00_agent_overview.py): public API overview
- [01_hello_agent.py](https://github.com/kongusen/loom-agent/blob/main/examples/01_hello_agent.py): minimal single-run flow
- [02_provider_config.py](https://github.com/kongusen/loom-agent/blob/main/examples/02_provider_config.py): providers and environment variables
- [03_events_and_artifacts.py](https://github.com/kongusen/loom-agent/blob/main/examples/03_events_and_artifacts.py): run events and artifacts
- [04_multi_task_session.py](https://github.com/kongusen/loom-agent/blob/main/examples/04_multi_task_session.py): multi-run sessions
- [12_heartbeat_and_safety.py](https://github.com/kongusen/loom-agent/blob/main/examples/12_heartbeat_and_safety.py): heartbeat and safety rules
