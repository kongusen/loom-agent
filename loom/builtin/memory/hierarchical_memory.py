"""
Hierarchical Memory - 4-tier memory system with RAG support

Implements human-like memory hierarchy:
1. Ephemeral Memory: Tool intermediate results (temporary)
2. Working Memory: Current agent's short-term memory
3. Session Memory: Conversation mid-term memory
4. Long-term Memory: User profile, cross-session knowledge (vectorized)
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any, AsyncGenerator, Literal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import asyncio
import logging
import json

from loom.core.message import Message
from loom.core.events import AgentEvent, AgentEventType
from loom.interfaces.embedding import BaseEmbedding
from loom.interfaces.vector_store import BaseVectorStore
from loom.interfaces.retriever import Document


logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """
    Memory entry with metadata.

    Represents a single piece of memory at any tier.
    """

    id: str
    content: str
    tier: Literal["ephemeral", "working", "session", "longterm"]
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_message(self) -> Message:
        """Convert memory entry to Message object."""
        return Message(
            role=self.metadata.get("role", "assistant"),
            content=self.content,
            metadata={
                **self.metadata,
                "tier": self.tier,
                "timestamp": self.timestamp,
                "memory_id": self.id,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "tier": self.tier,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "embedding": self.embedding,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            tier=data["tier"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
        )


class HierarchicalMemory:
    """
    4-tier hierarchical memory system with RAG support.

    Memory Tiers:
    --------------
    1. **Ephemeral**: Tool call intermediate results
       - Lifetime: Single tool execution
       - Storage: Dict[str, MemoryEntry]
       - Use: Temporary computation states

    2. **Working**: Recent important memories
       - Lifetime: Current task/conversation turn
       - Storage: List[MemoryEntry] (FIFO with auto-promotion)
       - Size: Configurable (default: 10 entries)

    3. **Session**: Full conversation history
       - Lifetime: Entire conversation session
       - Storage: List[Message] (compatible with BaseMemory)
       - Size: Configurable (default: 100 messages)

    4. **Long-term**: User profile and knowledge
       - Lifetime: Persistent across sessions
       - Storage: Vectorized in vector store
       - Features: Semantic search, persistence

    Features:
    ---------
    - Automatic tier promotion (Working → Long-term)
    - Semantic retrieval via vector search
    - Keyword fallback when vector search unavailable
    - Stream-First event architecture
    - Persistence support

    Example:
        ```python
        from loom.builtin.memory import HierarchicalMemory
        from loom.builtin.embeddings import OpenAIEmbedding
        from loom.builtin.vector_store import InMemoryVectorStore

        # Initialize with full RAG support
        embedding = OpenAIEmbedding()
        vector_store = InMemoryVectorStore(dimension=1536)
        await vector_store.initialize()

        memory = HierarchicalMemory(
            embedding=embedding,
            vector_store=vector_store,
            enable_persistence=True,
            auto_promote=True
        )

        # Add messages (goes to Session)
        await memory.add_message(
            Message(role="user", content="I love Python programming")
        )

        # Add to long-term (user profile)
        await memory.add_to_longterm(
            "User is an experienced Python developer",
            metadata={"type": "user_profile"}
        )

        # Semantic retrieval
        results = await memory.retrieve(
            "programming languages user likes",
            top_k=3
        )
        print(results)
        ```
    """

    def __init__(
        self,
        embedding: Optional[BaseEmbedding] = None,
        vector_store: Optional[BaseVectorStore] = None,
        enable_persistence: bool = False,
        persist_dir: str = ".loom/memory",
        auto_promote: bool = True,
        working_memory_size: int = 10,
        session_memory_size: int = 100,
    ):
        """
        Initialize hierarchical memory.

        Args:
            embedding: Text embedding model (None = no semantic search)
            vector_store: Vector storage backend (None = create default)
            enable_persistence: Enable disk persistence
            persist_dir: Directory for persistence
            auto_promote: Auto-promote Working → Long-term
            working_memory_size: Max size of Working Memory
            session_memory_size: Max size of Session Memory
        """
        self.embedding = embedding
        self.vector_store = vector_store
        self.enable_persistence = enable_persistence
        self.persist_dir = Path(persist_dir)
        self.auto_promote = auto_promote
        self.working_memory_size = working_memory_size
        self.session_memory_size = session_memory_size

        # Four-tier storage
        self._ephemeral: Dict[str, MemoryEntry] = {}
        self._working: List[MemoryEntry] = []
        self._session: List[Message] = []
        self._longterm: List[MemoryEntry] = []

        # Vector index mapping (doc_id -> memory_entry_id)
        self._vector_index: Dict[str, str] = {}

        # Concurrency lock
        self._lock = asyncio.Lock()

        # Auto-create vector store if embedding provided but no store
        if embedding and not vector_store:
            logger.info(
                "[HierarchicalMemory] Creating default InMemoryVectorStore"
            )
            from loom.builtin.vector_store import InMemoryVectorStore

            self.vector_store = InMemoryVectorStore(
                dimension=embedding.get_dimension()
            )
            # Note: Caller should await vector_store.initialize()

        # Initialize persistence
        if self.enable_persistence:
            self._ensure_persist_dir()
            self._load_from_disk()

        logger.info(
            f"[HierarchicalMemory] Initialized with "
            f"embedding={'yes' if embedding else 'no'}, "
            f"vector_store={'yes' if vector_store else 'no'}, "
            f"persistence={enable_persistence}"
        )

    # ===== Core Stream-First Methods (BaseMemory Protocol) =====

    async def add_message_stream(
        self, message: Message
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Add message to Session Memory (Stream-First).

        Also automatically extracts to Working Memory if auto_promote enabled.

        Args:
            message: Message to add

        Yields:
            AgentEvent: MEMORY_ADD_START, MEMORY_ADD_COMPLETE
        """
        yield AgentEvent(
            type=AgentEventType.MEMORY_ADD_START,
            metadata={"role": message.role, "tier": "session"},
        )

        async with self._lock:
            # Add to session
            self._session.append(message)

            # Auto-extract to working memory
            if self.auto_promote and message.role == "assistant":
                await self._extract_to_working(message)

            # Trim session if too large
            if len(self._session) > self.session_memory_size:
                overflow = len(self._session) - self.session_memory_size
                self._session = self._session[overflow:]

            # Persist
            if self.enable_persistence:
                await self._save_to_disk()

        yield AgentEvent(
            type=AgentEventType.MEMORY_ADD_COMPLETE,
            metadata={
                "message_index": len(self._session) - 1,
                "total_messages": len(self._session),
                "working_count": len(self._working),
                "longterm_count": len(self._longterm),
            },
        )

    async def get_messages_stream(
        self, limit: Optional[int] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Get messages from Session Memory (Stream-First).

        Args:
            limit: Optional limit (None = all messages)

        Yields:
            AgentEvent: MEMORY_LOAD_START, MEMORY_MESSAGES_LOADED
        """
        yield AgentEvent(
            type=AgentEventType.MEMORY_LOAD_START,
            metadata={"limit": limit, "tier": "session"},
        )

        async with self._lock:
            messages = self._session[-limit:] if limit else self._session.copy()

        yield AgentEvent(
            type=AgentEventType.MEMORY_MESSAGES_LOADED,
            metadata={
                "messages": messages,
                "count": len(messages),
                "total": len(self._session),
            },
        )

    async def clear_stream(self) -> AsyncGenerator[AgentEvent, None]:
        """
        Clear Session/Working/Ephemeral Memory (preserves Long-term).

        Yields:
            AgentEvent: MEMORY_CLEAR_START, MEMORY_CLEAR_COMPLETE
        """
        yield AgentEvent(type=AgentEventType.MEMORY_CLEAR_START)

        async with self._lock:
            session_count = len(self._session)
            working_count = len(self._working)
            ephemeral_count = len(self._ephemeral)

            self._session.clear()
            self._working.clear()
            self._ephemeral.clear()

            if self.enable_persistence:
                await self._save_to_disk()

        yield AgentEvent(
            type=AgentEventType.MEMORY_CLEAR_COMPLETE,
            metadata={
                "session_cleared": session_count,
                "working_cleared": working_count,
                "ephemeral_cleared": ephemeral_count,
                "longterm_preserved": len(self._longterm),
            },
        )

    # ===== Convenience Wrappers =====

    async def add_message(self, message: Message) -> None:
        """Add message (convenience wrapper)."""
        async for _ in self.add_message_stream(message):
            pass

    async def get_messages(
        self, limit: Optional[int] = None
    ) -> List[Message]:
        """Get messages (convenience wrapper)."""
        messages = []
        async for event in self.get_messages_stream(limit):
            if event.type == AgentEventType.MEMORY_MESSAGES_LOADED:
                messages = event.metadata.get("messages", [])
        return messages

    async def clear(self) -> None:
        """Clear memory (convenience wrapper)."""
        async for _ in self.clear_stream():
            pass

    # ===== Optional RAG Methods =====

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        tier: Optional[str] = None,
    ) -> str:
        """
        Semantically retrieve relevant memories.

        Uses vector search if available, otherwise falls back to keyword search.

        Args:
            query: Query text
            top_k: Number of results
            filters: Metadata filters
            tier: Tier filter (ephemeral/working/session/longterm)

        Returns:
            XML-formatted retrieval results or empty string

        Example Output:
            ```xml
            <retrieved_memory>
            <memory tier="longterm" relevance="0.92">
            User is a Python developer with 5 years experience
            </memory>
            <memory tier="working" relevance="0.85">
            Currently discussing AI agents
            </memory>
            </retrieved_memory>
            ```
        """
        if not self.embedding or not self.vector_store:
            # Fall back to keyword search
            return await self._keyword_retrieve(query, top_k, tier)

        try:
            # Vector search
            query_vector = await self.embedding.embed_query(query)

            # Search in vector store
            vector_results = await self.vector_store.search(
                query_vector,
                top_k=top_k * 2,  # Get more to account for filtering
                filters=filters,
            )

            # Match with memory entries and apply tier filter
            results = []
            for doc, score in vector_results:
                entry_id = self._vector_index.get(doc.doc_id)
                if not entry_id:
                    continue

                entry = self._find_entry_by_id(entry_id)
                if not entry:
                    continue

                # Tier filter
                if tier and entry.tier != tier:
                    continue

                results.append((entry, score))

                if len(results) >= top_k:
                    break

            # Format as XML
            return self._format_results_xml(results)

        except Exception as e:
            logger.warning(
                f"Vector retrieval failed: {e}, falling back to keyword search"
            )
            return await self._keyword_retrieve(query, top_k, tier)

    async def add_to_longterm(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add to Long-term Memory with vectorization.

        Args:
            content: Content to store
            metadata: Metadata (type, category, etc.)
        """
        async with self._lock:
            entry = MemoryEntry(
                id=self._generate_id(),
                content=content,
                tier="longterm",
                timestamp=datetime.now().timestamp(),
                metadata=metadata or {},
            )

            # Vectorize
            if self.embedding:
                try:
                    entry.embedding = await self.embedding.embed_query(content)
                except Exception as e:
                    logger.warning(f"Failed to vectorize: {e}")

            # Add to longterm storage
            self._longterm.append(entry)

            # Add to vector store
            if self.vector_store and entry.embedding:
                try:
                    doc = Document(
                        content=content,
                        metadata={**(metadata or {}), "tier": "longterm"},
                        doc_id=entry.id,
                    )
                    await self.vector_store.add_vectors(
                        vectors=[entry.embedding],
                        documents=[doc],
                    )
                    self._vector_index[entry.id] = entry.id
                except Exception as e:
                    logger.warning(f"Failed to add to vector store: {e}")

            # Persist
            if self.enable_persistence:
                await self._save_longterm()

        logger.debug(
            f"[HierarchicalMemory] Added to long-term: {content[:50]}..."
        )

    async def get_by_tier(
        self,
        tier: str,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """
        Get memories by tier.

        Args:
            tier: ephemeral, working, session, or longterm
            limit: Optional limit

        Returns:
            List of Messages from the tier
        """
        async with self._lock:
            if tier == "ephemeral":
                entries = list(self._ephemeral.values())
                messages = [e.to_message() for e in entries]
            elif tier == "working":
                messages = [e.to_message() for e in self._working]
            elif tier == "session":
                messages = self._session.copy()
            elif tier == "longterm":
                messages = [e.to_message() for e in self._longterm]
            else:
                logger.warning(f"Unknown tier: {tier}")
                messages = []

            return messages[-limit:] if limit else messages

    # ===== Ephemeral Memory (Tool Memory) =====

    async def add_ephemeral(
        self,
        key: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add ephemeral (temporary) memory.

        Used for tool call intermediate results.

        Args:
            key: Unique key (e.g., "tool_call_123")
            content: Intermediate result content
            metadata: Metadata (tool_name, status, etc.)
        """
        async with self._lock:
            self._ephemeral[key] = MemoryEntry(
                id=key,
                content=content,
                tier="ephemeral",
                timestamp=datetime.now().timestamp(),
                metadata=metadata or {},
            )

        logger.debug(
            f"[HierarchicalMemory] Added ephemeral: {key}"
        )

    async def get_ephemeral(self, key: str) -> Optional[str]:
        """Get ephemeral memory content by key."""
        async with self._lock:
            entry = self._ephemeral.get(key)
            return entry.content if entry else None

    async def clear_ephemeral(self, key: Optional[str] = None) -> None:
        """
        Clear ephemeral memory.

        Args:
            key: Specific key to clear (None = clear all)
        """
        async with self._lock:
            if key:
                self._ephemeral.pop(key, None)
                logger.debug(f"[HierarchicalMemory] Cleared ephemeral: {key}")
            else:
                count = len(self._ephemeral)
                self._ephemeral.clear()
                logger.debug(
                    f"[HierarchicalMemory] Cleared all ephemeral ({count} entries)"
                )

    # ===== Private Helper Methods =====

    async def _extract_to_working(self, message: Message) -> None:
        """Extract key information from message to Working Memory."""
        # Simple strategy: keep recent assistant messages
        entry = MemoryEntry(
            id=self._generate_id(),
            content=message.content,
            tier="working",
            timestamp=datetime.now().timestamp(),
            metadata={"role": message.role},
        )

        self._working.append(entry)

        # Capacity control: promote oldest if exceeded
        while len(self._working) > self.working_memory_size:
            oldest = self._working.pop(0)

            # Promote to long-term if important
            if self.auto_promote and len(oldest.content) > 100:
                await self._promote_to_longterm(oldest)

    async def _promote_to_longterm(self, entry: MemoryEntry) -> None:
        """Promote Working Memory entry to Long-term."""
        entry.tier = "longterm"

        # Vectorize if not already
        if self.embedding and not entry.embedding:
            try:
                entry.embedding = await self.embedding.embed_query(entry.content)
            except Exception as e:
                logger.warning(f"Failed to vectorize promoted entry: {e}")

        self._longterm.append(entry)

        # Add to vector store
        if self.vector_store and entry.embedding:
            try:
                doc = Document(
                    content=entry.content,
                    metadata=entry.metadata,
                    doc_id=entry.id,
                )
                await self.vector_store.add_vectors(
                    vectors=[entry.embedding],
                    documents=[doc],
                )
                self._vector_index[entry.id] = entry.id
            except Exception as e:
                logger.warning(f"Failed to add promoted entry to vector store: {e}")

        logger.debug(
            f"[HierarchicalMemory] Promoted to long-term: {entry.content[:50]}..."
        )

    async def _keyword_retrieve(
        self,
        query: str,
        top_k: int,
        tier: Optional[str],
    ) -> str:
        """Keyword-based retrieval (fallback)."""
        query_lower = query.lower()
        matches = []

        # Search all tiers
        all_entries: List[MemoryEntry] = []

        async with self._lock:
            # Ephemeral
            all_entries.extend(self._ephemeral.values())

            # Working
            all_entries.extend(self._working)

            # Session (convert to entries)
            for i, msg in enumerate(self._session):
                all_entries.append(
                    MemoryEntry(
                        id=f"session_{i}",
                        content=msg.content,
                        tier="session",
                        timestamp=0,
                        metadata={"role": msg.role},
                    )
                )

            # Long-term
            all_entries.extend(self._longterm)

        # Filter by tier and keyword
        for entry in all_entries:
            if tier and entry.tier != tier:
                continue

            if query_lower in entry.content.lower():
                # Simple relevance score based on keyword frequency
                score = entry.content.lower().count(query_lower) / len(
                    entry.content.split()
                )
                matches.append((entry, score))

        # Sort by score
        matches.sort(key=lambda x: x[1], reverse=True)

        # Format top_k
        return self._format_results_xml(matches[:top_k])

    def _format_results_xml(
        self, results: List[Tuple[MemoryEntry, float]]
    ) -> str:
        """Format retrieval results as XML."""
        if not results:
            return ""

        parts = ["<retrieved_memory>"]
        for entry, score in results:
            parts.append(
                f'<memory tier="{entry.tier}" relevance="{score:.2f}">'
            )
            # Truncate long content
            content = entry.content
            if len(content) > 500:
                content = content[:500] + "..."
            parts.append(content)
            parts.append("</memory>")
        parts.append("</retrieved_memory>")

        return "\n".join(parts)

    def _find_entry_by_id(self, entry_id: str) -> Optional[MemoryEntry]:
        """Find memory entry by ID across all tiers."""
        # Ephemeral
        if entry_id in self._ephemeral:
            return self._ephemeral[entry_id]

        # Working
        for entry in self._working:
            if entry.id == entry_id:
                return entry

        # Long-term
        for entry in self._longterm:
            if entry.id == entry_id:
                return entry

        return None

    def _generate_id(self) -> str:
        """Generate unique ID."""
        from uuid import uuid4
        return str(uuid4())

    def _ensure_persist_dir(self) -> None:
        """Ensure persistence directory exists."""
        self.persist_dir.mkdir(parents=True, exist_ok=True)

    async def _save_to_disk(self) -> None:
        """Save session/working memory to disk."""
        if not self.enable_persistence:
            return

        session_file = self.persist_dir / "session.json"
        working_file = self.persist_dir / "working.json"

        # Save session messages
        session_data = [
            {"role": msg.role, "content": msg.content, "metadata": msg.metadata}
            for msg in self._session
        ]

        # Save working entries
        working_data = [e.to_dict() for e in self._working]

        try:
            session_file.write_text(json.dumps(session_data, indent=2))
            working_file.write_text(json.dumps(working_data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save to disk: {e}")

    async def _save_longterm(self) -> None:
        """Save long-term memory to disk."""
        if not self.enable_persistence:
            return

        longterm_file = self.persist_dir / "longterm.json"
        longterm_data = [e.to_dict() for e in self._longterm]

        try:
            longterm_file.write_text(json.dumps(longterm_data, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save long-term memory: {e}")

    def _load_from_disk(self) -> None:
        """Load memory from disk."""
        session_file = self.persist_dir / "session.json"
        working_file = self.persist_dir / "working.json"
        longterm_file = self.persist_dir / "longterm.json"

        # Load session
        if session_file.exists():
            try:
                session_data = json.loads(session_file.read_text())
                self._session = [
                    Message(
                        role=msg["role"],
                        content=msg["content"],
                        metadata=msg.get("metadata", {}),
                    )
                    for msg in session_data
                ]
                logger.info(
                    f"[HierarchicalMemory] Loaded {len(self._session)} session messages"
                )
            except Exception as e:
                logger.warning(f"Failed to load session: {e}")

        # Load working
        if working_file.exists():
            try:
                working_data = json.loads(working_file.read_text())
                self._working = [
                    MemoryEntry.from_dict(entry) for entry in working_data
                ]
                logger.info(
                    f"[HierarchicalMemory] Loaded {len(self._working)} working entries"
                )
            except Exception as e:
                logger.warning(f"Failed to load working memory: {e}")

        # Load long-term
        if longterm_file.exists():
            try:
                longterm_data = json.loads(longterm_file.read_text())
                self._longterm = [
                    MemoryEntry.from_dict(entry) for entry in longterm_data
                ]

                # Rebuild vector index
                for entry in self._longterm:
                    self._vector_index[entry.id] = entry.id

                logger.info(
                    f"[HierarchicalMemory] Loaded {len(self._longterm)} long-term entries"
                )
            except Exception as e:
                logger.warning(f"Failed to load long-term memory: {e}")

    # ===== Utility Methods =====

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "ephemeral_count": len(self._ephemeral),
            "working_count": len(self._working),
            "working_capacity": self.working_memory_size,
            "session_count": len(self._session),
            "session_capacity": self.session_memory_size,
            "longterm_count": len(self._longterm),
            "has_embedding": self.embedding is not None,
            "has_vector_store": self.vector_store is not None,
            "persistence_enabled": self.enable_persistence,
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"HierarchicalMemory("
            f"ephemeral={len(self._ephemeral)}, "
            f"working={len(self._working)}/{self.working_memory_size}, "
            f"session={len(self._session)}/{self.session_memory_size}, "
            f"longterm={len(self._longterm)})"
        )
