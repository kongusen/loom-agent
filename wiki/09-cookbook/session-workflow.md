# Session Workflow

Use this pattern when later runs need continuity from earlier runs.

## When To Use It

- multi-step product flows
- coding copilots with follow-up questions
- iterative planning and refinement
- user-specific assistant sessions

## Shape

```python
from loom import AgentConfig, ModelRef, RunContext, SessionConfig, create_agent

agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions="You help users refine API designs across multiple turns.",
    )
)

session = agent.session(SessionConfig(id="user-123"))

first = await session.run("List three options for versioning an API")
second = await session.run(
    "Recommend one option for a startup team",
    context=RunContext(inputs={"previous_answer": first.output}),
)
```

## Design Rule

Use `Session` for continuity and `RunContext` for explicit per-run inputs.

That split keeps the contract clear:

- session state is long-lived
- `RunContext` is request-scoped

## What To Avoid

- putting all transient inputs into session metadata
- creating a new agent for every follow-up turn when only the session changed

## What To Add Next

- add `MemoryConfig` when you want explicit memory behavior
- add `KnowledgeBundle` in `RunContext` when grounding is needed on one run

## Runnable Example

- [examples/04_multi_task_session.py](https://github.com/kongusen/loom-agent/blob/main/examples/04_multi_task_session.py)
- [examples/03_events_and_artifacts.py](https://github.com/kongusen/loom-agent/blob/main/examples/03_events_and_artifacts.py)
