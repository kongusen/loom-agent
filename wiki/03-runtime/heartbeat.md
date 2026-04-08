# Heartbeat (H_b)

Heartbeat is Loom's background sensing layer. It runs alongside the main execution loop and watches the environment for changes that may matter to the agent.

## Public Entry Point

Application developers configure heartbeat through `HeartbeatConfig` on `AgentConfig`:

```python
from loom import (
    AgentConfig,
    ModelRef,
    create_agent,
)
from loom.config import HeartbeatConfig, ResourceThresholds, WatchConfig

agent = create_agent(
    AgentConfig(
        model=ModelRef.anthropic("claude-sonnet-4"),
        heartbeat=HeartbeatConfig(
            watch_sources=[
                WatchConfig.resource(
                    thresholds=ResourceThresholds(memory_pct=90.0),
                )
            ],
        ),
    )
)
```

You normally do not instantiate `Heartbeat` directly from application code.

## What Heartbeat Monitors

| Source | Public config | Detects |
|---|---|---|
| Filesystem | `WatchConfig.filesystem(...)` | file changes |
| Process | `WatchConfig.process(...)` | process exit / PID changes |
| Resources | `WatchConfig.resource(...)` | CPU, memory, disk thresholds |
| Event bus | `WatchConfig.mf_events(...)` | event-topic activity |

## Urgency

Heartbeat events are classified by urgency and then projected into runtime state.

| Urgency | Effect |
|---|---|
| `low` | queued for later handling |
| `high` | can request interruption |
| `critical` | strongest interrupt signal |

## Internal Code

- `loom/runtime/heartbeat.py`
- `loom/runtime/monitors.py`
