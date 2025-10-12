from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional


class EventType(str, Enum):
    TEXT = "text"
    TOOL = "tool"
    CONTROL = "control"  # pause/resume/abort


@dataclass
class SteeringEvent:
    event_type: EventType
    data: Dict[str, Any]
    priority: int = 0


Handler = Callable[[SteeringEvent], Awaitable[None]]


class EventBus:
    """增强的事件总线 - 支持实时 Steering（中断/暂停/注入）。"""

    def __init__(self) -> None:
        self._event_queue: asyncio.Queue[SteeringEvent] = asyncio.Queue()
        self._subscribers: Dict[EventType, list[Handler]] = {}
        self._abort_signal = asyncio.Event()
        self._pause_signal = asyncio.Event()

    async def publish(self, event: SteeringEvent) -> None:
        await self._event_queue.put(event)

    async def subscribe(self, event_type: EventType, handler: Handler) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    async def process_events(self) -> None:
        while True:
            if self._pause_signal.is_set():
                await asyncio.sleep(0.05)
                continue
            if self._abort_signal.is_set():
                break
            event = await self._event_queue.get()
            await self._dispatch_event(event)

    async def _dispatch_event(self, event: SteeringEvent) -> None:
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            await handler(event)

    def abort(self) -> None:
        self._abort_signal.set()

    def is_aborted(self) -> bool:
        return self._abort_signal.is_set()

    def pause(self) -> None:
        self._pause_signal.set()

    def resume(self) -> None:
        self._pause_signal.clear()

