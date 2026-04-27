# Getting Started

Get a Loom agent running in under 5 minutes.

## Installation

```bash
pip install loom-agent
export ANTHROPIC_API_KEY=sk-ant-...
```

## Minimal Example

```python
import asyncio

from loom import Agent, Model, Runtime


async def main():
    agent = Agent(
        model=Model.anthropic("claude-sonnet-4"),
        instructions="You are a concise assistant.",
        runtime=Runtime.sdk(),
    )

    result = await agent.run("List the main capabilities of Loom")
    print(result.output)


asyncio.run(main())
```

## What To Learn First

1. `Agent` is the only top-level execution object.
2. `Model` selects the provider-backed model.
3. `Runtime` selects the execution profile and policy composition.
4. `Capability` declares files, web, shell, MCP, and skill access.
5. Use `agent.run()` for one-off executions.
6. Use `agent.session(SessionConfig(...))` when the application needs continuity.
7. Use `RuntimeSignal` and `SignalAdapter` for gateway, cron, heartbeat, webhook, and application events.

## Import Rule

- Start from `from loom import ...` for the main application path.
- Use `from loom.config import ...` for advanced configuration internals.
- Use `from loom.runtime import ...` only when you need runtime states or mechanism contracts directly.

## Provider Selection

Use `Model` to select a provider-backed model:

- `Model.anthropic(...)`
- `Model.openai(...)`
- `Model.gemini(...)`
- `Model.qwen(...)`
- `Model.ollama(...)`

Provider implementations live under `loom/providers/`, but application code should normally configure providers through `Model`.

## Next

1. [First Agent](first-agent.md)
2. [API Reference](../07-api-reference/README.md)
3. [Core Concepts](../02-core-concepts/README.md)
4. [Architecture](../Architecture.md)
