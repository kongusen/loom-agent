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

## SandboxToolManager (Recommended)

**As of v0.5.0**, the recommended approach for tool management is **SandboxToolManager**. This unified tool manager provides:

- **Unified Interface**: All tools (built-in, custom, MCP) registered through one interface
- **Automatic Sandboxing**: File operations are automatically sandboxed for safety
- **Dynamic Registration**: Tools can be added/removed at runtime
- **Consistent Execution**: Tool list sent to LLM matches actual execution source

### Why SandboxToolManager?

The older `ToolRegistry` approach is maintained for backward compatibility and internal use, but **SandboxToolManager** is the modern, recommended approach because:

1. **Consistency**: Dependency validation and tool execution use the same source
2. **Safety**: Built-in sandboxing for file operations
3. **Simplicity**: Single manager for all tool types
4. **Future-proof**: Designed for the evolving tool ecosystem

### Using SandboxToolManager with Agent

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.tools.sandbox import Sandbox
from loom.tools.sandbox_manager import SandboxToolManager, ToolScope
from loom.protocol.mcp import MCPToolDefinition

# Create sandbox and tool manager
sandbox = Sandbox("/path/to/workspace")
tool_manager = SandboxToolManager(sandbox)

# Register custom tools
async def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 25°C"

await tool_manager.register_tool(
    "get_weather",
    get_weather,
    MCPToolDefinition(
        name="get_weather",
        description="Get weather information for a city",
        inputSchema={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"]
        }
    ),
    ToolScope.SYSTEM
)

# Create agent with tool manager
llm = OpenAIProvider(api_key="your-key")
agent = Agent.create(
    llm,
    node_id="weather-agent",
    system_prompt="You are a weather assistant",
    sandbox_manager=tool_manager,
)
```

### Tool Scopes

SandboxToolManager supports different tool scopes for security:

- **SANDBOXED**: File operations constrained to sandbox directory
- **SYSTEM**: System-level operations (bash, http)
- **MCP**: External MCP server tools
- **CONTEXT**: Context query tools (memory, events)

### Migration from ToolRegistry

If you're currently using `ToolRegistry`, you can migrate gradually:

```python
# Old approach (still supported)
agent = Agent.create(llm, tool_registry=registry)

# New approach (recommended)
agent = Agent.create(llm, sandbox_manager=tool_manager)

# Both work together (tool_manager takes priority)
agent = Agent.create(llm, tool_registry=registry, sandbox_manager=tool_manager)
```

**Recommendation**: Use `sandbox_manager` for all new code. The `tool_registry` parameter is maintained for backward compatibility.
