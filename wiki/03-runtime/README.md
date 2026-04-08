# Runtime

The runtime is the internal execution layer behind the public `Agent` API.

For application developers, the public path is still:

```text
AgentConfig -> Agent -> Session -> Run
```

This section explains the internals that power that path.

## Two Parallel Systems

```text
┌─────────────────────────────────────┐
│  L* Loop (main execution path)      │
│  Reason -> Act -> Observe -> Delta  │
└──────────────────┬──────────────────┘
                   │ shares context
┌──────────────────▼──────────────────┐
│  H_b Heartbeat (background sensing) │
│  Filesystem · Process · Resources   │
└─────────────────────────────────────┘
```

- `L*` drives one run toward completion.
- `H_b` watches the environment in parallel.
- `Agent` adapts public config objects into these runtime components.

## Public Runtime Mapping

| Public object | Runtime layer behind it |
|---|---|
| `Agent.run()` | `AgentEngine.execute(...)` |
| `Session` | run lifecycle and engine reuse |
| `RunContext` | prompt/runtime context payload |
| `HeartbeatConfig` | runtime heartbeat assembly |
| `RuntimeConfig` | engine limits, features, fallback |

## Pages

- [Execution Loop (L*)](loop.md)
- [Heartbeat (H_b)](heartbeat.md)

## Code

- `loom/runtime/engine.py`
- `loom/runtime/session.py`
- `loom/runtime/loop.py`
- `loom/runtime/heartbeat.py`
