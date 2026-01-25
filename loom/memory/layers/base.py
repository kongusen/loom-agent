"""
Memory Layer Base Abstractions

Defines the unified interface for all memory layers (L1-L4).
Based on Axiom A4 (Memory Hierarchy Axiom).
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class MemoryLayer(ABC, Generic[T]):
    """
    Memory layer abstract interface

    Unified contract for all memory layers (L1-L4).
    All implementations must provide these core operations.
    """

    @abstractmethod
    async def add(self, item: T) -> None:
        """
        Add item to the layer

        Args:
            item: Item to add
        """
        pass

    @abstractmethod
    async def retrieve(self, query: Any, limit: int = 10) -> list[T]:
        """
        Retrieve items from the layer

        Args:
            query: Query condition (can be string, filter, etc.)
            limit: Maximum number of items to return

        Returns:
            List of matching items
        """
        pass

    @abstractmethod
    async def evict(self, count: int = 1) -> list[T]:
        """
        Evict items (for capacity management)

        Args:
            count: Number of items to evict

        Returns:
            List of evicted items
        """
        pass

    @abstractmethod
    def size(self) -> int:
        """
        Get current layer size

        Returns:
            Number of items currently stored
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the layer"""
        pass
