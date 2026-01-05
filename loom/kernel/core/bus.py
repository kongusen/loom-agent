"""
Universal Event Bus (Kernel)
"""

import asyncio
from typing import Dict, List, Callable, Awaitable, Optional, Any

from loom.protocol.cloudevents import CloudEvent
from loom.infra.store import EventStore
from loom.infra.store import InMemoryEventStore
from loom.infra.transport import Transport, EventHandler
from loom.infra.transport.memory import InMemoryTransport

class UniversalEventBus:
    """
    Universal Event Bus based on Event Sourcing.
    Delegates routing to a Transport layer.
    """
    
    def __init__(self, store: EventStore = None, transport: Transport = None):
        self.store = store or InMemoryEventStore()
        self.transport = transport or InMemoryTransport()
        
    async def connect(self):
        """Connect the underlying transport."""
        await self.transport.connect()
        
    async def disconnect(self):
        """Disconnect the underlying transport."""
        await self.transport.disconnect()

    async def publish(self, event: CloudEvent) -> None:
        """
        Publish an event to the bus.
        1. Persist to store.
        2. Route to subscribers via Transport.
        """
        # 1. Persist
        await self.store.append(event)
        
        # 2. Route via Transport
        topic = self._get_topic(event)
        
        # Ensure connected
        # (Optimistically connect. In prod, connect() called at startup app.start())
        await self.transport.connect()
        
        await self.transport.publish(topic, event)

    async def subscribe(self, topic: str, handler: Callable[[CloudEvent], Awaitable[None]]):
        """Register a handler for a topic."""
        # optimistic connect
        await self.transport.connect()
        await self.transport.subscribe(topic, handler)

    async def unsubscribe(self, topic: str, handler: Callable[[CloudEvent], Awaitable[None]]):
        """
        Unregister a handler from a topic.

        FIXED: Added to prevent memory leaks from accumulated handlers.
        Delegates to transport layer.
        """
        await self.transport.unsubscribe(topic, handler)

    def _get_topic(self, event: CloudEvent) -> str:
        """Construct topic string from event."""
        # Special routing for requests: use subject (target) if present
        if event.subject and (event.type == "node.request" or event.type == "node.call"):
            safe_subject = event.subject.strip("/")
            return f"{event.type}/{safe_subject}"
            
        # Default: route by source (Origin)
        safe_source = event.source.strip("/")
        return f"{event.type}/{safe_source}"

    async def get_events(self) -> List[CloudEvent]:
        """Return all events in the store."""
        return await self.store.get_events(limit=1000)

    async def clear(self):
        """Clear state (for testing)."""
        if hasattr(self.store, "clear"):
            self.store.clear()
        
        await self.transport.disconnect()
