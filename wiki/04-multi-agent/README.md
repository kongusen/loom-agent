# Multi-Agent Orchestration

Loom supports spawning and coordinating multiple agents to tackle complex tasks in parallel.

## How It Works

```
Coordinator
    │
    ├── TaskPlanner  (dependency graph)
    │
    └── SubAgentManager × N
            │
            └── spawn(goal, depth+1)
```

## Pages

- [Task Planning](planning.md)
- [Coordination](coordination.md)

## Hard Constraints

- `d_max`: maximum recursion depth — sub-agents cannot spawn indefinitely
- `ρ = 1.0`: each sub-agent manages its own context pressure independently

**Code:** `loom/orchestration/`
