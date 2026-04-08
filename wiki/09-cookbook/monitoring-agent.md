# Monitoring Agent

Use this pattern when the agent should respond to changing system state, not only static prompts.

## When To Use It

- service monitoring assistants
- codebase watchers
- runtime health agents
- agents that must combine observation with guarded actions

## Shape

```python
from loom import AgentConfig, ModelRef, create_agent
from loom.config import (
    FilesystemWatchMethod,
    HeartbeatConfig,
    ResourceThresholds,
    SafetyRule,
    WatchConfig,
)

agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        instructions="Monitor the system and recommend safe next steps.",
        heartbeat=HeartbeatConfig(
            interval=5.0,
            watch_sources=[
                WatchConfig.filesystem(
                    paths=["./src", "./config"],
                    method=FilesystemWatchMethod.HASH,
                ),
                WatchConfig.resource(
                    thresholds=ResourceThresholds(cpu_pct=85.0, memory_pct=90.0),
                ),
            ],
        ),
        safety_rules=[
            SafetyRule.when_argument_contains_any(
                name="no_force_restart",
                tool_name="restart_service",
                argument="name",
                values=["database", "auth-service"],
                reason="Critical services require manual approval.",
            )
        ],
    )
)
```

## Design Rule

Heartbeat belongs in configuration, not in the prompt.

That keeps environment sensing stable and inspectable:

- watch sources live in `HeartbeatConfig`
- interrupt behavior lives in `HeartbeatInterruptPolicy`
- action boundaries still live in `SafetyRule`

## What To Add Next

- combine with `Session` if monitoring spans multiple user interactions
- combine with tools when the agent must inspect or remediate

## Runnable Example

- [examples/12_heartbeat_and_safety.py](https://github.com/kongusen/loom-agent/blob/main/examples/12_heartbeat_and_safety.py)
