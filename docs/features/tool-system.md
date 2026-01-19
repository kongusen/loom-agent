# Tool System

The **Tool System** is Loom's interface with the external world. It allows Agents to perform actions, retrieve data, and effect change. Loom's approach to tools prioritizes **Safety**, **Simplicity**, and **Parallelism**.

## Core Philosophy

1.  **Any Python Function is a Tool**: You don't need complex wrapper classes. A simple Python function with type hints is all that's required.
2.  **MCP Compatibility**: Loom internally converts all tools to the **Model Context Protocol (MCP)** standard, ensuring compatibility with the broader AI ecosystem.
3.  **Safety First**: Read-only tools are distinguished from side-effect tools.

## The Tool Registry

The `ToolRegistry` is the central catalogue of capabilities.

### Registering a Tool

```python
def get_weather(city: str) -> str:
    """Get the weather for a specific city."""
    return "Sunny, 25C"

# Registering is clear and simple
registry.register_function(get_weather)
```

Loom automatically analyzes the signature, docstring, and type hints to generate the JSON schema for the LLM.

## Execution Engine

The `ToolExecutor` is a high-performance engine capable of **Parallel Execution**.

### Parallel vs. Serial
*   **Read-Only Tools**: Can be executed in parallel. If an agent asks for the weather in 3 cities, Loom fetches them simultaneously.
*   **Side-Effect Tools**: Executed serially to ensure state consistency.

### The Safety Barrier
Loom implements a "Barrier" synchronization primitive.
1.  All pending read-only tools are launched (Batch 1).
2.  System waits for all to complete.
3.  The first side-effect tool is executed (Batch 2).
4.  System waits.
5.  Next batch proceeds.

This guarantees that you never have race conditions where an agent reads a file while simultaneously writing to it.
