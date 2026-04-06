# Core Concepts

Loom models every agent as six cooperating components:

```
Agent = ⟨C, M, L*, H_b, S, Ψ⟩
```

| Component | Role |
|-----------|------|
| [Context (C)](context.md) | The agent's only perception interface |
| [Memory (M)](memory.md) | Four-layer memory system |
| [Loop (L*)](../03-runtime/loop.md) | Reason → Act → Observe → Δ execution engine |
| [Heartbeat (H_b)](../03-runtime/heartbeat.md) | Background sensing, parallel to L* |
| [Skills (S)](../05-ecosystem/skills.md) | Progressively loaded tools and capabilities |
| [Harness (Ψ)](safety.md) | Safety, permissions, and veto authority |

## The Key Insight

The model only sees what's in the context window. Loom's job is to make that window as useful as possible — structured, compressed, and always decision-ready — without replacing the model's judgment.

> **Harness is the stage, not the actor.**  
> The model decides. The Harness sets boundaries.

## Hard Constraints

Two physical constraints are always enforced regardless of what the model wants:

| Constraint | Meaning | Where |
|---|---|---|
| `ρ = 1.0` | Context pressure limit — triggers renewal when full | `loom/context/manager.py` |
| `d_max` | Max sub-agent recursion depth | `loom/orchestration/subagent.py` |
