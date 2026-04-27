# Multi-Agent Orchestration

Loom includes orchestration modules for planning and coordination, but these sit below the main public `Agent` API.

Use this section when you are extending Loom or building advanced orchestration flows on top of the runtime.

## Position In The Stack

```text
Agent + Runtime + Capability -> Session/Run
                              -> orchestration modules when advanced coordination is needed
```

## Core Pieces

```text
Coordinator
    │
    ├── TaskPlanner
    │
    └── SubAgentManager / worker managers
```

## What This Section Covers

- `TaskPlanner`: break one goal into dependent tasks
- `Coordinator`: execute a plan with timeout and aggregation
- `SubAgentManager`: spawn bounded child work

## Hard Constraints

- `d_max`: maximum recursion depth
- `rho`: each child flow still manages its own context pressure

## Pages

- [Task Planning](planning.md)
- [Coordination](coordination.md)

## Code

- `loom/orchestration/planner.py`
- `loom/orchestration/coordinator.py`
- `loom/orchestration/subagent.py`
