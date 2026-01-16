"""
Tests for Infrastructure Store
"""

import pytest

from loom.infra.store import EventStore, InMemoryEventStore
from loom.protocol.cloudevents import CloudEvent


class TestEventStore:
    """Test abstract EventStore class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that EventStore cannot be instantiated directly."""
        with pytest.raises(TypeError):
            EventStore()


@pytest.mark.asyncio
class TestInMemoryEventStore:
    """Test InMemoryEventStore implementation."""

    @pytest.fixture
    def store(self):
        """Create a fresh store for each test."""
        return InMemoryEventStore()

    @pytest.fixture
    def sample_event(self):
        """Create a sample event."""
        return CloudEvent.create(
            source="/test/source",
            type="test.event",
            data={"message": "test"}
        )

    async def test_initialization(self, store):
        """Test store initialization."""
        assert store._storage == []

    async def test_append_event(self, store, sample_event):
        """Test appending an event."""
        await store.append(sample_event)

        assert len(store._storage) == 1
        assert store._storage[0] == sample_event

    async def test_append_multiple_events(self, store):
        """Test appending multiple events."""
        for i in range(5):
            event = CloudEvent.create(
                source=f"/test/source{i}",
                type="test.event",
                data={"index": i}
            )
            await store.append(event)

        assert len(store._storage) == 5

    async def test_get_events_empty_store(self, store):
        """Test getting events from empty store."""
        events = await store.get_events()

        assert events == []

    async def test_get_events_returns_all(self, store, sample_event):
        """Test getting all events."""
        await store.append(sample_event)

        events = await store.get_events()

        assert len(events) == 1
        assert events[0] == sample_event

    async def test_get_events_with_limit(self, store):
        """Test getting events with limit."""
        for i in range(10):
            event = CloudEvent.create(
                source="/test",
                type="test.event",
                data={"index": i}
            )
            await store.append(event)

        events = await store.get_events(limit=5)

        assert len(events) == 5

    async def test_get_events_with_offset(self, store):
        """Test getting events with offset."""
        for i in range(10):
            event = CloudEvent.create(
                source="/test",
                type="test.event",
                data={"index": i}
            )
            await store.append(event)

        events = await store.get_events(offset=5)

        assert len(events) == 5
        # Should return events starting from index 5
        assert events[0].data["index"] == 5

    async def test_get_events_with_limit_and_offset(self, store):
        """Test getting events with both limit and offset."""
        for i in range(20):
            event = CloudEvent.create(
                source="/test",
                type="test.event",
                data={"index": i}
            )
            await store.append(event)

        events = await store.get_events(limit=5, offset=10)

        assert len(events) == 5
        # Should return events 10-14
        assert events[0].data["index"] == 10
        assert events[-1].data["index"] == 14

    async def test_get_events_with_source_filter(self, store):
        """Test filtering by source."""
        event1 = CloudEvent.create(
            source="/source/a",
            type="test.event",
            data={"val": 1}
        )
        event2 = CloudEvent.create(
            source="/source/b",
            type="test.event",
            data={"val": 2}
        )

        await store.append(event1)
        await store.append(event2)

        events = await store.get_events(source="/source/a")

        assert len(events) == 1
        assert events[0].source == "/source/a"

    async def test_get_events_with_type_filter(self, store):
        """Test filtering by type."""
        event1 = CloudEvent.create(
            source="/test",
            type="type.a",
            data={"val": 1}
        )
        event2 = CloudEvent.create(
            source="/test",
            type="type.b",
            data={"val": 2}
        )

        await store.append(event1)
        await store.append(event2)

        events = await store.get_events(type="type.a")

        assert len(events) == 1
        assert events[0].type == "type.a"

    async def test_get_events_with_multiple_filters(self, store):
        """Test filtering by multiple attributes."""
        event1 = CloudEvent.create(
            source="/source/a",
            type="type.x",
            data={"val": 1}
        )
        event2 = CloudEvent.create(
            source="/source/a",
            type="type.y",
            data={"val": 2}
        )
        event3 = CloudEvent.create(
            source="/source/b",
            type="type.x",
            data={"val": 3}
        )

        await store.append(event1)
        await store.append(event2)
        await store.append(event3)

        events = await store.get_events(source="/source/a", type="type.x")

        assert len(events) == 1
        assert events[0].data["val"] == 1

    async def test_get_events_filter_no_match(self, store, sample_event):
        """Test filter that matches no events."""
        await store.append(sample_event)

        events = await store.get_events(source="/nonexistent")

        assert len(events) == 0

    async def test_clear(self, store):
        """Test clearing the store."""
        await store.append(CloudEvent.create(source="/test", type="test", data={}))
        await store.append(CloudEvent.create(source="/test", type="test", data={}))

        assert len(store._storage) == 2

        store.clear()

        assert len(store._storage) == 0

    async def test_events_stored_in_order(self, store):
        """Test that events are stored in append order."""
        for i in range(5):
            event = CloudEvent.create(
                source="/test",
                type="test.event",
                data={"index": i}
            )
            await store.append(event)

        events = await store.get_events()

        for i, event in enumerate(events):
            assert event.data["index"] == i

    async def test_get_events_beyond_storage(self, store):
        """Test getting events beyond available storage."""
        await store.append(CloudEvent.create(source="/test", type="test", data={}))

        events = await store.get_events(limit=10, offset=5)

        assert len(events) == 0

    async def test_append_preserves_event(self, store, sample_event):
        """Test that appended event is preserved unchanged."""
        await store.append(sample_event)

        retrieved = await store.get_events(limit=1)

        assert retrieved[0].source == sample_event.source
        assert retrieved[0].type == sample_event.type
        assert retrieved[0].data == sample_event.data

    async def test_filter_with_nonexistent_attribute(self, store, sample_event):
        """Test filtering by attribute that doesn't exist on events."""
        await store.append(sample_event)

        # Filter by attribute that doesn't exist
        events = await store.get_events(nonexistent_attr="value")

        # Should return empty since no event has that attribute
        assert len(events) == 0
