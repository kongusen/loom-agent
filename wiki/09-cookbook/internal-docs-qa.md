# Internal Docs QA

Use this pattern when the app answers questions over internal policies, docs, or product notes.

## What The App Usually Needs

- grounded answers
- explicit retrieval boundaries
- evidence or citation display in the UI
- predictable behavior across repeated questions

## Shape

```python
from loom import (
    Agent,
    KnowledgeDocument,
    KnowledgeQuery,
    KnowledgeSource,
    Model,
    RunContext,
    Runtime,
)

agent = Agent(
    model=Model.anthropic("claude-sonnet-4"),
    instructions="Answer internal documentation questions from the supplied evidence.",
    knowledge=[
        KnowledgeSource.inline(
            "handbook",
            [
                KnowledgeDocument(
                    title="On-call Policy",
                    content="Primary on-call engineers must acknowledge incidents within 10 minutes.",
                ),
                KnowledgeDocument(
                    title="Deploy Policy",
                    content="Production deploys require approval from the release owner.",
                ),
            ],
        )
    ],
    runtime=Runtime.sdk(),
)

knowledge = agent.resolve_knowledge(
    KnowledgeQuery(
        text="Who can approve a production deploy?",
        goal="Answer deploy approval question",
        top_k=3,
    )
)

result = await agent.run(
    "Answer the user question using the retrieved documentation",
    context=RunContext(
        inputs={"user_question": "Who can approve a production deploy?"},
        knowledge=knowledge,
    ),
)
```

## Design Rule

Keep what to retrieve separate from how to answer.

That makes the app easier to inspect:

- retrieval is visible in `KnowledgeQuery`
- evidence is visible in `KnowledgeBundle`
- response behavior is controlled by the agent instructions and runtime profile

## Good Defaults

- keep document sources named and stable
- preserve citations if the UI shows evidence
- avoid hiding the user question inside only the prompt string

## Related Patterns

- [Knowledge-Backed Answers](knowledge-backed-answers.md)

## Runnable Example

- [examples/14_internal_docs_qa.py](https://github.com/kongusen/loom-agent/blob/main/examples/14_internal_docs_qa.py)
- [examples/00_agent_overview.py](https://github.com/kongusen/loom-agent/blob/main/examples/00_agent_overview.py)
