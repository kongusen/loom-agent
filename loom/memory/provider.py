"""MemoryProvider — bridges memory into ContextOrchestrator."""

from __future__ import annotations

from ..types import ContextFragment


class MemoryProvider:
    source = "memory"

    def __init__(self, manager, tokenizer) -> None:
        self._mgr = manager
        self._tok = tokenizer

    async def provide(self, query: str, budget: int) -> list[ContextFragment]:
        entries = await self._mgr.extract_for(query, budget)
        return [
            ContextFragment(source="memory", content=e.content, tokens=e.tokens, relevance=0.8, metadata={"role": e.metadata.get("role", "")})
            for e in entries
        ]
