# Loom API Reference

Loom provides a direct, intuitive API for creating and managing AI agents with type safety and automatic validation.

## Overview

The Loom API is built around the **Agent** class, which provides two creation styles:

1. **Agent.create()** - One-shot creation with an LLM and options (recommended)
2. **Agent.builder()** - Chain configuration then `.build()` for more control

## Agent Class

The Agent class represents an autonomous AI agent that can execute tasks, use tools, and collaborate with other agents.

### Creating an Agent

#### Basic Creation with `Agent.create()`

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

# Create LLM provider
llm = OpenAIProvider(api_key="your-api-key", model="gpt-4")

# Create agent
agent = Agent.create(
    llm,
    node_id="assistant",
    system_prompt="You are a helpful AI assistant",
)
```

### Agent.create() Parameters

#### Required Parameters

- **`llm`** (LLMProvider): LLM provider instance (OpenAI, Anthropic, etc.)
- **`node_id`** (str): Unique identifier for the agent

#### Optional Parameters

- **`system_prompt`** (str): System prompt for the agent
  - Default: "You are a helpful AI assistant"

- **`max_iterations`** (int): Maximum number of iterations
  - Range: 1-100
  - Default: 10

- **`require_done_tool`** (bool): Require done tool call to complete tasks
  - Default: True

- **`tools`** (list[dict]): Tool definitions for the agent
  - Default: None

- **`tool_registry`** (ToolRegistry): Tool registry for managing tools
  - Default: None

- **`memory_config`** (MemoryConfig): Memory configuration for the agent
  - Default: None

- **`skills`** (list[str]): List of skill IDs to enable
  - Default: None
  - Example: `["python-dev", "testing"]`

- **`capabilities`** (CapabilityRegistry): Capability registry for advanced configuration
  - Default: None

- **`event_bus`** (EventBus): Event bus for agent communication
  - Default: Auto-created if not provided

- **`knowledge_base`** (KnowledgeBase): Knowledge base provider
  - Default: None

- **`max_context_tokens`** (int): Maximum context tokens for LLM calls
  - Default: 4000

### Creating Agents with Tools

```python
from loom.agent import Agent
from loom.tools.registry import ToolRegistry

def get_weather(city: str) -> str:
    """Get weather information for a city."""
    return f"Weather in {city}: Sunny, 22°C"

# Create tool registry
tool_registry = ToolRegistry()
tool_registry.register_function(get_weather)

# Define tool schema
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather information for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"]
        }
    }
}]

# Create agent with tools
agent = Agent.create(
    llm,
    node_id="weather-assistant",
    system_prompt="You help with weather queries",
    tools=tools,
    tool_registry=tool_registry,
)
```

## Creating Multiple Agents

You can create multiple agents with different configurations:

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-api-key", model="gpt-4")

# Create general assistant
assistant = Agent.create(
    llm,
    node_id="assistant",
    system_prompt="You are a helpful general assistant",
    max_iterations=10,
)

# Create data analyst
analyst = Agent.create(
    llm,
    node_id="analyst",
    system_prompt="You are a data analysis expert",
    max_iterations=15,
)

print(f"Created agents: {assistant.node_id}, {analyst.node_id}")
```

## Complete Example

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.tools.registry import ToolRegistry
from loom.protocol import Task

# 1. Create LLM provider
llm = OpenAIProvider(api_key="your-api-key", model="gpt-4")

# 2. Define tools
def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Search results for: {query}"

def calculate(expression: str) -> float:
    """Calculate a mathematical expression."""
    return eval(expression)

# 3. Create tool registry
tool_registry = ToolRegistry()
tool_registry.register_function(search_web)
tool_registry.register_function(calculate)

# 4. Define tool schemas
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Calculate a mathematical expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression"}
                },
                "required": ["expression"]
            }
        }
    }
]

# 5. Create agent
agent = Agent.create(
    llm,
    node_id="assistant",
    system_prompt="You are a helpful assistant with web search and calculation capabilities",
    tools=tools,
    tool_registry=tool_registry,
    max_iterations=10,
)

print(f"Agent created: {agent.node_id}")
```

## Type Safety

The API provides complete type annotations for IDE support:

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

# Type hints work automatically
llm: OpenAIProvider = OpenAIProvider(api_key="key")
agent: Agent = Agent.create(
    llm,
    node_id="agent",
    system_prompt="You are a helpful assistant"
)
```

## Error Handling

The API provides clear error messages:

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

# Missing required parameters
try:
    agent = Agent.create(
        None,  # Missing LLM provider
        node_id="agent"
    )
except TypeError as e:
    print(f"Error: {e}")

# Invalid parameters
try:
    agent = Agent.create(
        llm,
        node_id="agent",
        max_iterations=200  # Exceeds maximum (100)
    )
except ValueError as e:
    print(f"Error: {e}")
```

## Next Steps

- Learn about [LLM Providers](../providers/llm-providers.md)
- Explore [Memory System](../features/memory-system.md)
- Understand [Event System](../features/event-system.md)
