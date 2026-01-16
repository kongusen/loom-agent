"""
Transport Base Classes

Extracted to avoid circular imports in __init__.py
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from loom.protocol.cloudevents import CloudEvent

EventHandler = Callable[[CloudEvent], Awaitable[None]]


class Transport(ABC):
    """
    Abstract Base Class for Event Transport.
    Responsible for delivering events between components (local or remote).
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the transport layer."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        pass

    @abstractmethod
    async def publish(self, topic: str, event: CloudEvent) -> None:
        """Publish an event to a specific topic."""
        pass

    @abstractmethod
    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        """Subscribe to a topic."""
        pass

    @abstractmethod
    async def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        """Unsubscribe from a topic."""
        pass
