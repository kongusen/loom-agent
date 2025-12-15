"""
In-Memory Storage - Stream-First Implementation

Simple in-memory message storage with event streaming support.
This is the simplest memory implementation and serves as a reference
for implementing custom memory backends.

Example:
    ```python
    from loom.builtin.memory import InMemoryMemory
    from loom.core.message import Message

    memory = InMemoryMemory()

    # Non-streaming (simple)
    await memory.add_message(Message(role="user", content="Hello"))
    messages = await memory.get_messages()

    # Streaming (with events)
    async for event in memory.add_message_stream(Message(role="user", content="Hello")):
        if event.type == AgentEventType.MEMORY_ADD_COMPLETE:
            print(f"Message added at index {event.metadata['message_index']}")
    ```
"""

from __future__ import annotations

from typing import List, Optional, AsyncGenerator

from loom.core.message import Message  # Unified Message architecture
from loom.core.events import AgentEvent, AgentEventType


class InMemoryMemory:
    """
    Simple in-memory message storage with streaming event support.

    This implementation stores all messages in a Python list.
    No persistence - all data is lost when the process ends.

    Features:
    - Stream-first architecture (all core methods emit events)
    - Convenience wrappers for simple usage
    - Zero-config (no setup required)
    - Thread-safe (async-safe)

    Use cases:
    - Development and testing
    - Short-lived conversations
    - When persistence is not needed

    Example:
        ```python
        memory = InMemoryMemory()

        # Add messages
        await memory.add_message(Message(role="user", content="Hello"))
        await memory.add_message(Message(role="assistant", content="Hi!"))

        # Get all messages
        messages = await memory.get_messages()
        print(f"Total: {len(messages)} messages")

        # Get last N messages
        recent = await memory.get_messages(limit=10)

        # Clear all messages
        await memory.clear()
        ```
    """

    def __init__(self) -> None:
        """Initialize empty in-memory storage."""
        self._messages: List[Message] = []

    # ===== Core Streaming Methods =====

    async def add_message_stream(
        self, message: Message
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Add message to memory with streaming events (CORE METHOD).

        This is the core implementation. All message additions flow through here.

        Args:
            message: Message to add to memory

        Yields:
            AgentEvent: Streaming events:
                - MEMORY_ADD_START: Operation started
                - MEMORY_ADD_COMPLETE: Message added successfully

        Example:
            ```python
            async for event in memory.add_message_stream(msg):
                if event.type == AgentEventType.MEMORY_ADD_START:
                    print("Adding message...")
                elif event.type == AgentEventType.MEMORY_ADD_COMPLETE:
                    idx = event.metadata['message_index']
                    total = event.metadata['total_messages']
                    print(f"Added message {idx} (total: {total})")
            ```
        """
        # Emit start event
        yield AgentEvent(
            type=AgentEventType.MEMORY_ADD_START,
            metadata={
                "role": message.role,
                "content_length": len(message.content) if message.content else 0
            }
        )

        # Add message to storage
        self._messages.append(message)

        # Emit complete event
        yield AgentEvent(
            type=AgentEventType.MEMORY_ADD_COMPLETE,
            metadata={
                "message_index": len(self._messages) - 1,
                "total_messages": len(self._messages),
                "role": message.role
            }
        )

    async def get_messages_stream(
        self, limit: Optional[int] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Get messages from memory with streaming events (CORE METHOD).

        This is the core implementation. All message retrieval flows through here.

        Args:
            limit: Optional limit on number of messages to return.
                  If None, returns all messages.
                  If positive, returns last N messages.

        Yields:
            AgentEvent: Streaming events:
                - MEMORY_LOAD_START: Load started
                - MEMORY_MESSAGES_LOADED: Messages loaded (contains messages in metadata)

        Example:
            ```python
            async for event in memory.get_messages_stream(limit=10):
                if event.type == AgentEventType.MEMORY_LOAD_START:
                    print("Loading messages...")
                elif event.type == AgentEventType.MEMORY_MESSAGES_LOADED:
                    messages = event.metadata["messages"]
                    print(f"Loaded {len(messages)} messages")
            ```
        """
        # Emit start event
        yield AgentEvent(
            type=AgentEventType.MEMORY_LOAD_START,
            metadata={
                "limit": limit,
                "total_available": len(self._messages)
            }
        )

        # Get messages (apply limit if specified)
        if limit is not None:
            messages = self._messages[-limit:] if limit > 0 else []
        else:
            messages = self._messages.copy()

        # Emit loaded event with messages
        yield AgentEvent(
            type=AgentEventType.MEMORY_MESSAGES_LOADED,
            metadata={
                "messages": messages,
                "count": len(messages),
                "total": len(self._messages),
                "limit": limit
            }
        )

    async def clear_stream(self) -> AsyncGenerator[AgentEvent, None]:
        """
        Clear all messages from memory with streaming events (CORE METHOD).

        This is the core implementation. All clear operations flow through here.

        Yields:
            AgentEvent: Streaming events:
                - MEMORY_CLEAR_START: Clear started
                - MEMORY_CLEAR_COMPLETE: All messages cleared

        Example:
            ```python
            async for event in memory.clear_stream():
                if event.type == AgentEventType.MEMORY_CLEAR_START:
                    print("Clearing memory...")
                elif event.type == AgentEventType.MEMORY_CLEAR_COMPLETE:
                    print("Memory cleared")
            ```
        """
        # Emit start event
        messages_before = len(self._messages)
        yield AgentEvent(
            type=AgentEventType.MEMORY_CLEAR_START,
            metadata={"messages_count": messages_before}
        )

        # Clear messages
        self._messages.clear()

        # Emit complete event
        yield AgentEvent(
            type=AgentEventType.MEMORY_CLEAR_COMPLETE,
            metadata={
                "messages_cleared": messages_before,
                "messages_remaining": len(self._messages)
            }
        )

    # ===== Convenience Wrappers =====

    async def add_message(self, message: Message) -> None:
        """
        Add message to memory (convenience wrapper).

        This method consumes add_message_stream() internally.
        Use this when you don't need real-time event streaming.

        Args:
            message: Message to add

        Example:
            ```python
            await memory.add_message(Message(role="user", content="Hello"))
            ```
        """
        async for event in self.add_message_stream(message):
            pass  # Just consume the stream

    async def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """
        Get messages from memory (convenience wrapper).

        This method consumes get_messages_stream() internally.
        Use this when you don't need real-time event streaming.

        Args:
            limit: Optional limit on number of messages

        Returns:
            List[Message]: Messages from memory

        Example:
            ```python
            # Get all messages
            all_messages = await memory.get_messages()

            # Get last 10 messages
            recent = await memory.get_messages(limit=10)
            ```
        """
        messages = []
        async for event in self.get_messages_stream(limit):
            if event.type == AgentEventType.MEMORY_MESSAGES_LOADED:
                messages = event.metadata.get("messages", [])
        return messages

    async def clear(self) -> None:
        """
        Clear all messages from memory (convenience wrapper).

        This method consumes clear_stream() internally.
        Use this when you don't need real-time event streaming.

        Example:
            ```python
            await memory.clear()
            print("All messages cleared")
            ```
        """
        async for event in self.clear_stream():
            pass  # Just consume the stream

    # ===== Optional Persistence Methods =====

    async def save(self, path: str) -> None:
        """
        No-op for in-memory storage (no persistence).

        InMemoryMemory does not support persistence.
        Use PersistentMemory for disk storage.

        Args:
            path: Ignored (for interface compatibility)
        """
        pass

    async def load(self, path: str) -> None:
        """
        No-op for in-memory storage (no persistence).

        InMemoryMemory does not support persistence.
        Use PersistentMemory for disk loading.

        Args:
            path: Ignored (for interface compatibility)
        """
        pass

    # ===== Utility Methods =====

    def __len__(self) -> int:
        """Get number of messages in memory."""
        return len(self._messages)

    def __repr__(self) -> str:
        """Human-readable representation."""
        return f"InMemoryMemory(messages={len(self._messages)})"
