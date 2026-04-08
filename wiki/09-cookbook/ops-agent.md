# Ops Agent

Use this pattern when the app watches system state and recommends or performs operational actions.

## What The App Usually Needs

- heartbeat-based observation
- strong action constraints
- explicit separation between monitoring and remediation
- session continuity for incident handling

## Shape

```python
from loom import AgentConfig, ModelRef, SessionConfig, create_agent, tool
from loom.config import (
    HeartbeatConfig,
    ResourceThresholds,
    SafetyRule,
    ToolAccessPolicy,
    ToolPolicy,
    WatchConfig,
    PolicyConfig,
)


@tool(description="Restart a service")
async def restart_service(name: str) -> str:
    return f"Restarted {name}"


agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions="Monitor operational state and propose safe remediations.",
        tools=[restart_service],
        policy=PolicyConfig(
            tools=ToolPolicy(
                access=ToolAccessPolicy(
                    allow=["restart_service"],
                    allow_destructive=False,
                )
            )
        ),
        heartbeat=HeartbeatConfig(
            watch_sources=[
                WatchConfig.resource(
                    thresholds=ResourceThresholds(cpu_pct=85.0, memory_pct=90.0),
                )
            ]
        ),
        safety_rules=[
            SafetyRule.when_argument_contains_any(
                name="protect-critical-services",
                tool_name="restart_service",
                argument="name",
                values=["database", "auth-service"],
                reason="Critical services require manual approval.",
            )
        ],
    )
)

incident = agent.session(SessionConfig(id="incident-2026-04-08"))
result = await incident.run("Assess system health and recommend the next action")
```

## Design Rule

Ops agents should be constrained by configuration, not only by prompt wording.

In practice:

- heartbeat defines what the agent notices
- policy defines broad tool permissions
- safety rules define the hard stop conditions

## Good Defaults

- keep critical actions vetoable
- use sessions per incident or per environment
- start in recommendation mode before enabling remediation

## Related Patterns

- [Monitoring Agent](monitoring-agent.md)
- [Guardrailed Tool Agent](guardrailed-tool-agent.md)

## Runnable Example

- [examples/12_heartbeat_and_safety.py](https://github.com/kongusen/loom-agent/blob/main/examples/12_heartbeat_and_safety.py)
