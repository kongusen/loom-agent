# Loom API Reference

Loom provides a FastAPI-style API with type safety, automatic validation, and intuitive design.

## Overview

The Loom API is built around two main components:

1. **LoomApp** - The main application class for managing agents and infrastructure
2. **AgentConfig** - Pydantic model for type-safe agent configuration

## LoomApp

The main application class that manages agents, event bus, and dispatcher.

### Creating an Application

```python
from loom.api import LoomApp

# Create application with default components
app = LoomApp()

# Or provide custom components
from loom.events import EventBus
from loom.runtime import Dispatcher

event_bus = EventBus()
dispatcher = Dispatcher(event_bus)

app = LoomApp(
    event_bus=event_bus,
    dispatcher=dispatcher
)
```

### LoomApp Methods

#### `set_llm_provider(provider: LLMProvider) -> LoomApp`

Set the global LLM provider for all agents.

**Parameters:**
- `provider` (LLMProvider): LLM provider instance

**Returns:** Self (supports method chaining)

**Example:**
```python
from loom.providers.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-api-key")
app.set_llm_provider(llm)
```

#### `add_tools(tools: list[dict]) -> LoomApp`

Add global tools available to all agents.

**Parameters:**
- `tools` (list): List of tool definitions

**Returns:** Self (supports method chaining)

**Example:**
```python
def get_weather(city: str) -> str:
    return f"Weather in {city}: Sunny"

app.add_tools([get_weather])
```

#### `create_agent(config: AgentConfig, llm_provider: Optional[LLMProvider] = None, tools: Optional[list] = None, memory: Optional[LoomMemory] = None) -> Agent`

Create an agent with Pydantic configuration.

**Parameters:**
- `config` (AgentConfig): Agent configuration (Pydantic model)
- `llm_provider` (Optional[LLMProvider]): LLM provider (defaults to global)
- `tools` (Optional[list]): Agent-specific tools (merged with global tools)
- `memory` (Optional[LoomMemory]): Custom memory system

**Returns:** Agent instance

**Raises:** ValueError if LLM provider is not configured

**Example:**
```python
from loom.api import AgentConfig

config = AgentConfig(
    agent_id="assistant",
    name="My Assistant",
    system_prompt="You are a helpful assistant",
)

agent = app.create_agent(config)
```

#### `get_agent(agent_id: str) -> Optional[Agent]`

Get an existing agent by ID.

**Parameters:**
- `agent_id` (str): Agent ID

**Returns:** Agent instance or None if not found

**Example:**
```python
agent = app.get_agent("assistant")
if agent:
    print(f"Found agent: {agent.node_id}")
```

#### `list_agents() -> list[str]`

List all created agent IDs.

**Returns:** List of agent ID strings

**Example:**
```python
agent_ids = app.list_agents()
print(f"Total agents: {len(agent_ids)}")
```

## AgentConfig

Pydantic model for type-safe agent configuration with automatic validation.

### Fields

#### Required Fields

- **`agent_id`** (str): Unique identifier for the agent
  - Min length: 1
  - Max length: 100

- **`name`** (str): Human-readable agent name
  - Min length: 1
  - Max length: 200

#### Optional Fields

- **`system_prompt`** (str): System prompt for the agent
  - Default: "You are a helpful AI assistant"

- **`capabilities`** (list[str]): List of agent capabilities
  - Valid values: "tool_use", "reflection", "planning", "multi_agent"
  - Default: ["tool_use"]

- **`max_iterations`** (int): Maximum number of iterations
  - Range: 1-100
  - Default: 10

- **`max_context_tokens`** (int): Maximum context tokens
  - Range: 1000-1000000
  - Default: 100000

- **`enable_observation`** (bool): Enable observation mode
  - Default: True

- **`require_done_tool`** (bool): Require done tool call
  - Default: True

### Validation

AgentConfig automatically validates all fields using Pydantic:

```python
from loom.api import AgentConfig
from pydantic import ValidationError

# Valid configuration
config = AgentConfig(
    agent_id="agent-1",
    name="Agent 1",
    max_iterations=10,
)

# Invalid configuration (raises ValidationError)
try:
    config = AgentConfig(
        agent_id="agent-2",
        name="Agent 2",
        max_iterations=200,  # Exceeds maximum (100)
    )
except ValidationError as e:
    print(f"Validation error: {e}")

# Invalid capability (raises ValidationError)
try:
    config = AgentConfig(
        agent_id="agent-3",
        name="Agent 3",
        capabilities=["invalid_capability"],
    )
except ValidationError as e:
    print(f"Validation error: {e}")
```

## Complete Example

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 1. Create application
app = LoomApp()

# 2. Configure global LLM provider
llm = OpenAIProvider(
    api_key="your-api-key",
    model="gpt-4"
)
app.set_llm_provider(llm)

# 3. Add global tools
def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Search results for: {query}"

app.add_tools([search_web])

# 4. Create agents with different configurations
assistant_config = AgentConfig(
    agent_id="assistant",
    name="General Assistant",
    system_prompt="You are a helpful general assistant",
    capabilities=["tool_use", "reflection"],
    max_iterations=10,
)

analyst_config = AgentConfig(
    agent_id="analyst",
    name="Data Analyst",
    system_prompt="You are a data analysis expert",
    capabilities=["tool_use", "planning"],
    max_iterations=15,
)

assistant = app.create_agent(assistant_config)
analyst = app.create_agent(analyst_config)

# 5. List all agents
print(f"Created agents: {app.list_agents()}")

# 6. Get specific agent
agent = app.get_agent("assistant")
print(f"Retrieved agent: {agent.node_id}")
```

## Method Chaining

LoomApp supports method chaining for fluent API design:

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# Chain methods together
app = (
    LoomApp()
    .set_llm_provider(OpenAIProvider(api_key="key"))
    .add_tools([search_web, calculate])
)

# Create agent
agent = app.create_agent(AgentConfig(
    agent_id="agent",
    name="Agent",
))
```

## Type Safety

The API provides complete type annotations for IDE support:

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider
from loom.orchestration import Agent

# Type hints work automatically
app: LoomApp = LoomApp()
llm: OpenAIProvider = OpenAIProvider(api_key="key")
config: AgentConfig = AgentConfig(agent_id="agent", name="Agent")
agent: Agent = app.create_agent(config)
```

## Error Handling

The API provides clear error messages:

```python
from loom.api import LoomApp, AgentConfig
from pydantic import ValidationError

app = LoomApp()

# Missing LLM provider
try:
    config = AgentConfig(agent_id="agent", name="Agent")
    agent = app.create_agent(config)
except ValueError as e:
    print(f"Error: {e}")
    # Error: LLM provider is required. Set it globally with set_llm_provider()
    # or pass it to create_agent()

# Invalid configuration
try:
    config = AgentConfig(
        agent_id="agent",
        name="Agent",
        max_iterations=200,  # Exceeds maximum
    )
except ValidationError as e:
    print(f"Validation error: {e}")
    # Validation error: max_iterations must be <= 100
```

## Next Steps

- Learn about [LLM Providers](../providers/llm-providers.md)
- Explore [Memory System](../features/memory-system.md)
- Understand [Event System](../features/event-system.md)
