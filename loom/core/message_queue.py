"""Message Queue for h2A Real-Time Steering (US1)

This module implements the async priority message queue that enables:
- Real-time agent interruption and cancellation
- Priority-based message processing
- Graceful shutdown with partial results
- Correlation ID tracking for multi-agent workflows

Architecture: h2A async message queue (Claude Code inspired)
"""

from __future__ import annotations

import asyncio
from typing import Optional
from uuid import uuid4

from loom.core.types import MessageQueueItem
from loom.core.errors import ExecutionAbortedError


class MessageQueue:
    """h2A async priority message queue for real-time steering.

    Features:
    - Priority-based ordering (10 = highest, 0 = lowest)
    - FIFO within same priority level
    - Cancel-all support for graceful shutdown
    - Correlation ID propagation

    Usage:
        queue = MessageQueue()
        await queue.put(MessageQueueItem(role="user", content="Task", priority=5))
        item = await queue.get()  # Blocks until item available
        await queue.cancel_all()  # Clear all pending items
    """

    def __init__(self, cancel_token: Optional[asyncio.Event] = None) -> None:
        """Initialize message queue.

        Args:
            cancel_token: Optional Event to signal cancellation from outside
        """
        # Use asyncio.PriorityQueue for automatic priority sorting
        # Items sorted by (priority, insertion_order) tuple
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._insertion_counter = 0  # For FIFO within same priority
        self._cancelled = asyncio.Event()
        self._external_cancel_token = cancel_token

    async def put(self, item: MessageQueueItem) -> None:
        """Add item to queue with priority ordering.

        Args:
            item: Message queue item with priority (0-10)

        Note: Higher priority numbers are processed first.
              Inverted for PriorityQueue (lower tuple values dequeued first).
        """
        if self._is_cancelled():
            raise ExecutionAbortedError("Queue cancelled, cannot add new items")

        # Invert priority for PriorityQueue (10 becomes -10, so it's dequeued first)
        priority = -item.priority

        # Use insertion counter for FIFO within same priority
        insertion_order = self._insertion_counter
        self._insertion_counter += 1

        # PriorityQueue sorts by tuple: (priority, insertion_order, item)
        await self._queue.put((priority, insertion_order, item))

    async def get(self, timeout: Optional[float] = None) -> MessageQueueItem:
        """Get highest priority item from queue.

        Args:
            timeout: Optional timeout in seconds (None = wait forever)

        Returns:
            MessageQueueItem: Highest priority item

        Raises:
            ExecutionAbortedError: If queue cancelled during get()
            asyncio.TimeoutError: If timeout expires
        """
        try:
            if timeout is not None:
                priority, order, item = await asyncio.wait_for(
                    self._queue.get(), timeout=timeout
                )
            else:
                # Check cancellation before blocking
                if self._is_cancelled():
                    raise ExecutionAbortedError("Queue cancelled")

                priority, order, item = await self._queue.get()

            # Check cancellation after get (in case cancelled while waiting)
            if self._is_cancelled():
                # Put item back if it's cancellable
                if item.cancellable:
                    raise ExecutionAbortedError("Queue cancelled")
                # Non-cancellable items still processed

            return item

        except asyncio.TimeoutError:
            raise

    async def cancel_all(self) -> None:
        """Cancel all pending items and prevent new additions.

        This signals graceful shutdown - current processing continues,
        but no new items will be dequeued.
        """
        self._cancelled.set()

        # Drain queue of cancellable items
        drained = []
        while not self._queue.empty():
            try:
                priority, order, item = self._queue.get_nowait()
                if not item.cancellable:
                    drained.append((priority, order, item))  # Keep non-cancellable
            except asyncio.QueueEmpty:
                break

        # Re-add non-cancellable items
        for priority, order, item in drained:
            await self._queue.put((priority, order, item))

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def is_cancelled(self) -> bool:
        """Check if queue has been cancelled."""
        return self._is_cancelled()

    def _is_cancelled(self) -> bool:
        """Internal cancellation check (includes external token)."""
        if self._cancelled.is_set():
            return True
        if self._external_cancel_token and self._external_cancel_token.is_set():
            return True
        return False

    def qsize(self) -> int:
        """Return approximate queue size."""
        return self._queue.qsize()

    async def peek(self) -> Optional[MessageQueueItem]:
        """Peek at highest priority item without removing it.

        Returns:
            MessageQueueItem if queue not empty, None otherwise
        """
        if self._queue.empty():
            return None

        # Get item
        priority, order, item = await self._queue.get()

        # Put it back
        await self._queue.put((priority, order, item))

        return item
