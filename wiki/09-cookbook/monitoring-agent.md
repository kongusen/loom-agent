# Monitoring Agent

Use this pattern when the agent should respond to changing system state, not only static prompts.

## When To Use It

- service monitoring assistants
- codebase watchers
- runtime health agents
- agents that combine observation with guarded actions

## Shape

```python
from loom import Agent, Model, Runtime, RuntimeSignal, SessionConfig

agent = Agent(
    model=Model.anthropic("claude-sonnet-4"),
    instructions="Monitor the system and recommend safe next steps.",
    runtime=Runtime.long_running(criteria=["recommendations are safe and actionable"]),
)

session = agent.session(SessionConfig(id="ops"))

await session.receive(
    RuntimeSignal.create(
        "CPU usage exceeded 90%",
        source="heartbeat",
        type="alert",
        urgency="high",
        payload={"host": "api-1"},
    )
)

result = await session.run("Assess pending runtime signals")
```

## Design Rule

Monitoring enters the runtime as signal input.

That keeps the kernel simple:

- heartbeat adapters emit `RuntimeSignal`
- gateway and cron adapters emit the same contract
- `AttentionPolicy` decides whether a signal should cause execution
- tools and remediation still go through user-facing ability declarations and `GovernancePolicy`

## What To Add Next

- combine with `SignalAdapter` for real heartbeat, webhook, or gateway event shapes
- combine with `Shell.approval_required()` when remediation is allowed
- use `Runtime.supervised(...)` when human review is required

## Runnable Example

- [examples/12_heartbeat_and_safety.py](https://github.com/kongusen/loom-agent/blob/main/examples/12_heartbeat_and_safety.py)
- [examples/16_signal_adapters.py](https://github.com/kongusen/loom-agent/blob/main/examples/16_signal_adapters.py)
