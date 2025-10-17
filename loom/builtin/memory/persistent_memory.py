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

from loom.core.types import Message
from loom.interfaces.memory import BaseMemory


class PersistentMemory(BaseMemory):
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

    async def add_message(self, message: Message) -> None:
        """Add message to memory and persist."""
        async with self._lock:
            self._messages.append(message)
            self._save_to_disk()

    async def get_messages(self) -> List[Message]:
        """Get all messages from memory."""
        async with self._lock:
            return self._messages.copy()

    async def clear(self) -> None:
        """Clear all messages from memory."""
        async with self._lock:
            self._messages.clear()
            self._compression_metadata.clear()
            self._save_to_disk()

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
