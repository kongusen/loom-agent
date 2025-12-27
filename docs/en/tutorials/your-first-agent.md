# Tutorial 1: Create Your First Agent

> **Learning Goal**: Understand basic Agent concepts, create and run a simple Agent

## What is an Agent?

An Agent is the basic computational unit in loom-agent, it can:
- Receive tasks
- Use tools
- Return results

## Create the Simplest Agent

```python
from loom.weave import create_agent, run

# Create Agent
agent = create_agent(
    name="Assistant",      # Agent name
    role="General Assistant" # Agent role description
)

# Run Task
result = run(agent, "Hello, please introduce yourself")
print(result)
```

## Understand the Code

1. **Import Module**: `loom.weave` provides simplified API
2. **create_agent()**: Create an Agent instance
3. **run()**: Run Agent synchronously (automatically handles async)

## Next Steps

→ [Tutorial 2: Adding Skills](adding-skills.md)
