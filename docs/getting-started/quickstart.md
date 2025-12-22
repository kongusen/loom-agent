# Quickstart

Welcome to Loom! This guide will get you up and running with your first intelligent agent in minutes.

## Prerequisites

- Python 3.9 or higher
- An API Key (OpenAI, DeepSeek, Anthropic, etc.)

## 1. Installation

```bash
pip install loom-agent
```

## 2. Your First Agent

Create a file named `app.py`:

```python
import asyncio
from loom.builtin import Agent, OpenAILLM, tool

# 1. Define a Tool
@tool
async def get_weather(city: str) -> str:
    """Get the weather for a city."""
    return f"The weather in {city} is Sunny, 25°C"

async def main():
    # 2. Configure LLM (Class-First)
    llm = OpenAILLM(api_key="sk-...", model="gpt-4o-mini")

    # 3. Create Agent
    agent = Agent(
        name="WeatherBot",
        llm=llm,
        tools=[get_weather],
        system_prompt="You are a helpful weather assistant."
    )

    # 4. Run it
    response = await agent.invoke("What's the weather in Tokyo?")
    print(response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

## 3. Key Concepts

- **Class-First Config**: We explicit instantiated `OpenAILLM`. Use `DeepSeekLLM` or `ClaudeLLM` for other providers.
- **@tool Decorator**: Adding `Async` functions as tools is as simple as adding a decorator. Type hints are mandatory!
- **Agent**: The main orchestrator that manages the loop of "Thinking" (LLM) and "Acting" (Tools).

## Next Steps

- [Configuration Guide](../guides/configuration.md): Learn about supported LLMs.
- [Tool System](../guides/tools.md): Learn to build complex tools.
- [Patterns](../guides/patterns.md): Build complex workflows.
