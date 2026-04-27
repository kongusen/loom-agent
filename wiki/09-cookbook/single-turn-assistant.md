# Single-Turn Assistant

Use this pattern when each request is independent and you do not need cross-run memory.

## When To Use It

- chat-style helper endpoints
- repository summarization
- one-off analysis or classification
- draft generation with no follow-up state

## Shape

```python
from loom import Agent, Model, Runtime

agent = Agent(
    model=Model.anthropic("claude-sonnet-4"),
    instructions="You are a concise product assistant.",
    runtime=Runtime.sdk(),
)

result = await agent.run("Summarize the release notes")
print(result.output)
```

## Why This Is The Default

- the API stays minimal
- there is no session lifecycle to manage
- the request boundary is explicit

## What To Add Next

- add `Generation` when output style matters
- move to `Session` when later runs must remember earlier ones
- add `KnowledgeQuery` when answers must be grounded in explicit evidence
- add `Capability` when the agent needs files, web, shell, MCP, or skills

## Runnable Example

- [examples/01_hello_agent.py](https://github.com/kongusen/loom-agent/blob/main/examples/01_hello_agent.py)
- [examples/00_agent_overview.py](https://github.com/kongusen/loom-agent/blob/main/examples/00_agent_overview.py)
