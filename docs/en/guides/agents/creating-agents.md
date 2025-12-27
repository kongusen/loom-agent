# Creating Agents

> **Problem-Oriented** - Learn to create and configure Agents using different methods

## Overview

loom-agent provides multiple ways to create Agents:
- **Simplified API**: Quick creation using `loom.weave`
- **Low-level API**: Fine-grained control using `AgentNode`
- **Pre-built Agents**: Ready-to-use Agents from `loom.stdlib`

## Method 1: Using loom.weave (Recommended)

The simplest creation method, suitable for rapid development:

```python
from loom.weave import create_agent, run

# Create the simplest Agent
agent = create_agent("my-agent", role="General Assistant")

# Run task
result = run(agent, "Hello, please introduce yourself")
print(result)
```

**Features**:
- Create with just 3 lines of code
- Automatic LoomApp management
- Suitable for rapid prototyping

### Adding Tools and Skills

```python
from loom.weave import create_agent, create_tool, run
from loom.stdlib.skills import CalculatorSkill

# Create Agent with tools
def search(query: str) -> str:
    """Search tool"""
    return f"Search results: {query}"

tool = create_tool("search", search)
agent = create_agent("assistant", role="Assistant", tools=[tool])

# Or add skills
agent = create_agent("analyst", role="Analyst")
calc_skill = CalculatorSkill()
calc_skill.register(agent)
```

## Method 2: Using Low-level API

Use `AgentNode` for fine-grained control:

```python
from loom.node.agent import AgentNode, ThinkingPolicy
from loom.api.main import LoomApp
from loom.infra.llm import MockLLMProvider

# Create LoomApp
app = LoomApp()

# Create Agent (full control)
agent = AgentNode(
    node_id="my-agent",
    dispatcher=app.dispatcher,
    role="Advanced Assistant",
    system_prompt="You are a professional AI assistant",
    provider=MockLLMProvider(),
    thinking_policy=ThinkingPolicy(enabled=True)
)

# Run task
result = await app.run(agent, "Analyze this problem")
```

**Features**:
- Complete control over all parameters
- Supports advanced configuration
- Suitable for production environments

## Method 3: Using Pre-built Agents

Use ready-to-use Agents from `loom.stdlib`:

```python
from loom.stdlib.agents import CoderAgent, AnalystAgent
from loom.weave import run

# Use pre-built Coder Agent
coder = CoderAgent("my-coder", base_dir="./src")
result = run(coder, "Create a hello.py file")

# Use pre-built Analyst Agent
analyst = AnalystAgent("my-analyst")
result = run(analyst, "Calculate 123 * 456")
```

**Available Pre-built Agents**:
- `CoderAgent`: Has file operation capabilities
- `AnalystAgent`: Has calculation capabilities

**Features**:
- Ready to use out of the box
- Pre-configured with common skills
- Suitable for rapid development

## Related Documentation

- [Configuring Agents](configuring-agents.md) - Detailed Agent configuration options
- [Configuring LLM Providers](../configuration/llm-providers.md) - Configure LLM providers
- [Creating Custom Skills](../skills/creating-custom-skills.md) - Add capabilities to Agents

