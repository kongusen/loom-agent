# Custom Events and Handlers

Loom's Event Bus is extensible. You can define your own event types and handlers.

## 1. Defining Actions

Use `TaskAction` or extend it (if the system supports extension, otherwise use the standard `TaskAction.EXECUTE` with custom payload).

Currently, Loom emphasizes using the standard `TaskAction` Enum for type safety.

## 2. Registering a Custom Handler

```python
import asyncio
from typing import Any
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.types.core import Task
from loom.events.actions import TaskAction

async def my_custom_logger(event):
    """A custom event handler that logs every task."""
    print(f"[AUDIT] Event: {event.type} - {event.data}")

async def main():
    # Create LLM provider
    llm = OpenAIProvider(api_key="your-api-key")

    # Create agent
    agent = Agent.create(
        llm,
        node_id="custom-agent",
        system_prompt="You are a helpful assistant.",
    )

    # Access the event bus via the agent and subscribe to events
    agent.event_bus.subscribe("node.thinking", my_custom_logger)
    agent.event_bus.subscribe("node.tool_call", my_custom_logger)
    print("Registered custom logger.")

    # ... run your agent ...

if __name__ == "__main__":
    asyncio.run(main())
```

> **Note**: In v0.4.2, direct Event Bus manipulation is an advanced feature usually handled by the `Dispatcher`.
