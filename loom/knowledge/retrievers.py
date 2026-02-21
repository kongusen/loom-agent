"""Retrievers — keyword, vector, hybrid search."""

from __future__ import annotations

import re
from typing import Any, Protocol, runtime_checkable

from ..types import Chunk, RetrievalResult, RetrieverOptions


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class VectorStore(Protocol):
    async def upsert(self, items: list[dict[str, Any]]) -> None: ...
    async def query(self, vector: list[float], limit: int) -> list[dict[str, Any]]: ...
    async def delete(self, ids: list[str]) -> None: ...


@runtime_checkable
class GraphStore(Protocol):
    async def add_nodes(self, nodes: list[dict[str, Any]]) -> None: ...
    async def add_edges(self, edges: list[dict[str, Any]]) -> None: ...
    async def find_related(self, query: str, limit: int) -> list[dict[str, Any]]: ...
    async def get_neighbors(self, node_id: str, depth: int = 1) -> list[dict[str, Any]]: ...


@runtime_checkable
class EntityExtractor(Protocol):
    async def extract(self, text: str) -> list[dict[str, Any]]: ...


class KeywordRetriever:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    def add_chunks(self, chunks: list[Chunk]) -> None:
        self._chunks.extend(chunks)

    def remove_by_document(self, doc_id: str) -> None:
        self._chunks = [c for c in self._chunks if c.document_id != doc_id]

    async def retrieve(
        self, query: str, opts: RetrieverOptions | None = None
    ) -> list[RetrievalResult]:
        limit = (opts or RetrieverOptions()).limit
        words = set(re.findall(r"\w+", query.lower()))
        scored = []
        for c in self._chunks:
            cwords = set(re.findall(r"\w+", c.content.lower()))
            overlap = len(words & cwords)
            if overlap:
                scored.append(RetrievalResult(chunk=c, score=overlap / max(len(words), 1)))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]


class InMemoryVectorStore:
    """Simple in-memory VectorStore using cosine similarity."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    async def upsert(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            self._items[item["id"]] = item

    async def query(self, vector: list[float], limit: int) -> list[dict[str, Any]]:
        scored = []
        for item in self._items.values():
            score = self._cosine(vector, item["vector"])
            scored.append((item, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "id": it["id"],
                "score": s,
                "content": it.get("content", ""),
                "metadata": it.get("metadata", {}),
            }
            for it, s in scored[:limit]
        ]

    async def delete(self, ids: list[str]) -> None:
        for id_ in ids:
            self._items.pop(id_, None)

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        return float(dot / max(na * nb, 1e-10))


class VectorRetriever:
    """Retriever backed by EmbeddingProvider + VectorStore."""

    def __init__(self, embedder: EmbeddingProvider, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store

    async def retrieve(
        self, query: str, opts: RetrieverOptions | None = None
    ) -> list[RetrievalResult]:
        limit = (opts or RetrieverOptions()).limit
        vec = await self._embedder.embed(query)
        raw = await self._store.query(vec, limit)
        return [
            RetrievalResult(
                chunk=Chunk(
                    id=r["id"], content=r.get("content", ""), metadata=r.get("metadata", {})
                ),
                score=r.get("score", 0.0),
            )
            for r in raw
        ]


class HybridRetriever:
    """Combines keyword + vector retrieval with reciprocal rank fusion."""

    def __init__(
        self, keyword: KeywordRetriever, vector: VectorRetriever, keyword_weight: float = 0.4
    ) -> None:
        self._keyword = keyword
        self._vector = vector
        self._kw = keyword_weight

    async def retrieve(
        self, query: str, opts: RetrieverOptions | None = None
    ) -> list[RetrievalResult]:
        limit = (opts or RetrieverOptions()).limit
        kw_results = await self._keyword.retrieve(query, RetrieverOptions(limit=limit * 2))
        vec_results = await self._vector.retrieve(query, RetrieverOptions(limit=limit * 2))
        # Reciprocal rank fusion
        scores: dict[str, float] = {}
        chunks: dict[str, Chunk] = {}
        for rank, r in enumerate(kw_results):
            scores[r.chunk.id] = scores.get(r.chunk.id, 0) + self._kw / (rank + 1)
            chunks[r.chunk.id] = r.chunk
        for rank, r in enumerate(vec_results):
            scores[r.chunk.id] = scores.get(r.chunk.id, 0) + (1 - self._kw) / (rank + 1)
            chunks[r.chunk.id] = r.chunk
        fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [RetrievalResult(chunk=chunks[cid], score=s) for cid, s in fused]


class GraphRetriever:
    """Retriever backed by GraphStore — entity-based graph traversal."""

    def __init__(self, graph: GraphStore, extractor: EntityExtractor) -> None:
        self._graph = graph
        self._extractor = extractor

    async def retrieve(
        self, query: str, opts: RetrieverOptions | None = None
    ) -> list[RetrievalResult]:
        limit = (opts or RetrieverOptions()).limit
        related = await self._graph.find_related(query, limit)
        return [
            RetrievalResult(
                chunk=Chunk(
                    id=r.get("id", ""), content=r.get("content", ""), metadata=r.get("metadata", {})
                ),
                score=r.get("score", 0.5),
            )
            for r in related[:limit]
        ]
