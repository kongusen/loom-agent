# Knowledge-Backed Answers

Use this pattern when the answer must be grounded in explicit evidence rather than only the base model.

## When To Use It

- policy and compliance questions
- internal documentation assistants
- product knowledge assistants
- any answer that should carry a stable retrieval boundary

## Shape

```python
from loom import (
    AgentConfig,
    KnowledgeDocument,
    KnowledgeQuery,
    KnowledgeSource,
    ModelRef,
    RunContext,
    create_agent,
)

agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions="Answer only from the supplied knowledge.",
        knowledge=[
            KnowledgeSource.inline(
                "policy-docs",
                [
                    KnowledgeDocument(
                        title="Deployment",
                        content="Production changes require approval from the release owner.",
                    )
                ],
            )
        ],
    )
)

knowledge = agent.resolve_knowledge(
    KnowledgeQuery(
        text="Who approves production changes?",
        goal="Summarize deployment approval policy",
        top_k=3,
    )
)

result = await agent.run(
    "Answer the deployment approval question",
    context=RunContext(knowledge=knowledge),
)
```

## Design Rule

Keep retrieval and execution as two explicit steps:

```text
KnowledgeQuery -> KnowledgeBundle -> RunContext
```

That makes the knowledge boundary inspectable even before deeper retrieval internals are fully wired.

## What To Add Next

- use `KnowledgeSource.dynamic(...)` for external retrieval adapters
- keep citations in the bundle when downstream UX needs evidence display

## Runnable Example

- [examples/00_agent_overview.py](https://github.com/kongusen/loom-agent/blob/main/examples/00_agent_overview.py)
