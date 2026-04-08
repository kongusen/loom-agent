# Approval Workflow

Use this pattern when the agent prepares or checks an action, but a human or external system must approve the final step.

## What The App Usually Needs

- structured multi-step flow
- continuity across requests
- explicit approval boundary
- tool and safety configuration that reflects the workflow stages

## Shape

```python
from loom import AgentConfig, ModelRef, RunContext, SessionConfig, create_agent

agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions=(
            "Prepare operational changes, summarize risk, "
            "and wait for explicit approval before irreversible actions."
        ),
    )
)

session = agent.session(SessionConfig(id="deploy-request-42"))

draft = await session.run("Prepare a production deployment plan for version 2.3.0")

review = await session.run(
    "Summarize risks and list the required approval step",
    context=RunContext(inputs={"draft_plan": draft.output}),
)

approved = await session.run(
    "Produce the final approved action summary",
    context=RunContext(
        inputs={
            "draft_plan": draft.output,
            "review_summary": review.output,
            "approval_state": "approved",
            "approved_by": "release-owner",
        }
    ),
)
```

## Design Rule

Treat approval as explicit runtime input, not an implicit assumption.

That keeps the workflow auditable:

- preparation happens in earlier runs
- approval state is passed explicitly
- the application can decide whether to unlock downstream tools

## Good Defaults

- keep approval state in `RunContext.inputs`
- create one session per approval object or request
- attach knowledge if the approval depends on policy documents

## Related Patterns

- [Session Workflow](session-workflow.md)
- [Internal Docs QA](internal-docs-qa.md)

## Runnable Example

- [examples/15_approval_workflow.py](https://github.com/kongusen/loom-agent/blob/main/examples/15_approval_workflow.py)
- [examples/04_multi_task_session.py](https://github.com/kongusen/loom-agent/blob/main/examples/04_multi_task_session.py)
