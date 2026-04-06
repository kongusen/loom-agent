"""Event system for Loom runtime"""

import asyncio
from collections import defaultdict
from typing import Awaitable, Callable, Optional

from .models import Event


EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """Event bus for publishing and subscribing to events"""

    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._all_subscribers: list[EventHandler] = []
        self._history_by_run: dict[str, list[Event]] = defaultdict(list)

    def subscribe(
        self,
        handler: EventHandler,
        event_type: Optional[str] = None
    ) -> None:
        """Subscribe to events"""
        if event_type:
            self._subscribers[event_type].append(handler)
        else:
            self._all_subscribers.append(handler)

    def unsubscribe(
        self,
        handler: EventHandler,
        event_type: Optional[str] = None
    ) -> None:
        """Unsubscribe from events"""
        if event_type:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
        else:
            if handler in self._all_subscribers:
                self._all_subscribers.remove(handler)

    async def publish(self, event: Event) -> None:
        """Publish event to subscribers"""
        self._history_by_run[event.run_id].append(event)

        # Notify type-specific subscribers
        handlers = list(self._subscribers.get(event.type, []))

        # Notify all-event subscribers
        handlers.extend(self._all_subscribers)

        # Execute handlers
        if handlers:
            await asyncio.gather(
                *[handler(event) for handler in handlers],
                return_exceptions=True
            )

    def list_by_run(self, run_id: str) -> list[Event]:
        """List historical events for a run."""
        return self._history_by_run.get(run_id, []).copy()


class EventStream:
    """Event stream for consuming events"""

    def __init__(self, event_bus: EventBus, run_id: str, preload_history: bool = True):
        self.event_bus = event_bus
        self.run_id = run_id
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._active = True
        self._preload_history = preload_history
        self._preloaded = False

    async def _handler(self, event: Event) -> None:
        """Internal event handler"""
        if event.run_id == self.run_id and self._active:
            await self._queue.put(event)

    async def _preload(self) -> None:
        """Preload historical events into the queue once."""
        if self._preloaded or not self._preload_history:
            return

        for event in self.event_bus.list_by_run(self.run_id):
            await self._queue.put(event)
        self._preloaded = True

    async def __aiter__(self):
        """Async iterator"""
        await self._preload()

        # Subscribe to events
        self.event_bus.subscribe(self._handler)

        try:
            while self._active:
                try:
                    event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                    yield event
                except asyncio.TimeoutError:
                    continue
        finally:
            self.event_bus.unsubscribe(self._handler)

    def close(self) -> None:
        """Close stream"""
        self._active = False
