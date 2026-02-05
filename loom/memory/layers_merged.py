"""
Memory Layer Abstractions (Merged Module)

Provides unified interfaces for all memory layers (L1-L4).
Based on Axiom A4 (Memory Hierarchy Axiom).

Classes:
- MemoryLayer: Abstract base class for all memory layers
- CircularBufferLayer: L1 - Fixed-capacity circular buffer with FIFO eviction
- PriorityQueueLayer: L2 - Heap-based priority queue
"""

import heapq
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from loom.protocol import Task

T = TypeVar("T")


# =============================================================================
# Base Layer Interface
# =============================================================================


class MemoryLayer(ABC, Generic[T]):
    """
    Memory layer abstract interface

    Unified contract for all memory layers (L1-L4).
    All implementations must provide these core operations.
    """

    @abstractmethod
    async def add(self, item: T) -> None:
        """Add item to the layer"""
        pass

    @abstractmethod
    async def retrieve(self, query: Any, limit: int = 10) -> list[T]:
        """Retrieve items from the layer"""
        pass

    @abstractmethod
    async def evict(self, count: int = 1) -> list[T]:
        """Evict items (for capacity management)"""
        pass

    @abstractmethod
    def size(self) -> int:
        """Get current layer size"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the layer"""
        pass


# =============================================================================
# L1: Circular Buffer Layer
# =============================================================================


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
        if len(self._buffer) == self._buffer.maxlen:
            evicted = self._buffer[0]
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
        """Register eviction callback"""
        self._eviction_callbacks.append(callback)


# =============================================================================
# L2: Priority Queue Layer
# =============================================================================


@dataclass(order=True)
class PriorityItem:
    """Priority item (for heap sorting)"""

    priority: float
    item: Task = field(compare=False)


class PriorityQueueLayer(MemoryLayer[Task]):
    """
    L2: Priority queue layer

    Features:
    - Heap-based priority queue
    - O(log n) insertion and deletion
    - Automatically maintains priority order
    """

    def __init__(self, max_size: int = 100):
        self._heap: list[PriorityItem] = []
        self._max_size = max_size

    async def add(self, item: Task) -> None:
        """Add task (O(log n))"""
        importance = item.metadata.get("importance", 0.5)
        priority_item = PriorityItem(-importance, item)

        if len(self._heap) < self._max_size:
            heapq.heappush(self._heap, priority_item)
        else:
            if priority_item < self._heap[0]:
                heapq.heapreplace(self._heap, priority_item)

    async def retrieve(self, _query: Any, limit: int = 10) -> list[Task]:
        """Get top N highest priority tasks"""
        sorted_items = sorted(self._heap)[:limit]
        return [item.item for item in sorted_items]

    async def evict(self, count: int = 1) -> list[Task]:
        """Evict lowest priority tasks"""
        evicted = []
        for _ in range(min(count, len(self._heap))):
            item = heapq.heappop(self._heap)
            evicted.append(item.item)
        return evicted

    def size(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        self._heap.clear()


__all__ = ["MemoryLayer", "CircularBufferLayer", "PriorityQueueLayer", "PriorityItem"]
