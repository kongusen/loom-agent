"""
Circular Buffer Layer (L1)

Fixed-capacity circular buffer with FIFO eviction strategy.
"""

from collections import deque
from collections.abc import Callable
from typing import Any

from loom.memory.layers.base import MemoryLayer
from loom.protocol import Task


class CircularBufferLayer(MemoryLayer[Task]):
    """
    L1: Circular buffer layer

    Features:
    - Fixed capacity circular buffer
    - FIFO eviction strategy
    - Eviction event callback mechanism
    """

    def __init__(self, max_size: int = 50):
        self._buffer: deque[Task] = deque(maxlen=max_size)
        self._eviction_callbacks: list[Callable[[Task], None]] = []

    async def add(self, item: Task) -> None:
        """Add task, automatically evict oldest"""
        # Check if eviction will occur
        if len(self._buffer) == self._buffer.maxlen:
            evicted = self._buffer[0]
            # Trigger eviction callbacks
            for callback in self._eviction_callbacks:
                callback(evicted)

        self._buffer.append(item)

    async def retrieve(self, _query: Any, limit: int = 10) -> list[Task]:
        """Get most recent N tasks"""
        return list(self._buffer)[-limit:]

    async def evict(self, count: int = 1) -> list[Task]:
        """Manual eviction (remove from left)"""
        evicted = []
        for _ in range(min(count, len(self._buffer))):
            if self._buffer:
                evicted.append(self._buffer.popleft())
        return evicted

    def size(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()

    def on_eviction(self, callback: Callable[[Task], None]) -> None:
        """
        Register eviction callback

        When a task is automatically evicted, all registered callbacks will be called.
        This allows external components (like index managers) to respond to eviction events.
        """
        self._eviction_callbacks.append(callback)
