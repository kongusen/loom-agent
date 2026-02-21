"""L2: Working memory — importance-scored entries."""

from __future__ import annotations

from ..types import MemoryEntry


class WorkingMemory:
    """L2: Extracted facts/decisions scored by importance. Evicts lowest."""

    name = "working_memory"

    def __init__(self, token_budget: int = 4000) -> None:
        self.token_budget = token_budget
        self.current_tokens = 0
        self._entries: list[MemoryEntry] = []

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
        ranked = sorted(self._entries, key=lambda e: e.importance, reverse=True)
        return ranked[:limit]
