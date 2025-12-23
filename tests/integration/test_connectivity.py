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
        
    async def publish(self, topic: str, event: CloudEvent) -> None:
        self.events.append(event) # Only append the event, not the topic tuple

@pytest.mark.asyncio
async def test_custom_transport_injection():
    """Verify that LoomApp uses the injected transport."""
    spy = SpyTransport()
    app = LoomApp(transport=spy)
    
    # Run a simple request
    # Since we don't have an agent, the request might fail routing, but it should still be PUBLISHED.
    # LoomApp.run -> dispatcher.dispatch -> bus.publish -> spy.publish
    
    # We can just fire an event manually if app.run needs setup
    # Or use app.run with a non-existent target (will publish but no one replies)
    
    # Let's add a dummy agent to avoid routing errors if any
    from loom.api.factory import Agent
    from loom.infra.llm import MockLLMProvider
    Agent(app, "test_agent", provider=MockLLMProvider())
    
    await app.run("Hello", target="node/test_agent")
    
    # Check spy
    assert len(spy.events) > 0
    # First event should be the request
    topic, event = spy.events[0]
    assert event.type == "node.request"
    assert "test_agent" in topic
