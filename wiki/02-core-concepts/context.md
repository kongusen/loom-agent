# Context Management

Context is the agent's **only perception interface**. Everything the model knows about the current task comes from the context window.

## Five Partitions

```
C = C_system ⊕ C_memory ⊕ C_skill ⊕ C_history ⊕ C_working
```

| Partition | Purpose | Compressed? |
|---|---|---|
| `C_system` | Harness-injected instructions | Never |
| `C_working` | Dashboard, plan, events, scratchpad | Never |
| `C_memory` | AGENTS.md, persistent notes | Rarely |
| `C_skill` | Active skill/tool declarations | Swapped on demand |
| `C_history` | Execution history | Yes — first to go |

Protection priority: `C_system > C_working > C_memory > C_skill > C_history`

## C_working — The Decision Interface

`C_working` is not a log. It's the model's working memory:

```python
C_working = {
    "dashboard": {
        "rho":                  # context pressure (0.0–1.0)
        "token_budget":         # remaining budget
        "goal_progress":        # model's self-assessment
        "error_count":          # recent errors
        "depth":                # sub-agent recursion depth
        "last_hb_ts":           # last heartbeat timestamp
        "interrupt_requested":  # H_b interrupt flag
    },
    "plan":            [...],   # current task plan
    "event_surface":   {...},   # pending events, active risks
    "knowledge_surface": {...}, # active questions, evidence packs
    "scratchpad":      "...",   # short-term reasoning
}
```

## Five Compression Levels

Triggered by context pressure `ρ`, one level per turn:

| Level | Trigger | Strategy |
|---|---|---|
| Snip | ρ > 0.7 | Truncate messages over 2000 chars |
| Micro | ρ > 0.8 | Deduplicate tool results by call ID |
| Collapse | ρ > 0.9 | Extractive summary of middle messages |
| Auto | ρ > 0.95 | Score-based keep: K·rel·e^(−λ·age) |
| Reactive | API 413 | Emergency: auto + snip at 500 chars |

## Context Renewal (Disk Paging)

When `ρ ≥ 1.0`, Loom snapshots `C_working` to `M_f` (filesystem), compresses history, and rebuilds a fresh context window. The agent continues without losing its working state.

**Code:** `loom/context/`
