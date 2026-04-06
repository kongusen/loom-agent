# Heartbeat (H_b)

H_b is an independent background thread that runs **parallel to L***. It solves the "waiting blind spot" — when the agent is blocked waiting for a shell command, network call, or sub-agent, H_b keeps sensing the world.

## What H_b Monitors

| Source | Class | Detects |
|---|---|---|
| Filesystem | `FilesystemMonitor` | File hash changes |
| Process | `ProcessMonitor` | Process exit |
| Resources | `ResourceMonitor` | CPU/memory/disk thresholds |
| Event bus | `MFEventsMonitor` | Topic subscriptions |

## Urgency Classification

H_b classifies each event by `delta_H` entropy:

| Urgency | Effect on C_working |
|---|---|
| `low` | Added to `pending_events` |
| `medium` | Added to `pending_events` |
| `high` | Added to `active_risks`, sets `interrupt_requested = True` |
| `critical` | Same as high, immediate interrupt |

## Usage

```python
from loom.runtime.heartbeat import Heartbeat
from loom.runtime.monitors import FilesystemMonitor

hb = Heartbeat(interval=5.0)
hb.add_source(FilesystemMonitor(paths=["./src"], delta_h=0.3))
hb.start(event_callback=lambda event, urgency: ...)
# ... agent runs ...
hb.stop()
```

**Code:** `loom/runtime/heartbeat.py`, `loom/runtime/monitors.py`
