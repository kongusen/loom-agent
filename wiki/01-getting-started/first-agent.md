# Your First Agent

## 1. Create An Agent

```python
from loom import AgentConfig, ModelRef, create_agent

agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions="Analyze repositories and summarize what matters.",
    )
)
```

## 2. Run It Once

```python
result = await agent.run("Analyze the README and summarize key features")

print(result.state)   # RunState.COMPLETED
print(result.output)  # model output
```

## 3. Use A Session For Continuity

```python
from loom import RunContext, SessionConfig

session = agent.session(SessionConfig(id="demo"))

first = await session.run("List three important features")
second = await session.run(
    "Summarize the previous answer in one sentence",
    context=RunContext(inputs={"previous_answer": first.output}),
)
```

## 4. Stream Events

```python
run = session.start("Inspect the project layout")

async for event in run.events():
    print(event.type, event.payload)

result = await run.wait()
```

## 5. Attach Knowledge

```python
from loom import KnowledgeQuery, RunContext

knowledge = agent.resolve_knowledge(
    KnowledgeQuery(
        text="What are the deployment rules?",
        goal="Summarize deployment policy",
        top_k=3,
    )
)

result = await agent.run(
    "Summarize deployment policy",
    context=RunContext(knowledge=knowledge),
)
```

## Next

- [API Reference](../07-api-reference/README.md)
- [Core Concepts](../02-core-concepts/README.md)
- [Architecture](../Architecture.md)
