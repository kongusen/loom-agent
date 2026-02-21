"""KnowledgeProvider — bridges KnowledgeBase into context orchestrator."""

from __future__ import annotations

from ..types import ContextFragment, RetrieverOptions
from .base import KnowledgeBase


class KnowledgeProvider:
    source = "knowledge"

    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    async def provide(self, query: str, budget: int) -> list[ContextFragment]:
        results = await self._kb.query(query, RetrieverOptions(limit=10))
        frags: list[ContextFragment] = []
        used = 0
        for r in results:
            tokens = r.chunk.tokens or (len(r.chunk.content) // 4 + 1)
            if used + tokens > budget:
                break
            frags.append(ContextFragment(
                source="knowledge", content=r.chunk.content,
                tokens=tokens, relevance=r.score,
                metadata={"chunk_id": r.chunk.id, "document_id": r.chunk.document_id},
            ))
            used += tokens
        return frags
