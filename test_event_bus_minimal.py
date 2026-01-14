"""
Minimal test to verify event bus publishing works
"""
import asyncio
from loom.kernel.core import UniversalEventBus, Dispatcher
from loom.protocol.cloudevents import CloudEvent

async def test_event_bus():
    print("Creating event bus...")
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # Create a simple listener
    received_events = []

    async def listener(event: CloudEvent):
        print(f"Received event: {event.type}")
        received_events.append(event)

    # Subscribe to events
    await bus.subscribe("test.event", listener)
    print("Listener subscribed")

    # Publish an event using dispatcher.bus.publish
    print("Publishing event...")
    await dispatcher.bus.publish(CloudEvent(
        type="test.event",
        source="test",
        data={"message": "Hello"}
    ))

    # Wait a bit for event processing
    await asyncio.sleep(0.1)

    print(f"Events received: {len(received_events)}")
    if len(received_events) > 0:
        print("✅ Event bus publishing works!")
    else:
        print("❌ Event bus publishing failed!")

if __name__ == "__main__":
    asyncio.run(test_event_bus())
