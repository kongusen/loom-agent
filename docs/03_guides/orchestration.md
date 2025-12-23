# Orchestration

One agent is powerful; a swarm is unstoppable. Loom provides `CrewNode` and `AttentionRouter` to organize multiple agents.

## Sequential Crew (Pipeline)
Passes the output of one agent as the input to the next.

```python
from loom.node.crew import CrewNode

# Define Agents
researcher = AgentNode(..., role="Researcher")
writer = AgentNode(..., role="Writer")

# Create Crew
blog_crew = CrewNode(
    node_id="crew/blog_writer",
    dispatcher=app.dispatcher,
    agents=[researcher, writer],
    pattern="sequential"
)

# Run
await app.run(
    task="Research AI trends and write a blog post",
    target="crew/blog_writer"
)
```

## Attention Router (Dynamic)
Uses an LLM to decide which agent should handle a task.

```python
from loom.node.router import AttentionRouter

router = AttentionRouter(
    node_id="router/main",
    dispatcher=app.dispatcher,
    agents=[math_agent, poetry_agent],
    provider=my_llm
)

# If task is "Write a haiku", router sends to poetry_agent
await app.run("Write a haiku", target="router/main")
```
