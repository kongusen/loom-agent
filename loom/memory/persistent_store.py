"""L3: Persistent store — keyword search, replaceable via protocol."""

from __future__ import annotations

from ..types import MemoryEntry


class PersistentStore:
    """L3: Long-term storage. Replace with vector DB via MemoryLayer protocol."""

    name = "persistent"

    def __init__(self, token_budget: int = 32000) -> None:
        self.token_budget = token_budget
        self.current_tokens = 0
        self._entries: dict[str, MemoryEntry] = {}

    async def store(self, entry: MemoryEntry) -> None:
        self._entries[entry.id] = entry
        self.current_tokens += entry.tokens

    async def retrieve(self, query: str = "", limit: int = 10) -> list[MemoryEntry]:
        if not query:
            entries = sorted(self._entries.values(), key=lambda e: e.created_at, reverse=True)
            return entries[:limit]
        q_words = query.lower().split()
        scored = []
        for e in self._entries.values():
            hits = sum(1 for w in q_words if w in e.content.lower())
            if hits > 0:
                scored.append((e, hits))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [e for e, _ in scored[:limit]]
