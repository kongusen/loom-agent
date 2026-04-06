# Your First Agent

## 1. Create a runtime

```python
from loom.api import AgentRuntime, AgentProfile
from loom.providers import AnthropicProvider

runtime = AgentRuntime(
    profile=AgentProfile.from_preset("default"),
    provider=AnthropicProvider(api_key="..."),
)
```

## 2. Start a session and task

```python
session = runtime.create_session()
task = session.create_task(
    goal="Analyze the README and summarize key features",
    context={"repo": "loom-agent"},
)
run = task.start()
```

## 3. Wait for results

```python
result = await run.wait()
print(result.state)    # RunState.COMPLETED
print(result.output)   # agent's answer
```

## 4. Stream events in real time

```python
run = task.start()
async for event in run.events():
    print(event.type, event.payload)
    if event.type == "run.completed":
        break
```

## 5. Cancel or pause

```python
await run.pause()
await run.resume()
await run.cancel()
```

## Next

- [Core Concepts](../02-core-concepts/README.md) — understand what's happening inside
- [API Reference](../07-api-reference/README.md) — full method signatures
