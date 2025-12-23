"""
Integration Test: Connectivity
"""

import pytest
from typing import List

from loom.api.main import LoomApp
from loom.api.factory import Agent
from loom.protocol.cloudevents import CloudEvent
from loom.interfaces.transport import Transport

class SpyTransport(Transport):
    def __init__(self) -> None:
        self.events: List[CloudEvent] = []
        
    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def subscribe(self, topic: str, handler) -> None:
        pass

    async def publish(self, topic: str, event: CloudEvent) -> None:
        self.events.append((topic, event))

@pytest.mark.asyncio
async def test_custom_transport_injection():
    """Verify that LoomApp uses the injected transport."""
    spy = SpyTransport()
    app = LoomApp(transport=spy)
    
    # Run a simple request physically via dispatcher to verify transport usage
    # We bypass app.run() because app.run() waits for a response that SpyTransport won't deliver.
    event = CloudEvent.create(
        source="/test",
        type="node.request",
        data={"task": "hello"},
        subject="node/test_agent"
    )
    
    await app.dispatcher.dispatch(event)
    
    # Check spy
    assert len(spy.events) > 0
    # First event should be the request
    topic, captured_event = spy.events[0]
    assert captured_event.type == "node.request"
    assert captured_event.data["task"] == "hello"
    assert "node/test_agent" in topic
