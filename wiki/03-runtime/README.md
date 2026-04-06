# Runtime

The runtime is the execution engine of every Loom agent.

## Two Parallel Systems

```
┌─────────────────────────────────────┐
│  L* Loop (main thread)              │
│  Reason → Act → Observe → Δ        │
└──────────────────┬──────────────────┘
                   │ shares context
┌──────────────────▼──────────────────┐
│  H_b Heartbeat (background thread)  │
│  Filesystem · Process · Resources   │
└─────────────────────────────────────┘
```

L* drives the task. H_b watches the world. When H_b detects something important, it injects an event into `C_working.event_surface` and can set `interrupt_requested = True`.

## Pages

- [Execution Loop (L*)](loop.md)
- [Heartbeat (H_b)](heartbeat.md)

**Code:** `loom/runtime/`
