"""
Transport Layer - Interface and Implementations

Provides event transport mechanisms for local and distributed systems.
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


# Import implementations for convenience
from .memory import InMemoryTransport
from .nats import NATSTransport
from .redis import RedisTransport

__all__ = [
    "Transport",
    "EventHandler",
    "InMemoryTransport",
    "NATSTransport",
    "RedisTransport",
]
