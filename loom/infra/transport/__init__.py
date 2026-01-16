"""
Transport Layer - Interface and Implementations

Provides event transport mechanisms for local and distributed systems.
"""

# Import base classes
from loom.infra.transport.base import EventHandler, Transport

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
