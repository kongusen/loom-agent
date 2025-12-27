# Tutorial 2: Adding Skills to Agent

> **Learning Goal**: Understand the concept of Skill, learn to add pre-built and custom skills to Agent

## What is a Skill?

Skill is the unit of capability encapsulation in loom-agent, it contains:

- **Tool**: Function that Agent can call
- **Prompt**: Instructions on how to use the tool
- **Memory Config**: Optional memory management configuration

## Using Pre-built Skills

loom-agent provides some out-of-the-box skills:

### Example: Adding Calculation Capability

```python
from loom.weave import create_agent, run
from loom.stdlib.skills import CalculatorSkill

# Create Agent
agent = create_agent("CalcAssistant", role="Math Assistant")

# Add Calculator Skill
calc_skill = CalculatorSkill()
calc_skill.register(agent)

# Run Task
result = run(agent, "Calculate 123 * 456")
print(result)
```

### Understand the Code

1. **Import Skill**: Import pre-built skill from `loom.stdlib.skills`
2. **Create Skill Instance**: `CalculatorSkill()`
3. **Register to Agent**: `calc_skill.register(agent)` adds skill to Agent

## Available Pre-built Skills

| Skill | Function | Import Path |
|-------|----------|-------------|
| `CalculatorSkill` | Math Calculation | `loom.stdlib.skills` |
| `FileSystemSkill` | File Read/Write | `loom.stdlib.skills` |

## Creating Custom Skills

You can create your own skills to extend Agent capabilities.

### Step 1: Inherit Skill Base Class

```python
from loom.stdlib.skills.base import Skill
from loom.weave import create_tool
from loom.node.tool import ToolNode
from typing import List

class WeatherSkill(Skill):
    """Weather Query Skill"""

    def __init__(self):
        super().__init__(
            name="weather",
            description="Query weather information"
        )
```

### Step 2: Implement get_tools() Method

```python
    def get_tools(self) -> List[ToolNode]:
        """Return weather query tool"""

        def get_weather(city: str) -> str:
            """
            Query city weather.

            Args:
                city: City name

            Returns:
                Weather information
            """
            # This is a mock implementation, should call weather API in reality
            return f"{city} weather: Sunny, 25°C"

        return [create_tool("get_weather", get_weather, "Query city weather")]

    def get_system_prompt(self) -> str:
        """Return system prompt (optional)"""
        return "You can use get_weather tool to query city weather information."
```

### Step 3: Use Custom Skill

```python
from loom.weave import create_agent, run

# Create Agent
agent = create_agent("WeatherAssistant", role="Weather Query Assistant")

# Add Custom Skill
weather_skill = WeatherSkill()
weather_skill.register(agent)

# Run Task
result = run(agent, "How is the weather in Beijing?")
print(result)
```

## Combining Multiple Skills

An Agent can have multiple skills:

```python
from loom.weave import create_agent, run
from loom.stdlib.skills import CalculatorSkill

# Create Agent
agent = create_agent("MultiAssistant", role="General Assistant")

# Add multiple skills
calc_skill = CalculatorSkill()
calc_skill.register(agent)

weather_skill = WeatherSkill()
weather_skill.register(agent)

# Agent can now handle both calculation and weather query
result = run(agent, "Calculate 100 + 200, then tell me the weather in Shanghai")
print(result)
```

## Next Steps

→ [Tutorial 3: Building Agent Teams](building-teams.md)
