# Runtime

The runtime is the execution layer behind the public `Agent` SDK.

For application developers, the public path is:

```text
Agent + Runtime + Capability
    -> Session / Run
    -> RuntimeTask / RuntimeSignal
```

This section explains the internals that power that path.

## Runtime Kernel

```text
┌────────────────────────────────────────────┐
│ Agent                                      │
│  model + instructions + tools/capabilities │
└──────────────────────┬─────────────────────┘
                       │
┌──────────────────────▼─────────────────────┐
│ Runtime policies                            │
│ context · continuity · harness · quality    │
│ delegation · governance · feedback          │
└──────────────────────┬─────────────────────┘
                       │
┌──────────────────────▼─────────────────────┐
│ Run / Session                               │
│ L* loop + provider + tools + persistence    │
└────────────────────────────────────────────┘
```

External producers do not become separate kernel features:

```text
gateway / cron / heartbeat / webhook / app callback
    -> SignalAdapter
    -> RuntimeSignal
    -> AttentionPolicy
    -> optional Agent run
```

## Main Runtime Objects

| Public object | Runtime layer behind it |
|---|---|
| `Agent.run()` | `AgentEngine.execute(...)` |
| `Agent.receive()` | signal adapter + session signal queue |
| `Session` | run lifecycle and engine reuse |
| `RunContext` | prompt/runtime context payload |
| `RuntimeTask` | structured task request |
| `RuntimeSignal` | normalized external event |
| `Runtime` | engine limits, features, and policy composition |
| `Capability` | ability source compiled into governed tools |

## Runtime Policies

| Policy | Responsibility |
|---|---|
| `AttentionPolicy` | Decide whether a signal should observe, run, or interrupt |
| `ContextProtocol` | Context partitioning, render, compact, renew, snapshot |
| `ContinuityPolicy` | Preserve work across compaction/reset |
| `Harness` | Long-task execution strategy |
| `QualityGate` | Acceptance criteria and PASS/FAIL evaluation |
| `DelegationPolicy` | Subtask and sub-agent dispatch boundary |
| `GovernancePolicy` | Tool permissions, veto, rate limits, read-only/destructive checks |
| `FeedbackPolicy` | Runtime feedback for dashboards and evolution |
| `SessionRestorePolicy` | Restore transcript/runtime state into later runs |
| `SkillInjectionPolicy` | Inject matching skill content into runtime context |

## Pages

- [Execution Loop (L*)](loop.md)
- [Heartbeat (H_b)](heartbeat.md)

## Code

- `loom/runtime/engine.py`
- `loom/runtime/session.py`
- `loom/runtime/signals.py`
- `loom/runtime/capability.py`
- `loom/runtime/governance.py`
- `loom/runtime/context.py`
- `loom/runtime/heartbeat.py`
