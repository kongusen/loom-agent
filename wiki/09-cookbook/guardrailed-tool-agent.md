# Guardrailed Tool Agent

Use this pattern when the agent can call tools and some actions must be constrained.

## When To Use It

- file and shell tools
- internal ops assistants
- admin workflows
- any tool-enabled app with side effects

## Shape

```python
from loom import Agent, Files, Model, Runtime, Shell, tool


@tool(description="Read deployment status", read_only=True)
async def deployment_status(service: str) -> str:
    return f"{service}: healthy"


agent = Agent(
    model=Model.anthropic("claude-sonnet-4"),
    instructions="Help with repository and deployment maintenance.",
    tools=[deployment_status],
    capabilities=[
        Files(read_only=True),
        Shell.approval_required(),
    ],
    runtime=Runtime.supervised(criteria=["no destructive action without approval"]),
)
```

## Design Rule

Use capabilities for what the agent can reach and runtime governance for how those abilities are constrained.

In practice:

- `Files(read_only=True)` is the default for analysis
- `Shell.approval_required()` keeps shell access explicit
- `Runtime.supervised(...)` adds a quality and approval-oriented runtime profile
- custom safety rules and advanced policy objects remain available through `loom.config`

## What To Add Next

- use `GovernancePolicy` directly when the app needs custom approval or rate-limit behavior
- add `SignalAdapter` when tool work is triggered by gateway, cron, heartbeat, or webhook events

## Runnable Example

- [examples/12_heartbeat_and_safety.py](https://github.com/kongusen/loom-agent/blob/main/examples/12_heartbeat_and_safety.py)
- [examples/15_approval_workflow.py](https://github.com/kongusen/loom-agent/blob/main/examples/15_approval_workflow.py)
