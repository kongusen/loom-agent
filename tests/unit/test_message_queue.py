"""Unit tests for MessageQueue (T034-T036)"""

import asyncio

import pytest

from loom.core.message_queue import MessageQueue
from loom.core.types import MessageQueueItem
from loom.core.errors import ExecutionAbortedError


@pytest.mark.unit
async def test_priority_ordering():
    """Test high priority messages dequeued before low priority (T034)."""
    queue = MessageQueue()

    # Add messages with different priorities
    await queue.put(MessageQueueItem(role="user", content="Low", priority=3))
    await queue.put(MessageQueueItem(role="user", content="High", priority=8))
    await queue.put(MessageQueueItem(role="user", content="Medium", priority=5))
    await queue.put(MessageQueueItem(role="user", content="Highest", priority=10))

    # Assert: Dequeue in priority order
    first = await queue.get()
    assert first.content == "Highest", "Priority 10 should be first"

    second = await queue.get()
    assert second.content == "High", "Priority 8 should be second"

    third = await queue.get()
    assert third.content == "Medium", "Priority 5 should be third"

    fourth = await queue.get()
    assert fourth.content == "Low", "Priority 3 should be last"


@pytest.mark.unit
async def test_cancel_all():
    """Test cancel_all() cancels all pending messages (T035)."""
    queue = MessageQueue()

    # Add multiple cancellable and non-cancellable items
    await queue.put(MessageQueueItem(role="user", content="C1", priority=5, cancellable=True))
    await queue.put(MessageQueueItem(role="user", content="NC1", priority=5, cancellable=False))
    await queue.put(MessageQueueItem(role="user", content="C2", priority=8, cancellable=True))

    # Cancel all
    await queue.cancel_all()

    # Assert: Queue marked as cancelled
    assert queue.is_cancelled()

    # Assert: Only non-cancellable items remain
    assert queue.qsize() == 1, "Only 1 non-cancellable item should remain"

    # Non-cancellable item still retrievable
    item = await queue.get()
    assert item.content == "NC1"

    # Further get() should raise
    with pytest.raises(ExecutionAbortedError):
        await asyncio.wait_for(queue.get(), timeout=0.1)


@pytest.mark.unit
async def test_fifo_within_priority():
    """Test same priority messages follow FIFO order (T036)."""
    queue = MessageQueue()

    # Add 5 messages with same priority
    for i in range(5):
        await queue.put(MessageQueueItem(role="user", content=f"Message{i}", priority=5))

    # Assert: Dequeued in insertion order
    for i in range(5):
        item = await queue.get()
        assert item.content == f"Message{i}", f"Expected Message{i} in FIFO order"


@pytest.mark.unit
async def test_external_cancel_token():
    """Test external cancel token integration."""
    cancel_token = asyncio.Event()
    queue = MessageQueue(cancel_token=cancel_token)

    await queue.put(MessageQueueItem(role="user", content="Task", priority=5))

    # Set external cancel token
    cancel_token.set()

    # Assert: Queue reports as cancelled
    assert queue.is_cancelled()

    # Assert: Get raises ExecutionAbortedError
    with pytest.raises(ExecutionAbortedError):
        await queue.get()


@pytest.mark.unit
async def test_empty_queue():
    """Test empty queue behavior."""
    queue = MessageQueue()

    assert queue.is_empty()
    assert queue.qsize() == 0

    await queue.put(MessageQueueItem(role="user", content="Test", priority=5))

    assert not queue.is_empty()
    assert queue.qsize() == 1


@pytest.mark.unit
async def test_peek():
    """Test peek() without removing item."""
    queue = MessageQueue()

    # Peek empty queue
    assert await queue.peek() is None

    # Add item
    await queue.put(MessageQueueItem(role="user", content="Test", priority=5))

    # Peek should return item without removing
    peeked = await queue.peek()
    assert peeked is not None
    assert peeked.content == "Test"

    # Queue still has item
    assert queue.qsize() == 1

    # Get should return same item
    item = await queue.get()
    assert item.content == "Test"
