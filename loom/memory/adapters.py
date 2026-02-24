"""Adapters — bridge external vector stores to PersistentStore Protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import MemoryEntry, SearchOptions

if TYPE_CHECKING:
    from ..knowledge.retrievers import EmbeddingProvider, VectorStore


class VectorPersistentStore:
    """Adapts VectorStore + EmbeddingProvider → PersistentStore Protocol.

    Allows any vector DB (Postgres pgvector, Pinecone, etc.) to serve as
    loom's long-term memory layer.
    """

    def __init__(self, store: VectorStore, embedder: EmbeddingProvider) -> None:
        self._store = store
        self._embedder = embedder

    async def save(self, entry: MemoryEntry) -> None:
        vec = await self._embedder.embed(entry.content)
        await self._store.upsert(
            [
                {
                    "id": entry.id,
                    "vector": vec,
                    "content": entry.content,
                    "metadata": {
                        **entry.metadata,
                        "tokens": entry.tokens,
                        "importance": entry.importance,
                        "created_at": entry.created_at,
                    },
                }
            ]
        )

    async def search(self, query: str, opts: SearchOptions | None = None) -> list[MemoryEntry]:
        opts = opts or SearchOptions()
        vec = await self._embedder.embed(query)
        results = await self._store.query(vec, opts.limit)
        return [
            MemoryEntry(
                id=r["id"],
                content=r.get("content", ""),
                tokens=r.get("metadata", {}).get("tokens", 0),
                importance=r.get("metadata", {}).get("importance", 0.5),
                metadata=r.get("metadata", {}),
                created_at=r.get("metadata", {}).get("created_at", 0.0),
            )
            for r in results
        ]

    async def delete(self, id: str) -> None:
        await self._store.delete([id])
