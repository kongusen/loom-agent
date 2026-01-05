# Protocol-First Architecture & Event Bus

Loom relies on a **Protocol-First** design philosophy. This means interaction patterns are defined by explicit Interfaces (Protocols) and Data Contracts, rather than concrete class inheritance.

## Why Protocol-First?

1.  **Decoupling**: You can replace the entire Memory system or Node implementation without breaking other parts, as long as the Protocol is satisfied.
2.  **Interoperability**: Different systems (even non-Python ones) can interact if they adhere to the data contract (CloudEvents).
3.  **Testing**: Mocks are trivial to implement.

## The Universal Event Bus

All communication in Loom happens over the **Universal Event Bus**. Agents **do not** call methods on each other directly. They publish events.

### CloudEvents Standard

We use the [CNCF CloudEvents](https://cloudevents.io/) specification for all messages.

```json
{
    "specversion": "1.0",
    "type": "node.request",
    "source": "/loom/agent/manager",
    "subject": "/loom/agent/worker",
    "id": "A234-1234-1234",
    "time": "2023-11-02T12:00:00Z",
    "datacontenttype": "application/json",
    "data": {
        "instruction": "Analyze this dataset",
        "context": {...}
    }
}
```

### Event Types
*   `node.request`: A request to perform work.
*   `node.response`: The result of the work.
*   `node.error`: Something went wrong.
*   `system.heartbeat`: Health checks.

## Key Protocols

### `NodeProtocol`
Defines an entity that can process events.
```python
class NodeProtocol(Protocol):
    async def process(self, event: CloudEvent) -> CloudEvent: ...
```

### `MemoryProtocol`
Defines how to store and retrieve data.
```python
class MemoryProtocol(Protocol):
    async def save(self, key: str, value: Any): ...
    async def load(self, key: str) -> Any: ...
```

### `TransferProtocol` (MCP)
The **Model Context Protocol (MCP)** defines how tools are discovered and invoked. Loom Agents use MCP to:
*   List available tools (`list_tools`).
*   call tools (`call_tool`).
*   Read resources (`read_resource`).

This standard allows Loom to connect to **any** MCP-compliant server (e.g., a Database MCP, a Slack MCP) without writing custom integration code.
