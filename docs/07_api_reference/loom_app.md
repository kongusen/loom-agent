# LoomApp & Core Kernel

## `loom.api.main.LoomApp`

The high-level facade for the Loom framework. Initializes the kernel, event bus, and dispatcher.

### Constructor
```python
def __init__(
    self, 
    store: Optional[EventStore] = None, 
    transport: Optional[Transport] = None,
    control_config: Optional[Dict[str, Any]] = None
)
```
- **store**: Persistence layer for events. Defaults to `InMemoryEventStore`.
- **transport**: Pub/Sub mechanism. Defaults to `InMemoryTransport`.
- **control_config**: Dictionary for configuring kernel interceptors.
    - `budget`: `{"max_tokens": int}` - Token usage limit.
    - `depth`: `{"max_depth": int}` - Max recursion depth.
    - `hitl`: `List[str]` - Keywords triggering human-in-the-loop.

### Methods

#### `add_node`
```python
def add_node(self, node: Node)
```
Registers a node with the application. The node must have been initialized with `app.dispatcher`.

#### `run`
```python
async def run(self, task: str, target: str) -> Any
```
Executes a task by sending a `node.request` to the target and waiting for `node.response`.
- **task**: The instruction string.
- **target**: The `node_id` of the receiver.
- **Returns**: The `result` field from the response event.
- **Raises**: `TimeoutError` if response takes longer than 30s (default).

#### `on`
```python
def on(self, event_type: str, handler: Callable[[CloudEvent], Any])
```
Registers an observability hook.
- **event_type**: CloudEvent type string (e.g., "agent.thought") or "*" for all.
- **handler**: Async or sync function receiving the event.

---

## `loom.kernel.bus.UniversalEventBus`

The backbone of the system. Manages Event Sourcing and Routing.

### Methods

#### `publish`
```python
async def publish(self, event: CloudEvent) -> None
```
Persists the event and routes it via the Transport.

#### `subscribe`
```python
async def subscribe(self, topic: str, handler: Callable[[CloudEvent], Awaitable[None]])
```
Subscribes to a topic.
- **topic**: Topic string (e.g., "node.request/agent-1").

---

## `loom.kernel.dispatcher.Dispatcher`

Manages theInterceptor Chain and Event Dispatch.

### Methods

#### `dispatch`
```python
async def dispatch(self, event: CloudEvent) -> None
```
Passes the event through `pre_invoke` interceptors, publishes to the bus, and then runs `post_invoke` interceptors.
