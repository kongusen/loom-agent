"""
Middleware Interceptors (Kernel)
"""

import uuid
from abc import ABC, abstractmethod

from loom.protocol.cloudevents import CloudEvent


class Interceptor(ABC):
    """
    Abstract Base Class for Interceptors.
    Allows AOP-style cross-cutting concerns (Auth, Logging, Budget).
    """

    @abstractmethod
    async def pre_invoke(self, event: CloudEvent) -> CloudEvent | None:
        """
        Called before the event is dispatched to a handler.
        Return the event (modified or not) to proceed.
        Return None to halt execution (block/filter).
        """
        pass

    @abstractmethod
    async def post_invoke(self, event: CloudEvent) -> None:
        """
        Called after the event has been processed.
        """
        pass

class TracingInterceptor(Interceptor):
    """
    Injects Distributed Tracing Context (W3C Trace Parent).
    """
    async def pre_invoke(self, event: CloudEvent) -> CloudEvent | None:
        if not event.traceparent:
            # Generate new trace
            trace_id = uuid.uuid4().hex
            span_id = uuid.uuid4().hex[:16]
            event.traceparent = f"00-{trace_id}-{span_id}-01"
        return event

    async def post_invoke(self, event: CloudEvent) -> None:
        pass

class AuthInterceptor(Interceptor):
    """
    Basic Source Verification.
    """
    def __init__(self, allowed_prefixes: set[str]):
        self.allowed_prefixes = allowed_prefixes

    async def pre_invoke(self, event: CloudEvent) -> CloudEvent | None:
        if not event.source:
             return None

        # Check simplified prefix
        # e.g. source="/agent/foo", prefix="agent"
        # source="agent", prefix="agent"
        parts = event.source.strip("/").split("/")
        if not parts:
            return None

        prefix = parts[0]
        if prefix not in self.allowed_prefixes:
            print(f"🚫 Unauthorized source: {event.source}")
            return None

        return event

    async def post_invoke(self, event: CloudEvent) -> None:
        pass
