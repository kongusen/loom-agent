"""Memory context provider — bridges MemoryManager into context system."""

from __future__ import annotations

from ..types import ContextFragment, ContextSource
from ..memory import MemoryManager


class MemoryContextProvider:
    """Bridges MemoryManager L2/L3 into the context system."""

    source = ContextSource.MEMORY

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    async def provide(self, query: str, budget: int) -> list[ContextFragment]:
        l2 = await self._memory.get_l2_context(query)
        l3 = await self._memory.get_l3_context(query)
        fragments, total = [], 0
        for entry in sorted(l2 + l3, key=lambda e: e.importance, reverse=True):
            if total + entry.tokens > budget:
                break
            fragments.append(ContextFragment(
                source=ContextSource.MEMORY,
                content=entry.content,
                tokens=entry.tokens,
                relevance=entry.importance,
            ))
            total += entry.tokens
        return fragments
