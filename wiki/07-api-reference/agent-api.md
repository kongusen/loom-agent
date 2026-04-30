# Agent API

This page describes Loom's core application-facing runtime objects.

The public `0.8.x` path is:

```text
Agent(...)
    -> Run / Session
```

Lower-level configuration objects remain available from `loom.config` for advanced use, but application code should start from `Agent(...)`.

## 1. `Agent`

`Agent` is the top-level execution object.

```python
from loom import Agent, Files, Model, Runtime, Web

agent = Agent(
    model=Model.openai("gpt-5.1"),
    instructions="You are a code assistant.",
    capabilities=[
        Files(read_only=True),
        Web.enabled(),
    ],
    runtime=Runtime.sdk(),
)
```

Common constructor fields:

| Field | Description |
|---|---|
| `model` | Provider-backed model reference, usually `Model.openai(...)`, `Model.anthropic(...)`, etc. |
| `instructions` | Stable behavior instructions |
| `tools` | Explicit Python tools declared with `@tool` |
| `capabilities` | Files, web, shell, MCP, or custom capability sources |
| `skills` | Task-specific skill declarations |
| `generation` | Model generation controls |
| `runtime` | Runtime profile or custom policy composition |
| `session_store` | Optional durable session persistence |

## 2. Main Methods

```python
await agent.run(prompt_or_task, context=None)
agent.stream(prompt_or_task, context=None)
await agent.receive(event_or_signal, adapter=None, session_id=None)
agent.session(config=None)
agent.resolve_knowledge(query)
```

### `agent.run()`

```python
result = await agent.run("Summarize this design document.")
print(result.output)
print(result.state)
```

Use it for one-off requests, stateless flows, extraction, classification, and simple chat endpoints.

### `agent.stream()`

```python
async for event in agent.stream("Analyze the current requirement."):
    print(event.type, event.payload)
```

This streams run events for event-driven UIs, status displays, and debugging.

### `agent.receive()`

```python
from loom import SignalAdapter

adapter = SignalAdapter(
    source="gateway:slack",
    type="message",
    summary=lambda event: event["text"],
)

await agent.receive(
    {"text": "Customer asks for deployment status"},
    adapter=adapter,
    session_id="support",
)
```

`receive()` accepts an existing `RuntimeSignal` or a raw event plus `SignalAdapter`. The signal is stored in the target session's runtime dashboard; `AttentionPolicy` decides whether it should trigger execution.

### `agent.session()`

```python
from loom import SessionConfig

session = agent.session(SessionConfig(id="assistant-1"))
```

Behavior rules:

- `agent.session()` with no config returns a new `Session`
- `agent.session(SessionConfig(id="same"))` reuses the same session object when available
- reused sessions merge metadata

### `agent.resolve_knowledge()`

```python
from loom import KnowledgeQuery, RunContext

bundle = agent.resolve_knowledge(
    KnowledgeQuery(
        text="How does Loom manage sessions?",
        top_k=3,
    )
)

result = await agent.run(
    "Explain Loom's session model.",
    context=RunContext(knowledge=bundle),
)
```

## 3. `RuntimeTask`

Use `RuntimeTask` when a run needs structured input or acceptance criteria.

```python
from loom import RuntimeTask

task = RuntimeTask(
    goal="Refactor the provider tool-call path",
    input={"providers": ["openai", "anthropic", "gemini"]},
    criteria=["tool call round-trip works", "provider details stay out of engine"],
)

result = await agent.run(task)
```

## 4. `SessionConfig`

`SessionConfig` is the input object for session-level configuration.

```python
from loom import SessionConfig

config = SessionConfig(
    id="demo",
    metadata={"tenant": "acme"},
    extensions={"trace_id": "req-123"},
)
```

| Field | Description |
|---|---|
| `id` | Explicit session identifier; the same id reuses the same session |
| `metadata` | Business metadata |
| `extensions` | Future-compatible extension fields |

## 5. `Session`

`Session` represents one stateful interaction scope.

```python
session.start(prompt_or_task, context=None)
await session.run(prompt_or_task, context=None)
session.stream(prompt_or_task, context=None)
await session.receive(event_or_signal, adapter=None)
session.get_run(run_id)
session.list_runs()
await session.close()
```

### `session.start()`

```python
run = session.start("Inspect the current repository layout.")
```

This creates a `Run` but does not wait for completion.

### `session.run()`

```python
result = await session.run("Generate a requirement summary.")
```

Equivalent to:

```python
run = session.start("Generate a requirement summary.")
result = await run.wait()
```

### `session.receive()`

```python
from loom import RuntimeSignal

await session.receive(
    RuntimeSignal.create(
        "Nightly job completed",
        source="cron",
        type="job",
        urgency="normal",
    )
)
```

## 6. `RunContext`

`RunContext` is the run-scoped structured context object.

```python
from loom import RunContext

context = RunContext(
    inputs={
        "repo": "loom-agent",
        "tenant": "acme",
    },
    extensions={"trace_id": "req-123"},
)
```

| Field | Description |
|---|---|
| `inputs` | Structured inputs for the current run |
| `knowledge` | Optional grounded knowledge evidence |
| `extensions` | Future-compatible extension fields |

Prefer putting business context in `inputs` rather than hiding it inside the prompt.

## 7. `Run`

`Run` represents one concrete execution.

```python
await run.wait()
run.events()
await run.artifacts()
await run.transcript()
```

### `run.events()`

```python
async for event in run.events():
    print(event.type, event.payload)
```

Typical event types include `run.started`, `run.completed`, `run.failed`, `artifact.created`, and provider/tool-loop events.

### `run.transcript()`

Returns a serializable dictionary with run id, session id, state, prompt/task, context, output, events, and artifacts. This is useful for persistence, auditing, and debugging.

## 8. `RunResult`

`RunResult` is returned by `run.wait()`, `session.run()`, and `agent.run()`.

| Field | Description |
|---|---|
| `run_id` | Run identifier |
| `state` | Final run state |
| `output` | Final output |
| `artifacts` | Output artifacts |
| `events` | Execution events |
| `error` | Optional error payload |
| `duration_ms` | Execution duration |

## 9. `tool()` Decorator

`tool()` turns a Python function into a Loom tool declaration.

```python
from loom import Agent, Model, tool


@tool(description="Get the weather for a city", read_only=True)
def get_weather(city: str) -> str:
    return f"{city}: sunny"


agent = Agent(
    model=Model.openai("gpt-5.1"),
    tools=[get_weather],
)
```

Common parameters:

| Parameter | Description |
|---|---|
| `name` | Custom tool name |
| `description` | Tool description |
| `read_only` | Whether the tool is read-only |
| `destructive` | Whether the tool is destructive |
| `concurrency_safe` | Whether the tool is concurrency-safe |
| `requires_permission` | Whether the tool requires permission |

## 10. Recommended End-to-End Shape

```python
import asyncio

from loom import Agent, Files, Generation, Model, RunContext, Runtime, SessionConfig, tool


@tool(description="Search repository docs", read_only=True)
def search_docs(query: str) -> str:
    return f"results for: {query}"


async def main():
    agent = Agent(
        model=Model.openai("gpt-5.1"),
        instructions="You are a repository assistant.",
        generation=Generation(temperature=0.2, max_output_tokens=512),
        tools=[search_docs],
        capabilities=[Files(read_only=True)],
        runtime=Runtime.long_running(criteria=["answers cite repo evidence"]),
    )

    session = agent.session(SessionConfig(id="repo-assistant"))

    result = await session.run(
        "Summarize the API design.",
        context=RunContext(inputs={"repo": "loom-agent"}),
    )
    print(result.output)


asyncio.run(main())
```

Next:

- [Providers](providers.md)
- [Configuration](configuration.md)

Related examples:

- [03_events_and_artifacts.py](https://github.com/kongusen/loom-agent/blob/main/examples/03_events_and_artifacts.py)
- [04_multi_task_session.py](https://github.com/kongusen/loom-agent/blob/main/examples/04_multi_task_session.py)
- [16_signal_adapters.py](https://github.com/kongusen/loom-agent/blob/main/examples/16_signal_adapters.py)
