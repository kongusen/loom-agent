"""Typed event bus — publish/subscribe with parent-child propagation and pattern matching."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, Awaitable

from ..types import AgentEvent

logger = logging.getLogger(__name__)

Handler = Callable[[AgentEvent], Awaitable[None]]


class EventBus:
    """Event bus with parent-child propagation and pattern matching (e.g. 'tool:*')."""

    def __init__(self, node_id: str | None = None, parent: EventBus | None = None) -> None:
        self.node_id = node_id
        self._parent = parent
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._wildcard: list[Handler] = []

    def create_child(self, node_id: str) -> EventBus:
        return EventBus(node_id=node_id, parent=self)

    def on(self, event_type: str, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def on_pattern(self, pattern: str, handler: Handler) -> None:
        self._handlers[pattern].append(handler)

    def on_all(self, handler: Handler) -> None:
        self._wildcard.append(handler)

    def off(self, event_type: str, handler: Handler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event: AgentEvent) -> None:
        event_type = getattr(event, "type", "")
        # Exact match + wildcard
        for h in self._handlers.get(event_type, []) + self._wildcard:
            try:
                await h(event)
            except Exception:
                logger.exception("Event handler error for %s", event_type)
        # Pattern match: 'tool:*' matches 'tool:call', etc.
        for pat, handlers in self._handlers.items():
            if not pat.endswith(":*"):
                continue
            prefix = pat[:-1]  # 'tool:*' → 'tool:'
            if event_type.startswith(prefix):
                for h in handlers:
                    try:
                        await h(event)
                    except Exception:
                        logger.exception("Pattern handler error for %s", pat)
        # Propagate to parent
        if self._parent:
            await self._parent.emit(event)
