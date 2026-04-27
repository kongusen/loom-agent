# Repo Copilot

Use this pattern when the agent acts as a coding or repository assistant for one codebase.

## What The App Usually Needs

- continuity across follow-up questions
- repository-specific instructions
- read-only file and web capabilities by default
- optional grounded knowledge from local docs

## Shape

```python
from loom import Agent, Capability, Model, RunContext, Runtime, SessionConfig

agent = Agent(
    model=Model.anthropic("claude-sonnet-4"),
    instructions=(
        "You are a repository copilot. "
        "Prefer concrete, code-aware answers and keep changes scoped."
    ),
    capabilities=[
        Capability.files(read_only=True),
        Capability.web(),
    ],
    runtime=Runtime.long_running(criteria=["answers are grounded in repository evidence"]),
)

session = agent.session(SessionConfig(id="repo-user-123"))

first = await session.run("Summarize the current package layout")
second = await session.run(
    "Which API boundaries still look too wide?",
    context=RunContext(inputs={"previous_summary": first.output}),
)
```

## Design Rule

For repo copilots, keep the agent stable and the session long-lived.

That usually means:

- repository identity belongs in instructions or session metadata
- current question-specific facts belong in `RunContext`
- broad permissions belong in `Capability`
- runtime behavior belongs in `Runtime`

## Good Defaults

- start read-only
- add shell/write-capable capabilities only for explicit editing workflows
- prefer session continuity over rebuilding the agent each turn

## Related Patterns

- [Session Workflow](session-workflow.md)
- [Guardrailed Tool Agent](guardrailed-tool-agent.md)

## Runnable Example

- [examples/13_repo_copilot.py](https://github.com/kongusen/loom-agent/blob/main/examples/13_repo_copilot.py)
- [examples/04_multi_task_session.py](https://github.com/kongusen/loom-agent/blob/main/examples/04_multi_task_session.py)
