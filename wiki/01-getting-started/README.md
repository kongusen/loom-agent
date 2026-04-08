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
from loom import AgentConfig, ModelRef, create_agent


async def main():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a concise assistant.",
        )
    )

    result = await agent.run("List the main capabilities of Loom")
    print(result.output)


asyncio.run(main())
```

## What To Learn First

1. `AgentConfig` is the only top-level config object.
2. `Agent` is the only top-level runtime object.
3. Use `agent.run()` for one-off executions.
4. Use `agent.session(SessionConfig(...))` when the application needs continuity.
5. Use `RunContext` to pass structured runtime inputs and resolved knowledge.

## Import Rule

- Start from `from loom import ...` for the main application path.
- Move to `from loom.config import ...` when you need advanced configuration objects.
- Move to `from loom.runtime import ...` when you need runtime states or run/session handles directly.

## Learning Path

1. [First Agent](first-agent.md)
2. [API Reference](../07-api-reference/README.md)
3. [Core Concepts](../02-core-concepts/README.md)
4. [Architecture](../Architecture.md)

## Providers

Use `ModelRef` to select a provider-backed model:

- `ModelRef.anthropic(...)`
- `ModelRef.openai(...)`
- `ModelRef.gemini(...)`
- `ModelRef.qwen(...)`
- `ModelRef.ollama(...)`

Provider implementations still live under `loom/providers/`, but the public API entry point is `AgentConfig(model=ModelRef(...))`, not direct provider construction.
