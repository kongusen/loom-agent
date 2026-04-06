# Execution Loop (L*)

L* is the agent's main execution engine. It runs until the goal is reached, context is full, or the Harness intervenes.

## The Four Phases

```
┌─────────────────────────────────────────────┐
│  L* = (Reason → Act → Observe → Δ)*        │
└─────────────────────────────────────────────┘
```

| Phase | What happens |
|---|---|
| **Reason** | Model reads context, updates plan, decides next action |
| **Act** | Tool calls execute; H_b continues sensing in parallel |
| **Observe** | Results enter context; ρ is recalculated |
| **Δ (Delta)** | Model decides: continue / goal_reached / renew / decompose / harness |

## State Machine

```
PENDING → RUNNING → COMPLETED
                 ↘ PAUSED → RUNNING
                 ↘ FAILED
                 ↘ CANCELLED
```

## Δ Decisions

| Decision | Trigger | Effect |
|---|---|---|
| `continue` | More steps needed | Next L* iteration |
| `goal_reached` | Task complete | Emit `run.completed` |
| `renew` | ρ ≥ 1.0 | Snapshot → compress → rebuild context |
| `decompose` | Task too large | Spawn sub-agents via `SubAgentManager` |
| `harness` | Safety violation | VetoAuthority blocks the action |

## Configuration

```python
from loom.runtime.loop import LoopConfig

config = LoopConfig(
    max_steps=50,
    timeout=300.0,
    renewal_threshold=0.95,
)
```

**Code:** `loom/runtime/loop.py`
