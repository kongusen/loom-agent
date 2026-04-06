"""Test events system"""

import pytest
import asyncio
from loom.api import EventBus, EventStream, Event


class TestEventBus:
    """Test EventBus"""

    @pytest.mark.asyncio
    async def test_publish_subscribe(self):
        """Test publish and subscribe"""
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(handler, "test.event")
        event = Event(run_id="run_001", type="test.event")
        await bus.publish(event)
        await asyncio.sleep(0.1)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribe"""
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(handler, "test.event")
        bus.unsubscribe(handler, "test.event")

        event = Event(run_id="run_001", type="test.event")
        await bus.publish(event)
        await asyncio.sleep(0.1)

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_list_by_run(self):
        """Test event history is stored by run."""
        bus = EventBus()
        await bus.publish(Event(run_id="run_001", type="test.event"))
        await bus.publish(Event(run_id="run_001", type="test.event_2"))

        history = bus.list_by_run("run_001")
        assert len(history) == 2
        assert history[0].type == "test.event"


class TestEventStream:
    """Test EventStream"""

    @pytest.mark.asyncio
    async def test_stream_events(self):
        """Test stream events"""
        bus = EventBus()
        run_id = "run_001"

        async def publish():
            await asyncio.sleep(0.1)
            await bus.publish(Event(run_id=run_id, type="e1"))
            await asyncio.sleep(0.1)
            await bus.publish(Event(run_id=run_id, type="e2"))

        asyncio.create_task(publish())

        stream = EventStream(bus, run_id)
        received = []

        async def consume():
            count = 0
            async for event in stream:
                received.append(event)
                count += 1
                if count >= 2:
                    stream.close()
                    break

        await consume()
        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_stream_preloads_history(self):
        """Test stream can replay historical events."""
        bus = EventBus()
        run_id = "run_001"
        await bus.publish(Event(run_id=run_id, type="e1"))
        await bus.publish(Event(run_id=run_id, type="e2"))

        stream = EventStream(bus, run_id)
        received = []

        async for event in stream:
            received.append(event)
            if len(received) >= 2:
                stream.close()
                break

        assert [event.type for event in received] == ["e1", "e2"]
