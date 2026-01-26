# Event System (The Nervous System)

Loom is an **Event-Driven System**. If the Fractal Architecture is the skeletal structure, the Event System is the nervous system that connects everything.

## Axiom 2: Event Sovereignty

The second axiom of Loom states: **"All communication must happen via Tasks (Events)."**

This means there are no backdoor function calls between isolated agents. Every interaction—requests, responses, signals, errors—is encapsulated in a standardized event object.

## Type-Safe Routing

In earlier versions, Loom relied on string-based routing, which was prone to errors (typos, schema mismatches). The current version introduces a **Type-Safe Event Bus**.

### 1. Task Actions
Instead of magic strings, we use Enums (`loom.events.actions`) to define all possible operations:

```python
from loom.events.actions import TaskAction

# Good: Type-safe
event_bus.publish(action=TaskAction.EXECUTE, payload=task)

# Bad: String typo
event_bus.publish(action="executes", ...) # Error
```

Supported Action Categories:
- **`TaskAction`**: `EXECUTE`, `CANCEL`, `QUERY`
- **`MemoryAction`**: `READ`, `WRITE`, `SYNC`
- **`AgentAction`**: `START`, `STOP`, `HEARTBEAT`

### 2. Protocol-based Handlers
Event handlers are now defined by a strict Protocol, ensuring that any function registered to handle an event matches the expected signature.

```python
class TaskHandler(Protocol):
    async def __call__(self, task: Task) -> Task:
        ...
```

## CloudEvents Standard

Loom strictly adheres to the **CNCF CloudEvents 1.0** specification. This ensures interoperability with external tools, monitoring systems, and other microservices.

### Event Structure
Every event in Loom contains:
- `id`: Unique identifier.
- `source`: URI of the sender (e.g., `node://agent-1`).
- `type`: The kind of event (e.g., `com.loom.task.created`).
- `data`: The payload (the task details, result, etc.).

## The Universal Bus

All events flow through a **Universal Event Bus**. This architecture decouples senders from receivers, allowing for:

1.  **Observability**: A monitoring tool can subscribe to the bus and see "thoughts" flowing in real-time.
2.  **Replayability**: Events can be logged and replayed for debugging or training.
3.  **Distribution**: Events can be routed over HTTP, WebSocket, or MQTT, allowing nodes to live on different physical machines.
