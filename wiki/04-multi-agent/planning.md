# Task Planning

`TaskPlanner` breaks a goal into a dependency-ordered task graph.

This is an advanced orchestration primitive, not the primary public application entry point. Most application developers should start with `Agent.run()` or `Session.run()`.

## Usage

```python
from loom.orchestration.planner import TaskPlanner

planner = TaskPlanner()
tasks = planner.create_plan("inspect repo -> run tests -> summarize")
# tasks[0].dependencies == []
# tasks[1].dependencies == [tasks[0].id]

ready = planner.get_ready_tasks()   # returns tasks with all deps completed
planner.update_status(task.id, "completed")
planner.all_completed()             # True when done
```

## Dependency Resolution

- Tasks with no dependencies are immediately ready
- A task becomes ready when all its dependencies reach `completed`
- Missing dependency IDs are treated as already satisfied

**Code:** `loom/orchestration/planner.py`
