"""
Loom Builtin Components - "The Parts Bin"
=========================================

This module contains the "batteries included" components for building Agents.

## 📦 Component Selector (AI Decision Tree)

### 1. Which LLM to use?
*   **OpenAI**: Use `OpenAILLM`.
*   **DeepSeek**: Use `DeepSeekLLM`.
*   **Claude (Anthropic)**: Use `ClaudeLLM`.
*   **Other/Custom**: Use `CustomLLM` (requires `base_url`).
> ⚠️ **CRITICAL**: Always instantiate the class directly. Do NOT use strings.
> `Agent(llm=OpenAILLM(...))` ✅
> `Agent(llm="openai")` ❌ (Deprecated)

### 2. How to define Tools?
Use the `@tool` decorator on async functions with proper type hints.
```python
@tool
async def search(query: str) -> str:
    \"\"\"Search the web for query.\"\"\"
    ...
```

### 3. Which Memory?
*   **Testing/Stateless**: `InMemoryMemory` (Default).
*   **Production**: `PersistentMemory` (Use with DB).

## 🚀 Usage Example

```python
from loom.builtin import Agent, DeepSeekLLM, tool

# 1. Setup LLM (Class-First)
llm = DeepSeekLLM(api_key="sk-...", temperature=0.7)

# 2. Setup Tool
@tool
async def get_weather(city: str) -> str: ...

# 3. Assemble Agent
agent = Agent(name="Bot", llm=llm, tools=[get_weather])
```
"""

# Tools (核心，无依赖)
from loom.builtin.tools import tool, ToolBuilder

# Memory (核心，无依赖)
from loom.builtin.memory import InMemoryMemory, PersistentMemory

# LLMs (需要 pip install openai)
from loom.builtin.llms import (
    UnifiedLLM,
    OpenAILLM,
    DeepSeekLLM,
    QwenLLM,
    KimiLLM,
    ZhipuLLM,
    DoubaoLLM,
    YiLLM,
)

__all__ = [
    # Tools
    "tool",
    "ToolBuilder",
    # Memory
    "InMemoryMemory",
    "PersistentMemory",
    # LLMs
    "UnifiedLLM",
    "OpenAILLM",
    "DeepSeekLLM",
    "QwenLLM",
    "KimiLLM",
    "ZhipuLLM",
    "DoubaoLLM",
    "YiLLM",
]
