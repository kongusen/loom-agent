# Getting Started

Get a Loom agent running in under 5 minutes.

## Installation

```bash
pip install loom-agent
# or with uv
uv add loom-agent
```

## Minimal Example

```python
import asyncio
from loom.api import AgentRuntime, AgentProfile
from loom.providers import AnthropicProvider

async def main():
    runtime = AgentRuntime(
        profile=AgentProfile.from_preset("default"),
        provider=AnthropicProvider(api_key="sk-ant-..."),
    )
    session = runtime.create_session()
    task = session.create_task("List the files in the current directory")
    run = task.start()
    result = await run.wait()
    print(result.output)

asyncio.run(main())
```

## Learning Path

1. [First Agent](first-agent.md) — build and run your first agent
2. [Core Concepts](../02-core-concepts/README.md) — understand how Loom works
3. [API Reference](../07-api-reference/README.md) — full API docs

## Supported Providers

| Provider | Class | Notes |
|---|---|---|
| Anthropic | `AnthropicProvider` | Claude models |
| OpenAI | `OpenAIProvider` | GPT models, compatible APIs |
| Google | `GeminiProvider` | Gemini models |

All providers include built-in retry and circuit breaker.
