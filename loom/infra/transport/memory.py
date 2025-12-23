"""
In-Memory Transport Implementation
"""

import asyncio
from typing import Dict, List
from loom.interfaces.transport import Transport, EventHandler
from loom.protocol.cloudevents import CloudEvent

class InMemoryTransport(Transport):
    """
    Local In-Memory Transport using asyncio.
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        self._handlers.clear()

    async def publish(self, topic: str, event: CloudEvent) -> None:
        """Dispatch event to local handlers."""
        if not self._connected:
            raise RuntimeError("Transport not connected")
        handlers = self._handlers.get(topic, [])
        
        # Simple wildcard support (prefix*)

        tasks = []
        
        # 1. Exact match
        if topic in self._handlers:
            for handler in self._handlers[topic]:
                tasks.append(handler(event))
                
        # 2. Wildcard match (Suffix *)
        for sub_topic, handlers in self._handlers.items():
            if sub_topic.endswith("*"):
                prefix = sub_topic[:-1]
                if topic.startswith(prefix):
                    for handler in handlers:
                        tasks.append(handler(event))
        
        if tasks:
            await asyncio.gather(*tasks)

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        if not self._connected:
            # Auto-connect convenience? Or strict? 
            # Strict is better for explicit lifecycle, but for dev ease we can auto-connect.
            self._connected = True
            
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)
