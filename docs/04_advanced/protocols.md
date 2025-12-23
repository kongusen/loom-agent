# Protocols & Extensions

Loom follows a **Protocol-First** architecture. This means you can replace almost any component by implementing its corresponding `typing.Protocol`.

## Key Protocols (`loom.protocol.interfaces`)

### `TransportProtocol`
Defines how events move.
- **Default**: `InMemoryTransport` (for single-process apps).
- **Extension**: Implement Redis, NATS, or Kafka transports to scale Loom across multiple servers.

#### Example: Redis Transport (Conceptual)

```python
import redis.asyncio as redis
from loom.protocol.cloudevents import CloudEvent
import json

class RedisTransport:
    def __init__(self, url: str):
        self.redis = redis.from_url(url)
        self.pubsub = self.redis.pubsub()

    async def connect(self):
        await self.redis.ping()

    async def disconnect(self):
        await self.redis.close()

    async def publish(self, topic: str, event: CloudEvent):
        payload = json.dumps(event.to_dict())
        await self.redis.publish(topic, payload)

    async def subscribe(self, topic: str, handler):
        await self.pubsub.subscribe(topic)
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                event = CloudEvent(**data)
                await handler(event)
```

### `LLMProviderProtocol`
Defines how to talk to models.
- **Default**: `MockLLMProvider`.
- **Extension**: Implement adapters for OpenAI, Anthropic, Ollama, etc.

### `MemoryStrategy`
Defines how agents start state.
- **Default**: `MetabolicMemory`.
- **Extension**: Implement `VectorStoreMemory` or `SQLMemory` for different persistence needs.

## Usage
Inject your custom implementations during Node or App initialization:

```python
app = LoomApp(transport=RedisTransport("redis://localhost"))
agent = AgentNode(..., provider=OpenAIProver())
```
