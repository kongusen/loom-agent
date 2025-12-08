"""
Event Journal: Append-Only Event Log for Event Sourcing

This module implements event sourcing for loom-agent, enabling:
- Complete execution replay
- Time-travel debugging
- Crash recovery
- Audit logging

Design Philosophy:
- Append-only log (immutable history)
- JSON Lines format (simple, streaming-friendly)
- Thread-based isolation (multi-conversation support)
- Batched writes (performance optimization)

Key Advantage over LangGraph's Checkpointing:
- LangGraph: Static state snapshots (fixed at capture time)
- loom-agent: Event streams (can be replayed with new strategies)

Example:
    ```python
    # Create journal
    journal = EventJournal(storage_path=Path("./logs"))

    # Record events during execution
    async for event in agent.execute(prompt):
        await journal.append(event, thread_id="user-123")

    # Replay events for recovery
    events = await journal.replay(thread_id="user-123")
    reconstructed_state = await StateReconstructor.reconstruct(events)

    # Continue from where we left off
    async for event in agent.execute(None, initial_frame=reconstructed_state):
        print(event)
    ```
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, List, Optional, Dict, Any
import time

from .events import AgentEvent, AgentEventType


@dataclass
class EventRecord:
    """
    Wrapper for an event with additional metadata for journaling.

    Attributes:
        event: The actual AgentEvent
        thread_id: Thread/conversation identifier
        sequence_number: Monotonically increasing sequence number
        recorded_at: When this event was recorded to journal
    """
    event: AgentEvent
    thread_id: str
    sequence_number: int
    recorded_at: float


class EventJournal:
    """
    Append-only event journal using JSON Lines format.

    Features:
    - Thread isolation (each conversation has separate event stream)
    - Batched writes (reduces I/O overhead)
    - Async I/O (non-blocking)
    - Automatic flushing (configurable interval)
    - Query by thread_id, time range, event type

    Storage Format:
        events.jsonl - Single file with one JSON object per line
        Each line: {"event": {...}, "thread_id": "...", "seq": 123, "recorded_at": ...}

    Thread Safety:
        Uses asyncio locks for concurrent access protection
    """

    def __init__(
        self,
        storage_path: Path,
        batch_size: int = 100,
        flush_interval: float = 1.0,
        enable_compression: bool = False
    ):
        """
        Initialize event journal.

        Args:
            storage_path: Directory to store journal files
            batch_size: Number of events to batch before writing
            flush_interval: Maximum seconds to wait before flushing
            enable_compression: Whether to compress journal files (future feature)
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.journal_file = self.storage_path / "events.jsonl"
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.enable_compression = enable_compression

        # Batching state
        self._buffer: List[EventRecord] = []
        self._lock = asyncio.Lock()
        self._sequence_counter = 0
        self._last_flush = time.time()

        # Background flushing task
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start background flushing task."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._auto_flush_loop())

    async def stop(self):
        """Stop background flushing and flush remaining events."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()

    async def append(self, event: AgentEvent, thread_id: str):
        """
        Append an event to the journal.

        Args:
            event: The event to record
            thread_id: Thread/conversation identifier

        This method is async and batched for performance.
        Events are buffered and written in batches.
        """
        async with self._lock:
            self._sequence_counter += 1

            record = EventRecord(
                event=event,
                thread_id=thread_id,
                sequence_number=self._sequence_counter,
                recorded_at=time.time()
            )

            self._buffer.append(record)

            # Flush if batch is full
            if len(self._buffer) >= self.batch_size:
                await self._flush_internal()

    async def flush(self):
        """Manually flush buffered events to disk."""
        async with self._lock:
            await self._flush_internal()

    async def _flush_internal(self):
        """Internal flush implementation (requires lock)."""
        if not self._buffer:
            return

        # Serialize events
        lines = []
        for record in self._buffer:
            line_data = {
                "event": self._serialize_event(record.event),
                "thread_id": record.thread_id,
                "seq": record.sequence_number,
                "recorded_at": record.recorded_at
            }
            lines.append(json.dumps(line_data))

        # Write to file (async)
        await asyncio.to_thread(self._write_lines, lines)

        # Clear buffer
        self._buffer.clear()
        self._last_flush = time.time()

    def _write_lines(self, lines: List[str]):
        """Synchronous file write (called in thread pool)."""
        with self.journal_file.open("a") as f:
            for line in lines:
                f.write(line + "\n")

    async def _auto_flush_loop(self):
        """Background task that flushes on interval."""
        while True:
            await asyncio.sleep(self.flush_interval)

            async with self._lock:
                if self._buffer and (time.time() - self._last_flush) >= self.flush_interval:
                    await self._flush_internal()

    def _serialize_event(self, event: AgentEvent) -> Dict[str, Any]:
        """
        Serialize AgentEvent to dict.

        Args:
            event: Event to serialize

        Returns:
            Dict: JSON-serializable representation
        """
        return {
            "type": event.type.value,
            "timestamp": event.timestamp,
            "phase": event.phase,
            "content": event.content,
            "tool_call": self._serialize_tool_call(event.tool_call) if event.tool_call and hasattr(event.tool_call, 'id') else None,
            "tool_result": self._serialize_tool_result(event.tool_result) if event.tool_result and hasattr(event.tool_result, 'tool_call_id') else None,
            "error": str(event.error) if event.error else None,
            "metadata": event.metadata,
            "iteration": event.iteration,
            "turn_id": event.turn_id
        }

    def _serialize_tool_call(self, tool_call) -> Dict[str, Any]:
        """Serialize ToolCall to dict."""
        return {
            "id": tool_call.id,
            "name": tool_call.name,
            "arguments": tool_call.arguments
        }

    def _serialize_tool_result(self, tool_result) -> Dict[str, Any]:
        """Serialize ToolResult to dict."""
        return {
            "tool_call_id": tool_result.tool_call_id,
            "tool_name": tool_result.tool_name,
            "content": tool_result.content,
            "is_error": tool_result.is_error,
            "execution_time_ms": tool_result.execution_time_ms,
            "metadata": tool_result.metadata
        }

    # ===== Query Methods =====

    async def replay(
        self,
        thread_id: str,
        after_sequence: Optional[int] = None,
        before_sequence: Optional[int] = None,
        event_types: Optional[List[AgentEventType]] = None
    ) -> List[AgentEvent]:
        """
        Replay events for a specific thread.

        Args:
            thread_id: Thread to replay
            after_sequence: Only events after this sequence number
            before_sequence: Only events before this sequence number
            event_types: Filter by event types

        Returns:
            List[AgentEvent]: Events in chronological order

        Example:
            ```python
            # Replay all events for thread
            events = await journal.replay(thread_id="user-123")

            # Replay only recent events
            events = await journal.replay(
                thread_id="user-123",
                after_sequence=1000
            )

            # Replay only LLM and tool events
            events = await journal.replay(
                thread_id="user-123",
                event_types=[
                    AgentEventType.LLM_DELTA,
                    AgentEventType.TOOL_RESULT
                ]
            )
            ```
        """
        events = []

        # Read file (async)
        lines = await asyncio.to_thread(self._read_all_lines)

        for line in lines:
            try:
                record_data = json.loads(line)

                # Filter by thread_id
                if record_data["thread_id"] != thread_id:
                    continue

                # Filter by sequence
                seq = record_data["seq"]
                if after_sequence is not None and seq <= after_sequence:
                    continue
                if before_sequence is not None and seq >= before_sequence:
                    continue

                # Deserialize event
                event = self._deserialize_event(record_data["event"])

                # Filter by event type
                if event_types and event.type not in event_types:
                    continue

                events.append(event)

            except (json.JSONDecodeError, KeyError) as e:
                # Skip corrupted lines
                print(f"Warning: Failed to parse journal line: {e}")
                continue

        return events

    def _read_all_lines(self) -> List[str]:
        """Synchronous file read (called in thread pool)."""
        if not self.journal_file.exists():
            return []

        with self.journal_file.open("r") as f:
            return f.readlines()

    def _deserialize_event(self, data: Dict[str, Any]) -> AgentEvent:
        """
        Deserialize AgentEvent from dict.

        Args:
            data: Dictionary from _serialize_event()

        Returns:
            AgentEvent: Reconstructed event
        """
        from .events import ToolCall, ToolResult

        # Reconstruct tool_call if present
        tool_call = None
        if data.get("tool_call"):
            tc_data = data["tool_call"]
            tool_call = ToolCall(
                id=tc_data["id"],
                name=tc_data["name"],
                arguments=tc_data["arguments"]
            )

        # Reconstruct tool_result if present
        tool_result = None
        if data.get("tool_result"):
            tr_data = data["tool_result"]
            tool_result = ToolResult(
                tool_call_id=tr_data["tool_call_id"],
                tool_name=tr_data["tool_name"],
                content=tr_data["content"],
                is_error=tr_data.get("is_error", False),
                execution_time_ms=tr_data.get("execution_time_ms"),
                metadata=tr_data.get("metadata", {})
            )

        return AgentEvent(
            type=AgentEventType(data["type"]),
            timestamp=data["timestamp"],
            phase=data.get("phase"),
            content=data.get("content"),
            tool_call=tool_call,
            tool_result=tool_result,
            error=Exception(data["error"]) if data.get("error") else None,
            metadata=data.get("metadata", {}),
            iteration=data.get("iteration"),
            turn_id=data.get("turn_id")
        )

    # ===== Management Methods =====

    async def get_threads(self) -> List[str]:
        """
        Get all unique thread IDs in the journal.

        Returns:
            List[str]: Thread IDs
        """
        threads = set()

        lines = await asyncio.to_thread(self._read_all_lines)
        for line in lines:
            try:
                record_data = json.loads(line)
                threads.add(record_data["thread_id"])
            except (json.JSONDecodeError, KeyError):
                continue

        return sorted(threads)

    async def get_thread_info(self, thread_id: str) -> Dict[str, Any]:
        """
        Get information about a thread.

        Args:
            thread_id: Thread identifier

        Returns:
            Dict with:
                - event_count: Number of events
                - first_event_time: Timestamp of first event
                - last_event_time: Timestamp of last event
                - event_types: Counter of event types
        """
        events = await self.replay(thread_id)

        if not events:
            return {
                "event_count": 0,
                "first_event_time": None,
                "last_event_time": None,
                "event_types": {}
            }

        event_types: Dict[str, int] = {}
        for event in events:
            event_types[event.type.value] = event_types.get(event.type.value, 0) + 1

        return {
            "event_count": len(events),
            "first_event_time": events[0].timestamp,
            "last_event_time": events[-1].timestamp,
            "event_types": event_types
        }

    async def compact(self, thread_id: str, keep_recent: int = 1000):
        """
        Compact old events for a thread (future feature).

        This would replace old events with a single checkpoint event.

        Args:
            thread_id: Thread to compact
            keep_recent: Number of recent events to keep uncompacted
        """
        # TODO: Implement compaction strategy
        # 1. Get all events for thread
        # 2. Keep last N events
        # 3. Reconstruct state from older events
        # 4. Create single CHECKPOINT event with reconstructed state
        # 5. Rewrite journal without old events
        pass


class EventJournalContext:
    """
    Context manager for EventJournal with automatic start/stop.

    Example:
        ```python
        async with EventJournalContext(path) as journal:
            await journal.append(event, thread_id="user-123")
        # Automatically flushed and stopped
        ```
    """

    def __init__(self, storage_path: Path, **kwargs):
        self.journal = EventJournal(storage_path, **kwargs)

    async def __aenter__(self) -> EventJournal:
        await self.journal.start()
        return self.journal

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.journal.stop()
