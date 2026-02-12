"""
Memory Layer Abstractions (Token-First Design)

Provides unified interfaces for all memory layers (L1-L4).
Based on Axiom A4 (Memory Hierarchy Axiom).

设计原则：
1. Token-First - 所有容量以 token 为单位
2. Quality over Quantity - 按重要性和信息密度排序
3. Smart Eviction - 智能驱逐低价值内容

Classes:
- MemoryLayer: Abstract base class for all memory layers
- TokenBudgetLayer: L1 - Token budget based storage with FIFO eviction
- PriorityTokenLayer: L2 - Priority queue with token budget
"""

import heapq
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from loom.runtime import Task

if TYPE_CHECKING:
    pass

T = TypeVar("T")


# =============================================================================
# Base Layer Interface
# =============================================================================


class MemoryLayer(ABC, Generic[T]):
    """
    Memory layer abstract interface (Token-First Design)

    Unified contract for all memory layers (L1-L4).
    All implementations must provide these core operations.
    """

    @abstractmethod
    async def add(self, item: T, token_count: int) -> bool:
        """Add item to the layer with its token count. Returns True if added."""
        pass

    @abstractmethod
    async def retrieve(self, query: Any, limit: int = 10) -> list[T]:
        """Retrieve items from the layer"""
        pass

    @abstractmethod
    async def evict_tokens(self, tokens_to_free: int) -> list[T]:
        """Evict items to free up specified tokens"""
        pass

    @abstractmethod
    def token_usage(self) -> int:
        """Get current token usage"""
        pass

    @abstractmethod
    def size(self) -> int:
        """Get current item count"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the layer"""
        pass


# =============================================================================
# L1: Token Budget Layer (formerly CircularBufferLayer)
# =============================================================================


@dataclass
class TokenItem:
    """Item with token count for budget tracking"""

    item: Task
    token_count: int
    created_at: float = field(default_factory=lambda: __import__("time").time())


class TokenBudgetLayer(MemoryLayer[Task]):
    """
    L1: Token budget based layer (Token-First Design)

    Features:
    - Token budget instead of item count
    - FIFO eviction when budget exceeded
    - Tracks token usage per item
    """

    def __init__(self, token_budget: int = 8000):
        self._items: deque[TokenItem] = deque()
        self._token_budget = token_budget
        self._current_tokens = 0
        self._eviction_callbacks: list[Callable[[Task], None]] = []

    async def add(self, item: Task, token_count: int) -> bool:
        """Add task with token count, evict oldest if over budget"""
        # Evict oldest items until we have room
        while self._current_tokens + token_count > self._token_budget and self._items:
            evicted_item = self._items.popleft()
            self._current_tokens -= evicted_item.token_count
            for callback in self._eviction_callbacks:
                callback(evicted_item.item)

        # Add new item
        self._items.append(TokenItem(item=item, token_count=token_count))
        self._current_tokens += token_count
        return True

    async def retrieve(self, _query: Any, limit: int = 10) -> list[Task]:
        """Get most recent N tasks"""
        items = list(self._items)[-limit:]
        return [ti.item for ti in items]

    async def evict_tokens(self, tokens_to_free: int) -> list[Task]:
        """Evict oldest items to free specified tokens"""
        evicted = []
        freed = 0
        while freed < tokens_to_free and self._items:
            evicted_item = self._items.popleft()
            self._current_tokens -= evicted_item.token_count
            freed += evicted_item.token_count
            evicted.append(evicted_item.item)
            for callback in self._eviction_callbacks:
                callback(evicted_item.item)
        return evicted

    def token_usage(self) -> int:
        return self._current_tokens

    def size(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()
        self._current_tokens = 0

    def on_eviction(self, callback: Callable[[Task], None]) -> None:
        """Register eviction callback"""
        self._eviction_callbacks.append(callback)

    @property
    def token_budget(self) -> int:
        return self._token_budget


# Backward compatibility alias
CircularBufferLayer = TokenBudgetLayer


# =============================================================================
# L2: Priority Token Layer (formerly PriorityQueueLayer)
# =============================================================================


@dataclass(order=True)
class PriorityItem:
    """Priority item with token count (for heap sorting)"""

    priority: float
    token_count: int = field(compare=False)
    item: Task = field(compare=False)


class PriorityTokenLayer(MemoryLayer[Task]):
    """
    L2: Priority queue with token budget (Token-First Design)

    Features:
    - Heap-based priority queue
    - Token budget instead of item count
    - Evicts lowest priority items when over budget
    """

    def __init__(self, token_budget: int = 16000):
        self._heap: list[PriorityItem] = []
        self._token_budget = token_budget
        self._current_tokens = 0

    async def add(self, item: Task, token_count: int) -> bool:
        """Add task with priority (O(log n))"""
        importance = item.metadata.get("importance", 0.5)
        priority_item = PriorityItem(-importance, token_count, item)

        # Check if we need to evict
        if self._current_tokens + token_count > self._token_budget:
            # Evict lowest priority items until we have room
            await self.evict_tokens(token_count)

        # Add if we have room now
        if self._current_tokens + token_count <= self._token_budget:
            heapq.heappush(self._heap, priority_item)
            self._current_tokens += token_count
            return True

        # Check if new item has higher priority than lowest
        if self._heap and priority_item < max(self._heap):
            # Remove lowest priority item
            lowest = max(self._heap)
            self._heap.remove(lowest)
            heapq.heapify(self._heap)
            self._current_tokens -= lowest.token_count
            # Add new item
            heapq.heappush(self._heap, priority_item)
            self._current_tokens += token_count
            return True

        return False

    async def retrieve(self, _query: Any, limit: int = 10) -> list[Task]:
        """Get top N highest priority tasks"""
        sorted_items = sorted(self._heap)[:limit]
        return [item.item for item in sorted_items]

    async def evict_tokens(self, tokens_to_free: int) -> list[Task]:
        """Evict lowest priority items to free specified tokens"""
        evicted = []
        freed = 0

        while freed < tokens_to_free and self._heap:
            # Find and remove lowest priority (highest value due to negation)
            lowest = max(self._heap)
            self._heap.remove(lowest)
            heapq.heapify(self._heap)
            self._current_tokens -= lowest.token_count
            freed += lowest.token_count
            evicted.append(lowest.item)

        return evicted

    def token_usage(self) -> int:
        return self._current_tokens

    def size(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
        self._current_tokens = 0

    @property
    def token_budget(self) -> int:
        return self._token_budget


# Backward compatibility alias
PriorityQueueLayer = PriorityTokenLayer


__all__ = [
    "MemoryLayer",
    "TokenBudgetLayer",
    "PriorityTokenLayer",
    "CircularBufferLayer",
    "PriorityQueueLayer",
    "PriorityItem",
    "TokenItem",
]
