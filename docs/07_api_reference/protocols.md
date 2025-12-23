# Protocols & Interfaces

Loom uses `typing.Protocol` to define contracts. Inspect `loom.protocol.interfaces` for source truth.

## `loom.protocol.interfaces.NodeProtocol`

```python
class NodeProtocol(Protocol):
    node_id: str
    source_uri: str
    
    async def process(self, event: CloudEvent) -> Any: ...
    async def call(self, target_node: str, data: Dict[str, Any]) -> Any: ...
```

## `loom.protocol.interfaces.TransportProtocol`

Interface for the pub/sub layer.

```python
class TransportProtocol(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def publish(self, topic: str, event: CloudEvent) -> None: ...
    async def subscribe(self, topic: str, handler: Any) -> None: ...
```

## `loom.interfaces.llm.LLMProvider`

Interface for Language Models.

```python
class LLMProviderProtocol(Protocol):
    async def chat(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Any: ...

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[str]: ...
```
