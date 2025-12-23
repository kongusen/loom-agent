
import asyncio
from typing import Dict, List, Set
from collections import defaultdict
import logging

from loom.interfaces.transport import Transport, EventHandler
from loom.protocol.cloudevents import CloudEvent

logger = logging.getLogger(__name__)

class InMemoryTransport(Transport):
    """
    In-memory transport implementation using asyncio.Queue/Event.
    Default for local development.
    """

    def __init__(self):
        self._connected = False
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        # For wildcard support: "node.request/*" -> [handler1, handler2]
        self._wildcard_handlers: Dict[str, List[EventHandler]] = defaultdict(list)

    async def connect(self) -> None:
        self._connected = True
        logger.info("InMemoryTransport connected")

    async def disconnect(self) -> None:
        self._connected = False
        self._handlers.clear()
        self._wildcard_handlers.clear()
        logger.info("InMemoryTransport disconnected")

    async def publish(self, topic: str, event: CloudEvent) -> None:
        if not self._connected:
             logger.warning("InMemoryTransport not connected, dropping event")
             return

        # Direct dispatch to handlers
        await self._dispatch(topic, event)

    async def subscribe(self, topic: str, handler: EventHandler) -> None:
        if "*" in topic:
            self._wildcard_handlers[topic].append(handler)
        else:
            self._handlers[topic].append(handler)

    async def _dispatch(self, topic: str, event: CloudEvent) -> None:
        targets: Set[EventHandler] = set()

        # 1. Exact match
        if topic in self._handlers:
            targets.update(self._handlers[topic])

        # 2. Wildcard match (Simple prefix/suffix matching)
        for pattern, handlers in self._wildcard_handlers.items():
            if self._match(topic, pattern):
                targets.update(handlers)

        # 3. Execute handlers
        for handler in targets:
            try:
                # Fire and forget / await
                # Since Bus expects us to be async, we await.
                # But handlers might be slow, so we should spawn tasks?
                # For in-memory bus, typically we want some concurrency.
                asyncio.create_task(self._safe_exec(handler, event))
            except Exception as e:
                 logger.error(f"Error dispatching to handler: {e}")

    async def _safe_exec(self, handler: EventHandler, event: CloudEvent):
        try:
             await handler(event)
        except Exception as e:
             logger.error(f"Handler failed: {e}")

    def _match(self, topic: str, pattern: str) -> bool:
        # Simple glob matching
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return topic.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return topic.endswith(pattern[1:])
        return topic == pattern
