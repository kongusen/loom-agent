"""
Loom v0.2.1 - AI-Native Agent Framework
=======================================

👋 **Hello Agent/Developer!** 
If you are an AI reading this usage guide to understand how to build with Loom, utilize this roadmap.

## 🌟 Core Architecture (Mental Model)

Loom is built on the **"Everything is a Runnable"** philosophy.
- **Atomic Unit**: `Runnable` (see `loom.core.runnable`). All components (LLMs, Tools, Agents) inherit from this.
- **Composition**: Build complex workflows by composing Runnables.
  - `Sequence`: A >> B (Linear chain)
  - `Group`: [A, B] (Parallel execution)
  - `Router`: A -> {B, C} (Conditional branching)
- **Execution**: The `RecursiveEngine` drive the "Think-Act-Observe" loop.

## 🧭 Developer Map (Where to find things)

### 1. The Brain (`loom.execution`)
- **Agent**: The main orchestrator (`from loom.execution import Agent`).
- **Engine**: The runtime loop (`loom.execution.engine.RecursiveEngine`).

### 2. The Parts (`loom.builtin`)
- **LLMs**: Connection to models (`OpenAILLM`, `DeepSeekLLM`). *Class-First Config!*
- **Tools**: Capability decorators (`@tool`).
- **Memory**: State persistence (`InMemoryMemory`).

### 3. The Glue (`loom.patterns`)
- **Composition**: `Sequence`, `Group`, `Router`.

## 🚀 Quick Start Pattern

```python
from loom.builtin import Agent, OpenAILLM, tool

@tool
async def search(query: str): ...

llm = OpenAILLM(api_key="...")
agent = Agent(name="Bot", llm=llm, tools=[search])
await agent.invoke("Hello")
```
"""

from loom.core import (
    Runnable,
    Message,
    BaseMessage,
    SystemMessage,
    UserMessage,
    AssistantMessage,
    ToolMessage,
)

__all__ = [
    "Runnable",
    "Message",
    "BaseMessage",
    "SystemMessage",
    "UserMessage",
    "AssistantMessage",
    "ToolMessage",
]
