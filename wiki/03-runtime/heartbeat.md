# Heartbeat (H_b)

Heartbeat is Loom's background sensing layer. In the `0.8.x` runtime language, heartbeat output should be treated as runtime signal input.

## Public Entry Point

Application developers normally model heartbeat events as `RuntimeSignal` objects, either directly or through a `SignalAdapter`:

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
        "Memory usage exceeded 90%",
        source="heartbeat",
        type="alert",
        urgency="high",
        payload={"host": "api-1"},
    )
)
```

Advanced users can still configure internal heartbeat monitors through `HeartbeatConfig` from `loom.config`, but the kernel-level contract remains `RuntimeSignal`.

## What Heartbeat Monitors Can Emit

| Source | Detects | Runtime signal shape |
|---|---|---|
| Filesystem | file changes | `source="heartbeat"`, `type="filesystem"` |
| Process | process exit / PID changes | `source="heartbeat"`, `type="process"` |
| Resources | CPU, memory, disk thresholds | `source="heartbeat"`, `type="resource"` |
| Event bus | event-topic activity | `source="heartbeat"`, `type="event"` |

## Urgency

Heartbeat events are classified by urgency and projected into runtime state.

| Urgency | Effect |
|---|---|
| `low` | observed or queued |
| `normal` | run-worthy pending work |
| `high` | can request interruption |
| `critical` | strongest interrupt request |

## Internal Code

- `loom/runtime/heartbeat.py`
- `loom/runtime/monitors.py`
- `loom/runtime/signals.py`
