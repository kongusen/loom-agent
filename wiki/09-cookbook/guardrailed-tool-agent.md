# Guardrailed Tool Agent

Use this pattern when the agent can call tools and some actions must be constrained.

## When To Use It

- file and shell tools
- internal ops assistants
- admin workflows
- any tool-enabled app with side effects

## Shape

```python
from loom import AgentConfig, ModelRef, create_agent, tool
from loom.config import (
    PolicyConfig,
    PolicyContext,
    SafetyRule,
    ToolAccessPolicy,
    ToolPolicy,
    ToolRateLimitPolicy,
)


@tool(description="Read a file", read_only=True)
async def read_file(path: str) -> str:
    return f"Read {path}"


@tool(description="Delete a file")
async def delete_file(path: str) -> str:
    return f"Deleted {path}"


agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions="Help with repository maintenance.",
        tools=[read_file, delete_file],
        policy=PolicyConfig(
            tools=ToolPolicy(
                access=ToolAccessPolicy(
                    allow=["read_file", "delete_file"],
                    allow_destructive=False,
                ),
                rate_limits=ToolRateLimitPolicy(max_calls_per_minute=30),
            ),
            context=PolicyContext.named("repo"),
        ),
        safety_rules=[
            SafetyRule.block_tool(
                name="no_delete",
                tool_names=["delete_file"],
                reason="Deletion is blocked in this app.",
            )
        ],
    )
)
```

## Design Rule

Use both layers:

- `PolicyConfig` defines broad governance
- `SafetyRule` defines explicit veto boundaries

That split scales better than pushing all restrictions into one giant config object.

## What To Add Next

- use `read_only_only=True` for browse/analyze modes
- add custom `SafetyEvaluator` when rules depend on business conditions

## Runnable Example

- [examples/12_heartbeat_and_safety.py](https://github.com/kongusen/loom-agent/blob/main/examples/12_heartbeat_and_safety.py)
- [examples/00_agent_overview.py](https://github.com/kongusen/loom-agent/blob/main/examples/00_agent_overview.py)
