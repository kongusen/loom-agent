"""
Memory Interface - Stream-First Architecture

This module defines the unified memory interface for loom-agent using Protocol
(similar to BaseLLM) and stream-first architecture (similar to Crew).

Design Philosophy:
- Protocol-based typing (no ABC inheritance required)
- Stream-first: Core methods return AsyncGenerator[AgentEvent]
- Convenience wrappers: Non-streaming methods consume streams
- Event-driven: All operations emit events for observability

Migration from v0.0.x:
    Old (ABC-based):
        class MyMemory(BaseMemory):
            async def add_message(self, message: Message) -> None: ...

    New (Protocol-based):
        class MyMemory:
            # Core streaming methods
            async def add_message_stream(self, message: Message) -> AsyncGenerator[AgentEvent, None]:
                yield AgentEvent(type=AgentEventType.MEMORY_ADD_START, ...)
                # ... do work ...
                yield AgentEvent(type=AgentEventType.MEMORY_ADD_COMPLETE, ...)

            # Convenience wrapper
            async def add_message(self, message: Message) -> None:
                async for event in self.add_message_stream(message):
                    pass  # Consume stream

Example:
    ```python
    from loom.builtin.memory import InMemoryMemory

    memory = InMemoryMemory()

    # Non-streaming (simple)
    await memory.add_message(Message(role="user", content="Hello"))
    messages = await memory.get_messages()

    # Streaming (real-time events)
    async for event in memory.add_message_stream(Message(role="user", content="Hello")):
        if event.type == AgentEventType.MEMORY_ADD_COMPLETE:
            print(f"Added message {event.metadata['message_index']}")
    ```
"""

from __future__ import annotations

from typing import Protocol, AsyncGenerator, Optional, List, Any
from typing_extensions import runtime_checkable

# Import will be resolved at runtime to avoid circular dependency
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from loom.core.types import Message
    from loom.core.events import AgentEvent


@runtime_checkable
class BaseMemory(Protocol):
    """
    Memory interface - Stream-first architecture with Protocol typing.

    **Why Protocol?**

    1. **Duck typing** - No inheritance required, just implement the methods
    2. **Runtime checkable** - Supports isinstance() checks
    3. **Zero coupling** - No need to import base class
    4. **Consistency** - Matches BaseLLM interface style

    **Stream-First Architecture:**

    Core methods (*_stream) yield events and are the source of truth.
    Convenience methods (no suffix) consume streams internally.

    **Required Methods:**

    You must implement these core streaming methods:

    1. :meth:`add_message_stream` - Add message with events
    2. :meth:`get_messages_stream` - Load messages with events
    3. :meth:`clear_stream` - Clear messages with events

    Convenience wrappers are typically implemented by consuming the streams:

    4. :meth:`add_message` - Wrapper around add_message_stream()
    5. :meth:`get_messages` - Wrapper around get_messages_stream()
    6. :meth:`clear` - Wrapper around clear_stream()

    **Event Flow:**

    Each streaming method should yield events in this pattern:

    1. START event (e.g., MEMORY_ADD_START)
    2. Optional progress/data events
    3. COMPLETE event (e.g., MEMORY_ADD_COMPLETE)
    4. On error: ERROR event instead of COMPLETE

    **Implementation Example:**

    .. code-block:: python

        class MyMemory:
            def __init__(self):
                self._messages = []

            async def add_message_stream(
                self, message: Message
            ) -> AsyncGenerator[AgentEvent, None]:
                \"\"\"Core streaming implementation\"\"\"
                from loom.core.events import AgentEvent, AgentEventType

                yield AgentEvent(
                    type=AgentEventType.MEMORY_ADD_START,
                    metadata={"role": message.role}
                )

                self._messages.append(message)

                yield AgentEvent(
                    type=AgentEventType.MEMORY_ADD_COMPLETE,
                    metadata={
                        "message_index": len(self._messages) - 1,
                        "total_messages": len(self._messages)
                    }
                )

            async def add_message(self, message: Message) -> None:
                \"\"\"Convenience wrapper\"\"\"
                async for event in self.add_message_stream(message):
                    pass  # Just consume the stream

            async def get_messages_stream(
                self, limit: Optional[int] = None
            ) -> AsyncGenerator[AgentEvent, None]:
                \"\"\"Core streaming implementation\"\"\"
                from loom.core.events import AgentEvent, AgentEventType

                yield AgentEvent(
                    type=AgentEventType.MEMORY_LOAD_START,
                    metadata={"limit": limit}
                )

                messages = self._messages[-limit:] if limit else self._messages.copy()

                yield AgentEvent(
                    type=AgentEventType.MEMORY_MESSAGES_LOADED,
                    metadata={
                        "messages": messages,
                        "count": len(messages),
                        "total": len(self._messages)
                    }
                )

            async def get_messages(
                self, limit: Optional[int] = None
            ) -> List[Message]:
                \"\"\"Convenience wrapper\"\"\"
                messages = []
                async for event in self.get_messages_stream(limit):
                    if event.type == AgentEventType.MEMORY_MESSAGES_LOADED:
                        messages = event.metadata.get("messages", [])
                return messages

            async def clear_stream(self) -> AsyncGenerator[AgentEvent, None]:
                \"\"\"Core streaming implementation\"\"\"
                from loom.core.events import AgentEvent, AgentEventType

                yield AgentEvent(type=AgentEventType.MEMORY_CLEAR_START)

                self._messages.clear()

                yield AgentEvent(type=AgentEventType.MEMORY_CLEAR_COMPLETE)

            async def clear(self) -> None:
                \"\"\"Convenience wrapper\"\"\"
                async for event in self.clear_stream():
                    pass

    **Type Checking:**

    .. code-block:: python

        from loom.interfaces.memory import BaseMemory, is_memory

        def use_memory(memory: BaseMemory):
            # Runtime check
            assert is_memory(memory), "Must implement BaseMemory protocol"

            # Type-safe usage
            await memory.add_message(msg)

    **Optional Methods:**

    For persistence support:

    - :meth:`save` - Save memory to disk
    - :meth:`load` - Load memory from disk
    """

    # ===== Core Streaming Methods (REQUIRED) =====

    async def add_message_stream(
        self, message: "Message"
    ) -> AsyncGenerator["AgentEvent", None]:
        """
        Add message to memory with streaming events (CORE METHOD).

        This is the core implementation. The convenience method add_message()
        should consume this stream.

        Args:
            message: Message to add

        Yields:
            AgentEvent: Events including:
                - MEMORY_ADD_START: Operation started
                - MEMORY_ADD_COMPLETE: Operation completed
                - MEMORY_ERROR: Operation failed

        Example:
            ```python
            async for event in memory.add_message_stream(message):
                if event.type == AgentEventType.MEMORY_ADD_START:
                    print("Adding message...")
                elif event.type == AgentEventType.MEMORY_ADD_COMPLETE:
                    print(f"Added at index {event.metadata['message_index']}")
            ```
        """
        ...

    async def get_messages_stream(
        self, limit: Optional[int] = None
    ) -> AsyncGenerator["AgentEvent", None]:
        """
        Load messages from memory with streaming events (CORE METHOD).

        This is the core implementation. The convenience method get_messages()
        should consume this stream.

        Args:
            limit: Optional limit on number of messages to return
                  (None = return all messages)

        Yields:
            AgentEvent: Events including:
                - MEMORY_LOAD_START: Load started
                - MEMORY_MESSAGES_LOADED: Messages loaded (contains messages in metadata)
                - MEMORY_ERROR: Load failed

        Example:
            ```python
            async for event in memory.get_messages_stream(limit=10):
                if event.type == AgentEventType.MEMORY_MESSAGES_LOADED:
                    messages = event.metadata["messages"]
                    print(f"Loaded {len(messages)} messages")
            ```
        """
        ...

    async def clear_stream(self) -> AsyncGenerator["AgentEvent", None]:
        """
        Clear all messages from memory with streaming events (CORE METHOD).

        This is the core implementation. The convenience method clear()
        should consume this stream.

        Yields:
            AgentEvent: Events including:
                - MEMORY_CLEAR_START: Clear started
                - MEMORY_CLEAR_COMPLETE: Clear completed
                - MEMORY_ERROR: Clear failed

        Example:
            ```python
            async for event in memory.clear_stream():
                if event.type == AgentEventType.MEMORY_CLEAR_START:
                    print("Clearing memory...")
                elif event.type == AgentEventType.MEMORY_CLEAR_COMPLETE:
                    print("Memory cleared")
            ```
        """
        ...

    # ===== Convenience Wrappers (REQUIRED) =====

    async def add_message(self, message: "Message") -> None:
        """
        Add message to memory (convenience wrapper).

        This method should consume add_message_stream() internally.
        Use this when you don't need real-time event streaming.

        Args:
            message: Message to add

        Example:
            ```python
            await memory.add_message(Message(role="user", content="Hello"))
            ```
        """
        ...

    async def get_messages(self, limit: Optional[int] = None) -> List["Message"]:
        """
        Get messages from memory (convenience wrapper).

        This method should consume get_messages_stream() internally.
        Use this when you don't need real-time event streaming.

        Args:
            limit: Optional limit on number of messages

        Returns:
            List[Message]: Messages from memory

        Example:
            ```python
            messages = await memory.get_messages(limit=10)
            print(f"Got {len(messages)} messages")
            ```
        """
        ...

    async def clear(self) -> None:
        """
        Clear all messages from memory (convenience wrapper).

        This method should consume clear_stream() internally.
        Use this when you don't need real-time event streaming.

        Example:
            ```python
            await memory.clear()
            ```
        """
        ...

    # ===== Optional Persistence Methods =====

    async def save(self, path: str) -> None:
        """
        Save memory to disk (optional).

        Implementations can override this for persistence support.
        Default implementation does nothing.

        Args:
            path: Path to save memory
        """
        return None

    async def load(self, path: str) -> None:
        """
        Load memory from disk (optional).

        Implementations can override this for persistence support.
        Default implementation does nothing.

        Args:
            path: Path to load memory from
        """
        return None


# ===== Utility Functions =====

def is_memory(obj: Any) -> bool:
    """
    Check if object implements BaseMemory protocol.

    Args:
        obj: Object to check

    Returns:
        bool: True if object implements BaseMemory

    Example:
        ```python
        from loom.builtin.memory import InMemoryMemory
        from loom.interfaces.memory import is_memory

        memory = InMemoryMemory()
        assert is_memory(memory)  # True

        not_memory = "string"
        assert not is_memory(not_memory)  # False
        ```
    """
    return isinstance(obj, BaseMemory)


def validate_memory(obj: Any, name: str = "memory") -> None:
    """
    Validate object implements BaseMemory protocol, otherwise raise exception.

    Args:
        obj: Object to validate
        name: Parameter name (for error message)

    Raises:
        TypeError: If object doesn't implement BaseMemory

    Example:
        ```python
        from loom.interfaces.memory import validate_memory

        def use_memory(memory):
            validate_memory(memory)  # Ensures protocol compliance
            await memory.add_message(msg)
        ```
    """
    if not isinstance(obj, BaseMemory):
        raise TypeError(
            f"{name} must implement BaseMemory protocol. "
            f"Got {type(obj).__name__} which is missing required methods. "
            f"Required: add_message_stream(), get_messages_stream(), clear_stream(), "
            f"add_message(), get_messages(), clear()"
        )
