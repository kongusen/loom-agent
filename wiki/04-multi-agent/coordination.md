# Coordination

`Coordinator` executes a task plan across registered agent managers.

## Usage

```python
from loom.orchestration.coordinator import Coordinator
from loom.orchestration.events import EventBus

bus = EventBus()
coord = Coordinator(bus)
coord.register_agent("worker", manager)

results = await coord.execute_plan("worker", planner, task_timeout=120.0)
summary = coord.aggregate_results(results)
# {"total": 2, "succeeded": 2, "failed": 0, "outputs": {...}, "errors": {}}
```

## SubAgentManager

```python
from loom.orchestration.subagent import SubAgentManager

manager = SubAgentManager(parent=agent, max_depth=3)
result = await manager.spawn("Summarize file X", depth=1)
# result.success, result.output, result.error
```

Exceeding `max_depth` returns `SubAgentResult(success=False, error="MAX_DEPTH_EXCEEDED")`.

**Code:** `loom/orchestration/coordinator.py`, `loom/orchestration/subagent.py`
