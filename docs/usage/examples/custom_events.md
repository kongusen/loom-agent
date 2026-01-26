# Custom Events and Handlers

Loom's Event Bus is extensible. You can define your own event types and handlers.

## 1. Defining Actions

Use `TaskAction` or extend it (if the system supports extension, otherwise use the standard `TaskAction.EXECUTE` with custom payload).

Currently, Loom emphasizes using the standard `TaskAction` Enum for type safety.

## 2. Registering a Custom Handler

```python
import asyncio
from typing import Any
from loom.api import LoomApp
from loom.types.core import Task
from loom.events.actions import TaskAction

async def my_custom_logger(task: Task) -> Task:
    """A middleware that logs every task."""
    print(f"[AUDIT] Processing task: {task.id} - {task.action}")
    return task

async def main():
    app = LoomApp()
    
    # Access the event bus via the app (or dispatcher)
    # Note: Direct bus access might require accessing internal components depending on API exposure.
    # Typically, you register plugins or middleware.
    
    # For demonstration, let's assume we can register to the internal bus:
    if hasattr(app, 'event_bus'):
        app.event_bus.register(TaskAction.EXECUTE, my_custom_logger)
        print("Registered custom logger.")

    # ... run your agent ...

if __name__ == "__main__":
    asyncio.run(main())
```

> **Note**: In v0.4.2, direct Event Bus manipulation is an advanced feature usually handled by the `Dispatcher`.
