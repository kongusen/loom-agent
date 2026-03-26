"""L2: Working memory — importance-scored entries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import MemoryEntry
from .semantic import cosine_similarity, hybrid_score, recency_score

if TYPE_CHECKING:
    from ..types import EmbeddingProvider


class WorkingMemory:
    """L2: Extracted facts/decisions scored by importance. Evicts lowest."""

    name = "working_memory"

    def __init__(
        self,
        token_budget: int = 4000,
        embedding: EmbeddingProvider | None = None,
    ) -> None:
        self.token_budget = token_budget
        self.current_tokens = 0
        self._entries: list[MemoryEntry] = []
        self._embedding = embedding

    async def store(self, entry: MemoryEntry) -> list[MemoryEntry]:
        """Store entry, return evicted entries (for L3 flow)."""
        self._entries.append(entry)
        self.current_tokens += entry.tokens
        evicted: list[MemoryEntry] = []
        while self.current_tokens > self.token_budget and self._entries:
            self._entries.sort(key=lambda e: e.importance)
            victim = self._entries.pop(0)
            self.current_tokens -= victim.tokens
            evicted.append(victim)
        return evicted

    async def retrieve(self, query: str = "", limit: int = 20) -> list[MemoryEntry]:
        if not query or not self._embedding:
            # Fallback: importance-only ranking
            ranked = sorted(self._entries, key=lambda e: e.importance, reverse=True)
            return ranked[:limit]

        # Semantic + hybrid ranking
        query_emb = await self._embedding.embed(query)
        scored = []
        for entry in self._entries:
            sem_sim = cosine_similarity(query_emb, entry.embedding) if entry.embedding else 0.0
            rec = recency_score(entry.created_at)
            score = hybrid_score(sem_sim, rec, entry.importance)
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:limit]]
