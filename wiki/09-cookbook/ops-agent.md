# Ops Agent

Use this pattern when the app watches system state and recommends or performs operational actions.

## What The App Usually Needs

- signal-based observation
- strong action constraints
- explicit separation between monitoring and remediation
- session continuity for incident handling

## Shape

```python
from loom import Agent, Model, Runtime, RuntimeSignal, SessionConfig, Shell, tool


@tool(description="Restart a service")
async def restart_service(name: str) -> str:
    return f"Restarted {name}"


agent = Agent(
    model=Model.anthropic("claude-sonnet-4"),
    instructions="Monitor operational state and propose safe remediations.",
    tools=[restart_service],
    capabilities=[
        Shell.approval_required(),
    ],
    runtime=Runtime.supervised(criteria=["critical services require approval"]),
)

incident = agent.session(SessionConfig(id="incident-2026-04-27"))

await incident.receive(
    RuntimeSignal.create(
        "Memory usage exceeded 90%",
        source="heartbeat",
        type="alert",
        urgency="high",
        payload={"service": "api"},
    )
)

result = await incident.run("Assess system health and recommend the next action")
```

## Design Rule

Ops agents should be constrained by runtime policy, not only by prompt wording.

In practice:

- heartbeat/gateway/cron events become `RuntimeSignal`
- capability declarations define what the agent can reach
- governance and supervised runtime profiles define the hard stops
- approvals should enter through `RunContext` or external application state

## Good Defaults

- keep critical actions vetoable
- use sessions per incident or per environment
- start in recommendation mode before enabling remediation
- keep shell access approval-gated

## Related Patterns

- [Monitoring Agent](monitoring-agent.md)
- [Guardrailed Tool Agent](guardrailed-tool-agent.md)

## Runnable Example

- [examples/12_heartbeat_and_safety.py](https://github.com/kongusen/loom-agent/blob/main/examples/12_heartbeat_and_safety.py)
- [examples/16_signal_adapters.py](https://github.com/kongusen/loom-agent/blob/main/examples/16_signal_adapters.py)
