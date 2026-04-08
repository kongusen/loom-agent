# Agent API

This page describes Loom's core runtime objects for application developers.

There is exactly one public execution path:

```text
AgentConfig -> Agent -> Session -> Run
```

## 1. `create_agent()`

```python
from loom import AgentConfig, ModelRef, create_agent

agent = create_agent(
    AgentConfig(
        model=ModelRef.openai("gpt-4.1-mini"),
        instructions="You are a code assistant.",
    )
)
```

`create_agent(config)` returns an `Agent`.

Equivalent form:

```python
from loom import Agent

agent = Agent(
    config=AgentConfig(
        model=ModelRef.openai("gpt-4.1-mini"),
    )
)
```

Prefer `create_agent()` in application code. It is clearer and better matches top-level assembly.

## 2. `Agent`

`Agent` is the only top-level execution object.

### Main Methods

```python
await agent.run(prompt, context=None)
agent.stream(prompt, context=None)
agent.session(config=None)
agent.resolve_knowledge(query)
```

### `agent.run()`

```python
result = await agent.run("Summarize this design document.")
print(result.output)
print(result.state)
```

Use it for:

- one-off requests
- stateless flows
- the simplest possible integration

### `agent.stream()`

```python
async for event in agent.stream("Analyze the current requirement."):
    print(event.type, event.payload)
```

Notes:

- this streams `RunEvent` objects
- it is not token-level text streaming
- it is useful for event-driven UIs, status displays, and debugging

### `agent.session()`

```python
from loom import SessionConfig

session = agent.session(SessionConfig(id="assistant-1"))
```

Behavior rules:

- `agent.session()` with no config returns a new `Session` each time
- `agent.session(SessionConfig(id="same"))` reuses the same `Session` if that id already exists
- reused sessions merge `metadata`

Example:

```python
first = agent.session(SessionConfig(id="demo", metadata={"tenant": "acme"}))
second = agent.session(SessionConfig(id="demo", metadata={"plan": "pro"}))

assert first is second
assert second.metadata == {"tenant": "acme", "plan": "pro"}
```

### `agent.resolve_knowledge()`

```python
from loom import KnowledgeQuery

bundle = agent.resolve_knowledge(
    KnowledgeQuery(
        text="How does Loom manage sessions?",
        top_k=3,
    )
)
```

This resolves the knowledge sources declared in `AgentConfig.knowledge` and returns a `KnowledgeBundle`.

Recommended usage:

```python
from loom import RunContext

result = await agent.run(
    "Explain Loom's session model.",
    context=RunContext(knowledge=bundle),
)
```

## 3. `SessionConfig`

`SessionConfig` is the input object for session-level configuration.

```python
from loom import SessionConfig

config = SessionConfig(
    id="demo",
    metadata={"tenant": "acme"},
    extensions={"trace_id": "req-123"},
)
```

Fields:

| Field | Type | Description |
|---|---|---|
| `id` | `str \| None` | Explicit session identifier; the same id reuses the same session |
| `metadata` | `dict[str, Any]` | Business metadata |
| `extensions` | `dict[str, Any]` | Extension fields |

## 4. `Session`

`Session` represents one stateful interaction scope.

### Main Methods

```python
session.start(prompt, context=None)
await session.run(prompt, context=None)
session.stream(prompt, context=None)
session.get_run(run_id)
session.list_runs()
await session.close()
```

### `session.start()`

```python
run = session.start("Inspect the current repository layout.")
```

This creates a `Run` but does not wait for completion.

Use it when:

- you want to consume events yourself
- you want to separate run creation from run completion

### `session.run()`

```python
result = await session.run("Generate a requirement summary.")
```

Equivalent to:

```python
run = session.start("Generate a requirement summary.")
result = await run.wait()
```

### `session.stream()`

```python
async for event in session.stream("Analyze this monitoring alert."):
    print(event.type)
```

### `session.list_runs()`

```python
runs = session.list_runs()
for run in runs:
    print(run.id, run.prompt, run.state)
```

Returns runs in creation order.

### `session.close()`

```python
await session.close()
```

After closing:

- the session no longer allows `start()`
- tracked run references are released

## 5. `RunContext`

`RunContext` is the input object for run-scoped structured context.

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

Fields:

| Field | Type | Description |
|---|---|---|
| `inputs` | `dict[str, Any]` | Structured inputs for the current run |
| `knowledge` | `KnowledgeBundle \| None` | Explicit grounded knowledge evidence |
| `extensions` | `dict[str, Any]` | Extension fields |

Prefer putting business context in `inputs` rather than hiding it inside the prompt.

## 6. `Run`

`Run` represents one concrete execution.

### Main Methods

```python
await run.wait()
run.events()
await run.artifacts()
await run.transcript()
```

### `run.wait()`

```python
result = await run.wait()
```

Waits for completion and returns a `RunResult`.

### `run.events()`

```python
async for event in run.events():
    print(event.type, event.payload)
```

Typical event types include:

- `run.started`
- `run.completed`
- `run.failed`
- `artifact.created`
- intermediate provider or tool-loop events

### `run.artifacts()`

```python
artifacts = await run.artifacts()
```

By default, Loom emits at least one summary artifact for the final output:

- `kind="text"`
- `title="Run Output"`
- `uri="run://<run_id>/output"`

### `run.transcript()`

```python
transcript = await run.transcript()
```

Returns a serializable dictionary containing:

- `run_id`
- `session_id`
- `state`
- `prompt`
- `context`
- `output`
- `events`
- `artifacts`

This is useful for persistence, auditing, and debugging.

## 7. `RunResult`

`RunResult` is returned by `run.wait()`, `session.run()`, and `agent.run()`.

Fields:

| Field | Type | Description |
|---|---|---|
| `run_id` | `str` | Run identifier |
| `state` | `RunState` | Final run state |
| `output` | `str` | Final output |
| `artifacts` | `list[Artifact]` | Output artifacts |
| `events` | `list[RunEvent]` | Execution events |
| `error` | `dict[str, Any] \| None` | Error payload |
| `duration_ms` | `int` | Execution duration |

## 8. `RunState`

Values:

- `QUEUED`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

## 9. `RunEvent`

`RunEvent` is Loom's standard execution event object.

Fields:

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Event identifier |
| `run_id` | `str` | Owning run id |
| `type` | `str` | Event type |
| `ts` | `datetime` | Timestamp |
| `visibility` | `str` | Visibility level, default `user` |
| `payload` | `dict[str, Any]` | Event payload |

## 10. `Artifact`

Fields:

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Artifact identifier |
| `run_id` | `str` | Owning run id |
| `kind` | `str` | Artifact kind |
| `title` | `str` | Title |
| `uri` | `str` | Access identifier |
| `created_at` | `datetime` | Creation time |
| `metadata` | `dict[str, Any]` | Extra metadata |

## 11. `tool()` Decorator

`tool()` turns a normal Python function into a Loom tool declaration.

```python
from loom import tool


@tool(description="Get the weather for a city", read_only=True)
def get_weather(city: str) -> str:
    return f"{city}: sunny"
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

The decorated object is a `ToolSpec`, so it can go directly into `AgentConfig.tools`:

```python
agent = create_agent(
    AgentConfig(
        model=ModelRef.openai("gpt-4.1-mini"),
        tools=[get_weather],
    )
)
```

## 12. Recommended End-to-End Shape

```python
import asyncio

from loom import AgentConfig, ModelRef, RunContext, SessionConfig, create_agent, tool
from loom.config import GenerationConfig


@tool(description="Search repository docs", read_only=True)
def search_docs(query: str) -> str:
    return f"results for: {query}"


async def main():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.openai("gpt-4.1-mini"),
            instructions="You are a repository assistant.",
            generation=GenerationConfig(temperature=0.2, max_output_tokens=512),
            tools=[search_docs],
        )
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

- [Configuration](configuration.md)
- [Providers](providers.md)

Related examples:

- [03_events_and_artifacts.py](https://github.com/kongusen/loom-agent/blob/main/examples/03_events_and_artifacts.py)
- [04_multi_task_session.py](https://github.com/kongusen/loom-agent/blob/main/examples/04_multi_task_session.py)
