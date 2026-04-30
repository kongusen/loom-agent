# Execution Loop (L*)

L* is Loom's internal execution loop. It is the engine behind `Agent.run()`, `Session.run()`, and `Run.wait()`.

## Phases

```text
L* = (Reason -> Act -> Observe -> Delta)*
```

| Phase | What happens |
|---|---|
| `Reason` | build messages, call the model, interpret next step |
| `Act` | execute tool calls and safety checks |
| `Observe` | feed results back into runtime context |
| `Delta` | decide whether to continue, renew, or finish |

## Public Mapping

| Public API | Internal loop effect |
|---|---|
| `agent.run(...)` | starts one L* execution |
| `session.run(...)` | starts one L* execution with session reuse |
| `run.events()` | streams runtime events emitted during L* |
| `RunResult` | materialized output after L* exits |

## Related Config

L* behavior is controlled indirectly through:

- `RuntimeConfig.limits`
- `RuntimeConfig.features`
- `Generation`
- `HeartbeatConfig`
- `SafetyRule`

## Internal Code

- `loom/runtime/loop.py`
- `loom/runtime/engine.py`
