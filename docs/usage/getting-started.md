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
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

# 1. Configure LLM provider
llm = OpenAIProvider(
    api_key="your-api-key",
    model="gpt-4"
)

# 2. Create agent directly
agent = Agent.from_llm(
    llm=llm,
    node_id="my-first-agent",
    system_prompt="You are a helpful AI assistant",
    max_iterations=10,
)

print(f"Agent created: {agent.node_id}")
```

### Creating Multiple Agents

Create multiple agents that share infrastructure:

```python
from loom.agent import Agent

# Create multiple agents (each with their own configuration)
agent1 = Agent.from_llm(
    llm=llm,
    node_id="assistant",
    system_prompt="You are a general purpose assistant",
)

agent2 = Agent.from_llm(
    llm=llm,
    node_id="analyst",
    system_prompt="You are specialized in data analysis",
)

print(f"Created 2 agents: {agent1.node_id}, {agent2.node_id}")
```

## Adding Tools

Tools allow agents to interact with external systems. Pass Python functions as tools:

```python
def get_weather(city: str) -> str:
    """Get weather information for a city."""
    # In real implementation, call weather API
    return f"Weather in {city}: Sunny, 22°C"

def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate Body Mass Index."""
    return round(weight_kg / (height_m ** 2), 2)

# Create agent with tools
from loom.tools.registry import ToolRegistry

tool_registry = ToolRegistry()
tool_registry.register_function(get_weather)
tool_registry.register_function(calculate_bmi)

# Create tool definitions
tools = [
    {
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
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_bmi",
            "description": "Calculate Body Mass Index",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight_kg": {"type": "number", "description": "Weight in kg"},
                    "height_m": {"type": "number", "description": "Height in meters"}
                },
                "required": ["weight_kg", "height_m"]
            }
        }
    }
]

agent = Agent.from_llm(
    llm=llm,
    node_id="health-assistant",
    system_prompt="You help with health and weather queries",
    tools=tools,
    tool_registry=tool_registry,
)
print(f"Agent created with tools")
```

## Integrating LLM Providers

To connect real LLM providers, configure them globally or per-agent:

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

# Initialize LLM provider
llm = OpenAIProvider(
    api_key="your-api-key",
    model="gpt-4"
)

# Create agent with LLM provider
agent = Agent.from_llm(
    llm=llm,
    node_id="smart-agent",
    system_prompt="You are an intelligent assistant",
)
```

## Building Fractal Agents

Loom allows you to compose agents into hierarchical teams using `CompositeNode`. This enables you to build complex "Cognitive Organisms" that can handle tasks exceeding the context limit of a single model.

See the [Fractal Tree Example](examples/fractal_tree.py) for a complete code sample.

```python
from loom.fractal.composite import CompositeNode
from loom.fractal.strategies import ParallelStrategy

team = CompositeNode(
    node_id="team",
    children=[agent_a, agent_b],
    strategy=ParallelStrategy()
)
```


*   Explore [Fractal Architecture](../framework/fractal-architecture.md) to understand how to build complex, nested agents
*   Read about [Metabolic Memory](../features/memory-system.md) to see how your agent remembers
*   Check the [API Reference](api-reference.md) for complete API documentation
*   Learn about [Orchestration Patterns](../features/orchestration.md) for multi-agent collaboration
