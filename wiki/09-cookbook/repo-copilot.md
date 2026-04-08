# Repo Copilot

Use this pattern when the agent acts as a coding or repository assistant for one codebase.

## What The App Usually Needs

- continuity across follow-up questions
- repository-specific instructions
- optional read-only tools
- optional grounded knowledge from local docs

## Shape

```python
from loom import AgentConfig, ModelRef, RunContext, SessionConfig, create_agent, tool
from loom.config import PolicyConfig, PolicyContext, ToolAccessPolicy, ToolPolicy


@tool(description="Read repository files", read_only=True)
async def read_file(path: str) -> str:
    return f"Read: {path}"


agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions=(
            "You are a repository copilot. "
            "Prefer concrete, code-aware answers and keep changes scoped."
        ),
        tools=[read_file],
        policy=PolicyConfig(
            tools=ToolPolicy(
                access=ToolAccessPolicy(
                    allow=["read_file"],
                    read_only_only=True,
                )
            ),
            context=PolicyContext.named("repo"),
        ),
    )
)

session = agent.session(SessionConfig(id="repo-user-123"))

first = await session.run("Summarize the current package layout")
second = await session.run(
    "Which API seams still look too wide?",
    context=RunContext(inputs={"previous_summary": first.output}),
)
```

## Design Rule

For repo copilots, keep the agent stable and the session long-lived.

That usually means:

- repository identity belongs in instructions or session metadata
- current question-specific facts belong in `RunContext`
- broad permissions belong in `PolicyConfig`

## Good Defaults

- start read-only
- add write-capable tools only for explicit editing workflows
- prefer session continuity over rebuilding the agent each turn

## Related Patterns

- [Session Workflow](session-workflow.md)
- [Guardrailed Tool Agent](guardrailed-tool-agent.md)

## Runnable Example

- [examples/13_repo_copilot.py](https://github.com/kongusen/loom-agent/blob/main/examples/13_repo_copilot.py)
- [examples/04_multi_task_session.py](https://github.com/kongusen/loom-agent/blob/main/examples/04_multi_task_session.py)
