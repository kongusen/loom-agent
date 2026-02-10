# Loom API Reference

Loom provides a direct, intuitive API for creating and managing AI agents with type safety and automatic validation.

**Version**: This reference reflects the v0.5.0 API. For breaking changes and migration, see [Migration Guide](migration-v0.5.md) and [What's New in v0.5.0](whats-new-v0.5.md).

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

- **`memory_config`** (MemoryConfig | dict): Memory configuration for the agent
  - Default: None
  - Supports either `MemoryConfig` (recommended) or a dict with `max_l1_size/max_l2_size/max_l3_size`
  - Note: v0.5.0 maps `MemoryConfig.l1/l2/l3.capacity` to L1–L3 sizes
  - Retention: `l1/l2/l3.retention_hours` will evict expired items
  - Promotion: `l1.promote_threshold` (access-count) and `l2.promote_threshold` (summarization bias)
  - L3: `l3.promote_threshold` used as access-count threshold for vectorization
  - Importance: `importance_threshold` for IMPORTANCE_BASED strategy
  - Compression: `l2.auto_compress` / `l3.auto_compress` gate L2→L3 / L3→L4
  - `enable_auto_migration` / `enable_compression` toggle automatic promotion/compression
  - L4 retention/capacity are best-effort; require a vector store that supports delete (InMemory supports)
  - Strategy: SIMPLE (access-count), IMPORTANCE_BASED (importance), TIME_BASED (age)
  - Default strategy is IMPORTANCE_BASED

- **`context_budget_config`** (BudgetConfig | dict): Context budget configuration
  - Default: None
  - Controls L1/L2/L3+ budget ratios and minimum items

- **`context_config`** (ContextConfig | dict): Unified context-flow configuration
  - Default: None
  - Aggregates memory/budget/compaction/session isolation
  - Explicit parameters override values from `context_config`
  - Dict accepts aliases: `memory_config`, `context_budget_config`, `compaction_config`

- **`session_isolation`** (SessionIsolationMode | str): Session lane isolation mode
  - Default: `"strict"`
  - Options: `"strict"`, `"advisory"`, `"none"`

- **`compaction_config`** (CompactionConfig | dict): Memory compaction configuration
  - Default: CompactionConfig()
  - Controls silent compaction threshold, cooldown, and strategy

- **`tool_policy`** (ToolPolicy): Tool permission policy (optional)
  - Default: None
  - Use `WhitelistPolicy` / `BlacklistPolicy` for explicit control

- **`skills_dir`** (str | Path | list): Skills package directory (SKILL.md format)
  - Default: None
  - Auto-registers `FilesystemSkillLoader` and enables progressive disclosure

- **`skill_loaders`** (list[SkillLoader]): Custom skill loaders
  - Default: None
  - Use for database/HTTP/custom sources

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

**Removed in v0.5.0**: `enable_tool_creation`, `enable_context_tools`. All tools (context tools, tool creation, delegation) are always available; the LLM decides whether to use them.

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

## Runtime & Safety Controls

Configure session isolation, memory compaction, and tool permissions:

```python
from loom.agent import Agent
from loom.config import ContextConfig
from loom.memory import BudgetConfig
from loom.memory.compaction import CompactionConfig
from loom.runtime import SessionIsolationMode
from loom.security import WhitelistPolicy

context_config = ContextConfig(
    session_isolation=SessionIsolationMode.STRICT,
    compaction=CompactionConfig(threshold=0.85, strategy="silent"),
    budget=BudgetConfig(l1_ratio=0.35, l2_ratio=0.25, l3_l4_ratio=0.20),
)

agent = Agent.create(
    llm,
    node_id="assistant",
    context_config=context_config,
    tool_policy=WhitelistPolicy(allowed_tools={"done", "store_memory", "recall_memory"}),
)
```

## L4 Vector Store Setup

```python
from loom.memory.vector_store import InMemoryVectorStore
from loom.providers.embedding.openai import OpenAIEmbeddingProvider

agent.memory.set_vector_store(InMemoryVectorStore())
agent.memory.set_embedding_provider(OpenAIEmbeddingProvider(api_key="your-api-key"))
```

## Skill Packages (Anthropic-style)

```python
from loom.agent import Agent

# skills/your-skill/SKILL.md + scripts/ + references/
agent = Agent.create(
    llm,
    node_id="assistant",
    skills_dir="./skills",
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
from loom.runtime import Task

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

## CapabilityRegistry (v0.5.0)

Unified capability discovery and dependency validation. Both methods are **async**; use `await` when calling.

- **`find_relevant_capabilities(task_description, context=None)`** → `CapabilitySet`  
  Returns tools (from SandboxToolManager) and skill IDs (from SkillRegistry, including Loaders and runtime-registered skills). Call as `await registry.find_relevant_capabilities(...)`.

- **`validate_skill_dependencies(skill_id)`** → `ValidationResult`  
  Checks that the skill’s required tools are available (via SandboxToolManager). Call as `await registry.validate_skill_dependencies(skill_id)`.

See [What's New in v0.5.0](whats-new-v0.5.md) for unified SkillRegistry and SkillActivator `tool_manager` usage.

## Next Steps

- [Migration Guide v0.4.x → v0.5.0](migration-v0.5.md)
- [What's New in v0.5.0](whats-new-v0.5.md)
- Explore [Memory System](../features/memory-system.md)
- Understand [Event System](../framework/event-bus.md)
