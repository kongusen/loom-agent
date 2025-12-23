"""
Event Store Interface
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

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
    async def get_events(self, limit: int = 100, offset: int = 0, **filters) -> List[CloudEvent]:
        """
        Retrieve events with optional filtering.
        Filters can match on standard CloudEvent attributes (source, type, etc.)
        """
        pass
