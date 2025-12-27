# Quick Start

> Create your first Agent in 5 minutes

## Step 1: Installation

```bash
pip install loom-agent
```

## Step 2: Create Your First Agent

Create a new file `my_agent.py`:

```python
from loom.weave import create_agent, run

# Create Agent
agent = create_agent("Assistant", role="General Assistant")

# Run Task
result = run(agent, "Hello, please introduce yourself")
print(result)
```

Run:

```bash
python my_agent.py
```

## Step 3: Add Skills

Enable the Agent with calculation capabilities:

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

## Step 4: Use Pre-built Agents

A simpler way:

```python
from loom.stdlib.agents import AnalystAgent
from loom.weave import run

# Use pre-built Analyst Agent
analyst = AnalystAgent("my-analyst")

# Run Task
result = run(analyst, "Calculate 2024 * 365")
print(result)
```

## Next Steps

🎉 Congratulations! You have created your first Agent.

**Continue Learning:**
- 📖 [Tutorial: Create Your First Agent](../tutorials/your-first-agent.md)
- 🛠️ [Guide: Create Agents](../guides/agents/)
- 💡 [Concept: Architecture Design](../concepts/architecture.md)
