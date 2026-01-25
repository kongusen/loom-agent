"""
Priority Queue Layer (L2)

Heap-based priority queue with O(log n) insertion and deletion.
"""

import heapq
from dataclasses import dataclass, field
from typing import Any

from loom.memory.layers.base import MemoryLayer
from loom.protocol import Task


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
        # Use negative number to implement max heap
        priority_item = PriorityItem(-importance, item)

        if len(self._heap) < self._max_size:
            heapq.heappush(self._heap, priority_item)
        else:
            # If new item has higher priority, replace lowest priority item
            if priority_item < self._heap[0]:
                heapq.heapreplace(self._heap, priority_item)

    async def retrieve(self, query: Any, limit: int = 10) -> list[Task]:
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
