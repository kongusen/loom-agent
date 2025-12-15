"""US6: Three-Tier Memory System

Provides a practical memory system with automatic persistence for agent conversations.

Tiers:
1. Short-term: In-memory message array (current session)
2. Mid-term: Compression summaries with metadata (managed by CompressionManager)
3. Long-term: JSON file persistence for cross-session recall

Design goals:
- Simple API for developers
- Automatic backup and recovery
- Zero-config defaults with customization options
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import asyncio

from typing import AsyncGenerator

from loom.core.message import Message  # Unified Message architecture
from loom.core.events import AgentEvent, AgentEventType


class PersistentMemory:
    """Three-tier memory with automatic persistence.

    Example:
        # Simple usage - auto-creates .loom directory
        memory = PersistentMemory()

        # Custom persistence path
        memory = PersistentMemory(persist_dir=".my_agent_memory")

        # Disable persistence
        memory = PersistentMemory(enable_persistence=False)
    """

    def __init__(
        self,
        persist_dir: str = ".loom",
        session_id: Optional[str] = None,
        enable_persistence: bool = True,
        auto_backup: bool = True,
        max_backup_files: int = 5,
    ):
        """Initialize persistent memory.

        Args:
            persist_dir: Directory for persisting memory (default: .loom)
            session_id: Session identifier (default: auto-generated timestamp)
            enable_persistence: Enable file persistence (default: True)
            auto_backup: Create backup before overwriting (default: True)
            max_backup_files: Maximum backup files to keep (default: 5)
        """
        self.persist_dir = Path(persist_dir)
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.enable_persistence = enable_persistence
        self.auto_backup = auto_backup
        self.max_backup_files = max_backup_files

        # Tier 1: Short-term (in-memory)
        self._messages: List[Message] = []

        # Tier 2: Mid-term (compression metadata - managed externally)
        self._compression_metadata: List[dict] = []

        # Setup persistence
        if self.enable_persistence:
            self._ensure_persist_dir()
            self._load_from_disk()

        self._lock = asyncio.Lock()

    def _ensure_persist_dir(self) -> None:
        """Create persistence directory if it doesn't exist."""
        self.persist_dir.mkdir(parents=True, exist_ok=True)

    def _get_memory_file(self) -> Path:
        """Get path to memory file."""
        return self.persist_dir / f"session_{self.session_id}.json"

    def _get_backup_file(self, index: int) -> Path:
        """Get path to backup file."""
        return self.persist_dir / f"session_{self.session_id}.backup{index}.json"

    def _load_from_disk(self) -> None:
        """Load memory from disk if exists."""
        memory_file = self._get_memory_file()
        if not memory_file.exists():
            return

        try:
            with open(memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load messages
            self._messages = [
                Message(**msg_data) for msg_data in data.get('messages', [])
            ]

            # Load compression metadata
            self._compression_metadata = data.get('compression_metadata', [])

        except Exception as e:
            # Try to recover from backup
            if self._recover_from_backup():
                return
            # If recovery fails, start fresh
            print(f"Warning: Failed to load memory from disk: {e}")
            self._messages = []
            self._compression_metadata = []

    def _save_to_disk(self) -> None:
        """Save memory to disk with optional backup."""
        if not self.enable_persistence:
            return

        memory_file = self._get_memory_file()

        try:
            # Create backup if file exists
            if self.auto_backup and memory_file.exists():
                self._create_backup()

            # Save current state
            data = {
                'session_id': self.session_id,
                'timestamp': datetime.now().isoformat(),
                'messages': [self._message_to_dict(m) for m in self._messages],
                'compression_metadata': self._compression_metadata,
            }

            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Warning: Failed to save memory to disk: {e}")

    def _message_to_dict(self, message: Message) -> dict:
        """Convert Message to JSON-serializable dict."""
        return {
            'role': message.role,
            'content': message.content,
            'tool_call_id': message.tool_call_id,
            'metadata': message.metadata,
        }

    def _create_backup(self) -> None:
        """Create backup of current memory file."""
        memory_file = self._get_memory_file()
        if not memory_file.exists():
            return

        # Rotate existing backups
        for i in range(self.max_backup_files - 1, 0, -1):
            old_backup = self._get_backup_file(i)
            new_backup = self._get_backup_file(i + 1)
            if old_backup.exists():
                old_backup.rename(new_backup)

        # Create new backup
        backup_file = self._get_backup_file(1)
        memory_file.rename(backup_file)

        # Clean up old backups
        self._cleanup_old_backups()

    def _cleanup_old_backups(self) -> None:
        """Remove backups exceeding max_backup_files."""
        for i in range(self.max_backup_files + 1, self.max_backup_files + 10):
            backup_file = self._get_backup_file(i)
            if backup_file.exists():
                backup_file.unlink()

    def _recover_from_backup(self) -> bool:
        """Attempt to recover from most recent backup.

        Returns:
            True if recovery successful, False otherwise
        """
        for i in range(1, self.max_backup_files + 1):
            backup_file = self._get_backup_file(i)
            if not backup_file.exists():
                continue

            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._messages = [
                    Message(**msg_data) for msg_data in data.get('messages', [])
                ]
                self._compression_metadata = data.get('compression_metadata', [])

                print(f"Successfully recovered from backup {i}")
                return True

            except Exception as e:
                print(f"Failed to recover from backup {i}: {e}")
                continue

        return False

    # ===== Core Streaming Methods (Stream-First Architecture) =====

    async def add_message_stream(
        self, message: Message
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Add message to memory with streaming events (CORE METHOD).

        Includes persistence events for disk I/O operations.

        Args:
            message: Message to add to memory

        Yields:
            AgentEvent: Streaming events:
                - MEMORY_ADD_START: Operation started
                - MEMORY_SAVE_START: Saving to disk (if persistence enabled)
                - MEMORY_SAVE_COMPLETE: Saved successfully
                - MEMORY_ADD_COMPLETE: Message added
                - MEMORY_ERROR: Operation failed

        Example:
            ```python
            async for event in memory.add_message_stream(msg):
                if event.type == AgentEventType.MEMORY_SAVE_START:
                    print("Saving to disk...")
                elif event.type == AgentEventType.MEMORY_ADD_COMPLETE:
                    print(f"Added message {event.metadata['message_index']}")
            ```
        """
        # Emit start event
        yield AgentEvent(
            type=AgentEventType.MEMORY_ADD_START,
            metadata={
                "role": message.role,
                "content_length": len(message.content) if message.content else 0,
                "persistence_enabled": self.enable_persistence
            }
        )

        try:
            async with self._lock:
                # Add message to memory
                self._messages.append(message)

                # Persist to disk if enabled
                if self.enable_persistence:
                    yield AgentEvent(
                        type=AgentEventType.MEMORY_SAVE_START,
                        metadata={
                            "file": str(self._get_memory_file()),
                            "auto_backup": self.auto_backup
                        }
                    )

                    self._save_to_disk()

                    yield AgentEvent(
                        type=AgentEventType.MEMORY_SAVE_COMPLETE,
                        metadata={
                            "file": str(self._get_memory_file()),
                            "message_count": len(self._messages)
                        }
                    )

            # Emit complete event
            yield AgentEvent(
                type=AgentEventType.MEMORY_ADD_COMPLETE,
                metadata={
                    "message_index": len(self._messages) - 1,
                    "total_messages": len(self._messages),
                    "role": message.role,
                    "persisted": self.enable_persistence
                }
            )

        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.MEMORY_ERROR,
                error=e,
                metadata={
                    "operation": "add_message",
                    "error_message": str(e)
                }
            )
            raise

    async def get_messages_stream(
        self, limit: Optional[int] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Get messages from memory with streaming events (CORE METHOD).

        Args:
            limit: Optional limit on number of messages to return

        Yields:
            AgentEvent: Streaming events:
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
        # Emit start event
        yield AgentEvent(
            type=AgentEventType.MEMORY_LOAD_START,
            metadata={
                "limit": limit,
                "total_available": len(self._messages),
                "session_id": self.session_id
            }
        )

        try:
            async with self._lock:
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
                    "limit": limit,
                    "session_id": self.session_id
                }
            )

        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.MEMORY_ERROR,
                error=e,
                metadata={
                    "operation": "get_messages",
                    "error_message": str(e)
                }
            )
            raise

    async def clear_stream(self) -> AsyncGenerator[AgentEvent, None]:
        """
        Clear all messages from memory with streaming events (CORE METHOD).

        Args:
            None

        Yields:
            AgentEvent: Streaming events:
                - MEMORY_CLEAR_START: Clear started
                - MEMORY_SAVE_START: Saving cleared state (if persistence enabled)
                - MEMORY_SAVE_COMPLETE: Saved successfully
                - MEMORY_CLEAR_COMPLETE: All messages cleared
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
        # Emit start event
        messages_before = len(self._messages)
        yield AgentEvent(
            type=AgentEventType.MEMORY_CLEAR_START,
            metadata={
                "messages_count": messages_before,
                "compression_metadata_count": len(self._compression_metadata)
            }
        )

        try:
            async with self._lock:
                # Clear messages and metadata
                self._messages.clear()
                self._compression_metadata.clear()

                # Persist cleared state if enabled
                if self.enable_persistence:
                    yield AgentEvent(
                        type=AgentEventType.MEMORY_SAVE_START,
                        metadata={
                            "file": str(self._get_memory_file()),
                            "operation": "clear"
                        }
                    )

                    self._save_to_disk()

                    yield AgentEvent(
                        type=AgentEventType.MEMORY_SAVE_COMPLETE,
                        metadata={
                            "file": str(self._get_memory_file()),
                            "message_count": 0
                        }
                    )

            # Emit complete event
            yield AgentEvent(
                type=AgentEventType.MEMORY_CLEAR_COMPLETE,
                metadata={
                    "messages_cleared": messages_before,
                    "messages_remaining": len(self._messages),
                    "persisted": self.enable_persistence
                }
            )

        except Exception as e:
            yield AgentEvent(
                type=AgentEventType.MEMORY_ERROR,
                error=e,
                metadata={
                    "operation": "clear",
                    "error_message": str(e)
                }
            )
            raise

    # ===== Convenience Wrappers =====

    async def add_message(self, message: Message) -> None:
        """Add message to memory and persist (convenience wrapper)."""
        async for event in self.add_message_stream(message):
            pass  # Just consume the stream

    async def get_messages(self, limit: Optional[int] = None) -> List[Message]:
        """Get messages from memory (convenience wrapper)."""
        messages = []
        async for event in self.get_messages_stream(limit):
            if event.type == AgentEventType.MEMORY_MESSAGES_LOADED:
                messages = event.metadata.get("messages", [])
        return messages

    async def clear(self) -> None:
        """Clear all messages from memory (convenience wrapper)."""
        async for event in self.clear_stream():
            pass  # Just consume the stream

    async def set_messages(self, messages: List[Message]) -> None:
        """Replace all messages in memory.

        Used by CompressionManager when compressing history.
        """
        async with self._lock:
            self._messages = messages.copy()
            self._save_to_disk()

    def add_compression_metadata(self, metadata: dict) -> None:
        """Add compression metadata (Tier 2).

        Called by CompressionManager to track compression events.
        """
        self._compression_metadata.append({
            'timestamp': datetime.now().isoformat(),
            **metadata
        })
        self._save_to_disk()

    def get_compression_history(self) -> List[dict]:
        """Get compression history metadata."""
        return self._compression_metadata.copy()

    def get_persistence_info(self) -> dict:
        """Get information about persistence state.

        Useful for debugging and monitoring.
        """
        memory_file = self._get_memory_file()

        backup_files = []
        for i in range(1, self.max_backup_files + 1):
            backup = self._get_backup_file(i)
            if backup.exists():
                backup_files.append({
                    'index': i,
                    'path': str(backup),
                    'size_bytes': backup.stat().st_size,
                    'modified': datetime.fromtimestamp(backup.stat().st_mtime).isoformat(),
                })

        return {
            'enabled': self.enable_persistence,
            'session_id': self.session_id,
            'persist_dir': str(self.persist_dir),
            'memory_file': str(memory_file),
            'memory_file_exists': memory_file.exists(),
            'message_count': len(self._messages),
            'compression_event_count': len(self._compression_metadata),
            'backups': backup_files,
        }
