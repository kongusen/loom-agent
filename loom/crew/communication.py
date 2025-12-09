"""
Inter-Agent Communication System - Message Bus and Shared State

This module provides communication infrastructure for multi-agent collaboration,
enabling agents to exchange messages and share state in a thread-safe manner.

Design Philosophy:
- Asynchronous message passing for loose coupling
- Publish/subscribe pattern for flexible communication
- Thread-safe shared state for coordination
- Inspired by actor model and message-oriented middleware

Example:
    ```python
    from loom.crew.communication import (
        AgentMessage,
        MessageType,
        MessageBus,
        SharedState
    )

    # Create message bus
    bus = MessageBus()

    # Agent subscribes to messages
    async def handler(message: AgentMessage):
        print(f"Received: {message.content}")

    bus.subscribe("agent1", handler)

    # Agent publishes message
    message = AgentMessage(
        message_id="msg1",
        from_agent="agent2",
        to_agent="agent1",
        type=MessageType.DELEGATION,
        content="Please analyze this data",
        thread_id="thread1"
    )

    await bus.publish(message)

    # Shared state usage
    state = SharedState()
    await state.set("key", "value")
    value = await state.get("key")
    ```
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from uuid import uuid4


class MessageType(Enum):
    """
    Types of inter-agent messages.

    Attributes:
        DELEGATION: Task delegation from one agent to another
        RESULT: Result/output from task execution
        QUERY: Information request between agents
        NOTIFICATION: General notification or update
    """

    DELEGATION = "delegation"
    RESULT = "result"
    QUERY = "query"
    NOTIFICATION = "notification"


@dataclass
class AgentMessage:
    """
    Message exchanged between agents.

    An AgentMessage represents a unit of communication between agents in a crew.
    Messages can be point-to-point or broadcast.

    Attributes:
        message_id: Unique message identifier
        from_agent: Sender agent ID
        to_agent: Recipient agent ID (None for broadcast)
        type: Type of message
        content: Message payload (any serializable data)
        thread_id: Conversation thread ID
        parent_message_id: ID of parent message (for threading)
        metadata: Additional message metadata
    """

    message_id: str
    from_agent: str
    to_agent: Optional[str]
    type: MessageType
    content: Any
    thread_id: str
    parent_message_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate message"""
        if not self.message_id:
            raise ValueError("Message ID cannot be empty")
        if not self.from_agent:
            raise ValueError("Message must have a sender (from_agent)")
        if not self.thread_id:
            raise ValueError("Message must have a thread_id")

    def is_broadcast(self) -> bool:
        """Check if message is a broadcast message."""
        return self.to_agent is None

    def is_reply(self) -> bool:
        """Check if message is a reply to another message."""
        return self.parent_message_id is not None

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize message to dictionary.

        Returns:
            Dict: Message data
        """
        return {
            "message_id": self.message_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "type": self.type.value,
            "content": self.content,
            "thread_id": self.thread_id,
            "parent_message_id": self.parent_message_id,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> AgentMessage:
        """
        Deserialize message from dictionary.

        Args:
            data: Message data dictionary

        Returns:
            AgentMessage: Reconstructed message
        """
        return AgentMessage(
            message_id=data["message_id"],
            from_agent=data["from_agent"],
            to_agent=data.get("to_agent"),
            type=MessageType(data["type"]),
            content=data["content"],
            thread_id=data["thread_id"],
            parent_message_id=data.get("parent_message_id"),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"AgentMessage(id={self.message_id[:8]}..., "
            f"from={self.from_agent}, "
            f"to={self.to_agent or 'broadcast'}, "
            f"type={self.type.value})"
        )


class MessageBus:
    """
    Message bus for inter-agent communication.

    The MessageBus implements a publish/subscribe pattern for asynchronous
    message passing between agents. Agents subscribe to receive messages
    and publish messages for others to receive.

    Example:
        ```python
        bus = MessageBus()

        # Subscribe
        async def handle_message(msg: AgentMessage):
            print(f"Received: {msg.content}")

        bus.subscribe("agent1", handle_message)

        # Publish
        message = AgentMessage(
            message_id="msg1",
            from_agent="agent2",
            to_agent="agent1",
            type=MessageType.QUERY,
            content="What's the status?",
            thread_id="thread1"
        )

        await bus.publish(message)

        # Get thread history
        history = bus.get_thread_messages("thread1")
        ```
    """

    def __init__(self):
        """Initialize message bus."""
        self._messages: Dict[str, List[AgentMessage]] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, message: AgentMessage) -> None:
        """
        Publish message to subscribers.

        Args:
            message: Message to publish
        """
        async with self._lock:
            # Store message in thread history
            if message.thread_id not in self._messages:
                self._messages[message.thread_id] = []
            self._messages[message.thread_id].append(message)

        # Notify subscribers (outside lock to avoid deadlock)
        if message.is_broadcast():
            # Broadcast to all subscribers
            for agent_id, callbacks in self._subscribers.items():
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message)
                        else:
                            callback(message)
                    except Exception as e:
                        # Best-effort delivery - log but don't fail
                        print(f"Error delivering message to {agent_id}: {e}")
        else:
            # Point-to-point message
            if message.to_agent in self._subscribers:
                for callback in self._subscribers[message.to_agent]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message)
                        else:
                            callback(message)
                    except Exception as e:
                        print(f"Error delivering message to {message.to_agent}: {e}")

    def subscribe(self, agent_id: str, callback: Callable) -> None:
        """
        Subscribe to messages for an agent.

        Args:
            agent_id: Agent ID to subscribe for
            callback: Callback function to invoke (async or sync)
        """
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(callback)

    def unsubscribe(self, agent_id: str, callback: Optional[Callable] = None) -> None:
        """
        Unsubscribe from messages.

        Args:
            agent_id: Agent ID to unsubscribe
            callback: Specific callback to remove (None = remove all)
        """
        if agent_id not in self._subscribers:
            return

        if callback is None:
            # Remove all callbacks for this agent
            del self._subscribers[agent_id]
        else:
            # Remove specific callback
            if callback in self._subscribers[agent_id]:
                self._subscribers[agent_id].remove(callback)

            # Clean up if no callbacks left
            if not self._subscribers[agent_id]:
                del self._subscribers[agent_id]

    def get_thread_messages(self, thread_id: str) -> List[AgentMessage]:
        """
        Get all messages in a thread.

        Args:
            thread_id: Thread ID

        Returns:
            List[AgentMessage]: Messages in chronological order
        """
        return self._messages.get(thread_id, []).copy()

    def get_conversation(
        self,
        thread_id: str,
        from_agent: Optional[str] = None,
        to_agent: Optional[str] = None
    ) -> List[AgentMessage]:
        """
        Get filtered conversation from a thread.

        Args:
            thread_id: Thread ID
            from_agent: Filter by sender (optional)
            to_agent: Filter by recipient (optional)

        Returns:
            List[AgentMessage]: Filtered messages
        """
        messages = self.get_thread_messages(thread_id)

        if from_agent:
            messages = [m for m in messages if m.from_agent == from_agent]
        if to_agent:
            messages = [m for m in messages if m.to_agent == to_agent]

        return messages

    def clear_thread(self, thread_id: str) -> None:
        """
        Clear all messages in a thread.

        Args:
            thread_id: Thread ID to clear
        """
        if thread_id in self._messages:
            del self._messages[thread_id]

    def clear_all(self) -> None:
        """Clear all messages from all threads."""
        self._messages.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get message bus statistics.

        Returns:
            Dict: Statistics including message counts
        """
        total_messages = sum(len(msgs) for msgs in self._messages.values())
        return {
            "total_threads": len(self._messages),
            "total_messages": total_messages,
            "total_subscribers": len(self._subscribers),
            "subscribers_by_agent": {
                agent_id: len(callbacks)
                for agent_id, callbacks in self._subscribers.items()
            }
        }


class SharedState:
    """
    Thread-safe shared state for agent coordination.

    SharedState provides a key-value store that agents can use to share
    data in a thread-safe manner. All operations are protected by locks
    to prevent race conditions.

    Example:
        ```python
        state = SharedState()

        # Set value
        await state.set("current_phase", "research")

        # Get value
        phase = await state.get("current_phase")

        # Atomic update
        await state.update("counter", lambda x: (x or 0) + 1)

        # Check existence
        if await state.has("current_phase"):
            print("Phase is set")

        # Delete value
        await state.delete("current_phase")
        ```
    """

    def __init__(self):
        """Initialize shared state."""
        self._state: Dict[str, Any] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def set(self, key: str, value: Any) -> None:
        """
        Set a value in shared state.

        Args:
            key: State key
            value: Value to store (must be serializable)
        """
        lock = await self._get_lock(key)
        async with lock:
            self._state[key] = value

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from shared state.

        Args:
            key: State key
            default: Default value if key not found

        Returns:
            Any: Stored value or default
        """
        lock = await self._get_lock(key)
        async with lock:
            return self._state.get(key, default)

    async def has(self, key: str) -> bool:
        """
        Check if key exists in shared state.

        Args:
            key: State key

        Returns:
            bool: True if key exists
        """
        lock = await self._get_lock(key)
        async with lock:
            return key in self._state

    async def delete(self, key: str) -> bool:
        """
        Delete a key from shared state.

        Args:
            key: State key

        Returns:
            bool: True if key was deleted, False if not found
        """
        lock = await self._get_lock(key)
        async with lock:
            if key in self._state:
                del self._state[key]
                return True
            return False

    async def update(self, key: str, updater: Callable[[Any], Any]) -> Any:
        """
        Atomically update a value.

        Args:
            key: State key
            updater: Function that takes current value and returns new value

        Returns:
            Any: New value after update
        """
        lock = await self._get_lock(key)
        async with lock:
            current = self._state.get(key)
            new_value = updater(current)
            self._state[key] = new_value
            return new_value

    async def keys(self) -> List[str]:
        """
        Get all keys in shared state.

        Returns:
            List[str]: List of keys
        """
        async with self._global_lock:
            return list(self._state.keys())

    async def items(self) -> Dict[str, Any]:
        """
        Get all key-value pairs.

        Returns:
            Dict: Copy of state dictionary
        """
        async with self._global_lock:
            return self._state.copy()

    async def clear(self) -> None:
        """Clear all state."""
        async with self._global_lock:
            self._state.clear()
            self._locks.clear()

    async def _get_lock(self, key: str) -> asyncio.Lock:
        """
        Get or create lock for a key.

        Args:
            key: State key

        Returns:
            asyncio.Lock: Lock for the key
        """
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]
