# Getting Started with Loom

Welcome to Loom. This guide will help you build your first **Cognitive Agent**.

## Installation

Loom is available via PyPI:

```bash
pip install loom-agent
```

## Prerequisites

You will need an API key for your preferred LLM provider (OpenAI, Anthropic, or Gemini).

```bash
export OPENAI_API_KEY="sk-..."
```

## Your First Agent

Loom provides a FastAPI-style API for creating agents with type safety and automatic validation.

### Basic Usage

Create your first agent using Pydantic configuration:

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# 1. Create application
app = LoomApp()

# 2. Configure LLM provider
llm = OpenAIProvider(
    api_key="your-api-key",
    model="gpt-4"
)
app.set_llm_provider(llm)

# 3. Create agent with Pydantic config
config = AgentConfig(
    agent_id="my-first-agent",
    name="My First Agent",
    system_prompt="You are a helpful AI assistant",
    capabilities=["tool_use", "reflection"],
    max_iterations=10,
)

agent = app.create_agent(config)
print(f"Agent created: {agent.node_id}")
```

### Creating Multiple Agents

Create multiple agents that share infrastructure:

```python
from loom.api import LoomApp, AgentConfig

app = LoomApp()
app.set_llm_provider(llm)

# Create multiple agents (shared event bus and dispatcher)
agent1 = app.create_agent(AgentConfig(
    agent_id="assistant",
    name="Assistant",
    system_prompt="You are a general purpose assistant",
))

agent2 = app.create_agent(AgentConfig(
    agent_id="analyst",
    name="Data Analyst",
    system_prompt="You are specialized in data analysis",
))

# List all agents
print(f"Created {len(app.list_agents())} agents")
```

## Adding Tools

Tools allow agents to interact with external systems. Pass Python functions as tools:

```python
from loom.api import LoomApp, AgentConfig

def get_weather(city: str) -> str:
    """Get weather information for a city."""
    # In real implementation, call weather API
    return f"Weather in {city}: Sunny, 22°C"

def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate Body Mass Index."""
    return round(weight_kg / (height_m ** 2), 2)

# Create agent with tools
app = LoomApp()
app.set_llm_provider(llm)

config = AgentConfig(
    agent_id="health-assistant",
    name="Health Assistant",
    system_prompt="You help with health and weather queries",
)

agent = app.create_agent(config, tools=[get_weather, calculate_bmi])
print(f"Agent created with tools")
```

## Integrating LLM Providers

To connect real LLM providers, configure them globally or per-agent:

```python
from loom.api import LoomApp, AgentConfig
from loom.providers.llm import OpenAIProvider

# Initialize LLM provider
llm = OpenAIProvider(
    api_key="your-api-key",
    model="gpt-4"
)

# Create app and set global LLM provider
app = LoomApp()
app.set_llm_provider(llm)

# Create agent (uses global LLM provider)
config = AgentConfig(
    agent_id="smart-agent",
    name="Smart Agent",
    system_prompt="You are an intelligent assistant",
)

agent = app.create_agent(config)
```

## Next Steps

*   Explore [Fractal Architecture](../framework/fractal-architecture.md) to understand how to build complex, nested agents
*   Read about [Metabolic Memory](../features/memory-system.md) to see how your agent remembers
*   Check the [API Reference](api-reference.md) for complete API documentation
*   Learn about [Orchestration Patterns](../features/orchestration.md) for multi-agent collaboration
