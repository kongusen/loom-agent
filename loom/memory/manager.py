"""Memory manager — orchestrates L1→L2→L3 pipeline."""

from __future__ import annotations

from ..types import MemoryEntry, Message
from .persistent_store import PersistentStore
from .sliding_window import SlidingWindow
from .tokens import _estimate_tokens
from .working_memory import WorkingMemory


class MemoryManager:
    """Orchestrates L1→L2→L3 memory pipeline."""

    def __init__(
        self,
        l1: SlidingWindow | None = None,
        l2: WorkingMemory | None = None,
        l3: PersistentStore | None = None,
    ) -> None:
        self.l1 = l1 or SlidingWindow()
        self.l2 = l2 or WorkingMemory()
        self.l3 = l3 or PersistentStore()

    async def add_message(self, msg: Message) -> None:
        evicted = self.l1.add(msg)
        for old_msg in evicted:
            text = old_msg.content if isinstance(old_msg.content, str) else str(old_msg.content)
            entry = MemoryEntry(
                content=text,
                tokens=_estimate_tokens(text),
                importance=0.3,
                metadata={"role": old_msg.role},
            )
            l2_evicted = await self.l2.store(entry)
            for e in l2_evicted:
                await self.l3.store(e)

    def get_history(self) -> list[Message]:
        return self.l1.get_messages()

    async def get_l2_context(self, query: str = "", limit: int = 10) -> list[MemoryEntry]:
        return await self.l2.retrieve(query, limit)

    async def get_l3_context(self, query: str = "", limit: int = 5) -> list[MemoryEntry]:
        return await self.l3.retrieve(query, limit)

    async def persist(self, entries: list[MemoryEntry]) -> None:
        for e in entries:
            await self.l3.store(e)

    async def extract_for(self, query: str, budget: int) -> list[MemoryEntry]:
        l2 = await self.l2.retrieve(query)
        l3 = await self.l3.retrieve(query)
        combined = sorted(l2 + l3, key=lambda e: e.importance, reverse=True)
        total, result = 0, []
        for e in combined:
            if total + e.tokens > budget:
                break
            result.append(e)
            total += e.tokens
        return result

    async def build_context(self, query: str, budget: int) -> str:
        """Build a combined context string from L1 history + L2/L3 retrieval."""
        history = self.l1.get_messages()
        history_text = "\n".join(f"{m.role}: {m.content}" for m in history[-10:])
        history_tokens = _estimate_tokens(history_text)
        remaining = max(budget - history_tokens, 0)
        entries = await self.extract_for(query, remaining)
        memory_text = "\n".join(e.content for e in entries)
        parts = []
        if history_text:
            parts.append(history_text)
        if memory_text:
            parts.append(memory_text)
        return "\n---\n".join(parts)

    async def absorb(self, entries: list[MemoryEntry], boost: float = 0.1) -> None:
        for e in entries:
            e.importance = min(1.0, e.importance + boost)
            l2_evicted = await self.l2.store(e)
            for victim in l2_evicted:
                await self.l3.store(victim)
