"""
Event Store - Interface and Implementation
"""

from abc import ABC, abstractmethod

from loom.protocol.cloudevents import CloudEvent


class EventStore(ABC):
    """
    Abstract Interface for Event Persistence.
    Decouples the Event Bus from the storage mechanism (Memory, Redis, SQL).
    """

    @abstractmethod
    async def append(self, event: CloudEvent) -> None:
        """
        Persist a single event.
        """
        pass

    @abstractmethod
    async def get_events(self, limit: int = 100, offset: int = 0, **filters) -> list[CloudEvent]:
        """
        Retrieve events with optional filtering.
        Filters can match on standard CloudEvent attributes (source, type, etc.)
        """
        pass


class InMemoryEventStore(EventStore):
    """
    Simple in-memory list storage for events.
    Useful for testing and local demos.
    """

    def __init__(self):
        self._storage: list[CloudEvent] = []

    async def append(self, event: CloudEvent) -> None:
        self._storage.append(event)

    async def get_events(self, limit: int = 100, offset: int = 0, **filters) -> list[CloudEvent]:
        """
        Naive implementation of filtering.
        """
        filtered = self._storage

        # Apply filters
        # e.g. get_events(source="/agent/a")
        if filters:
            filtered = [
                e for e in filtered
                if all(getattr(e, k, None) == v for k, v in filters.items())
            ]

        # Apply pagination
        return filtered[offset : offset + limit]

    def clear(self):
        self._storage.clear()
