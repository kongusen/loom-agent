"""KnowledgeBase — hybrid retrieval over ingested documents."""

from __future__ import annotations

from typing import Any

from ..types import Chunk, Document, RetrievalResult, RetrieverOptions
from .chunkers import FixedSizeChunker
from .retrievers import (
    EmbeddingProvider,
    EntityExtractor,
    GraphRetriever,
    GraphStore,
    HybridRetriever,
    KeywordRetriever,
    VectorRetriever,
    VectorStore,
)


class KnowledgeBase:
    def __init__(
        self,
        chunker: Any | None = None,
        embedder: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
        graph_store: GraphStore | None = None,
        entity_extractor: EntityExtractor | None = None,
    ) -> None:
        self._chunker = chunker or FixedSizeChunker()
        self._embedder = embedder
        self._vector_store = vector_store
        self._graph_store = graph_store
        self._entity_extractor = entity_extractor
        self._keyword = KeywordRetriever()
        self._vector_retriever: VectorRetriever | None = None
        self._graph_retriever: GraphRetriever | None = None
        self._hybrid: HybridRetriever | None = None
        if embedder and vector_store:
            self._vector_retriever = VectorRetriever(embedder, vector_store)
            self._hybrid = HybridRetriever(self._keyword, self._vector_retriever)
        if graph_store and entity_extractor:
            self._graph_retriever = GraphRetriever(graph_store, entity_extractor)
        self._docs: dict[str, list[Chunk]] = {}

    async def ingest(self, docs: list[Document]) -> None:
        for doc in docs:
            chunks = self._chunker.chunk(doc)
            self._docs[doc.id] = chunks
            self._keyword.add_chunks(chunks)
            if self._embedder and self._vector_store:
                texts = [c.content for c in chunks]
                vectors = await self._embedder.embed_batch(texts)
                await self._vector_store.upsert(
                    [
                        {
                            "id": c.id,
                            "vector": v,
                            "content": c.content,
                            "metadata": {"document_id": doc.id},
                        }
                        for c, v in zip(chunks, vectors, strict=False)
                    ]
                )
            if self._entity_extractor and self._graph_store:
                entities = await self._entity_extractor.extract(doc.content)
                nodes = [
                    {
                        "id": e.get("id", e.get("name", "")),
                        "label": e.get("name", ""),
                        "type": e.get("type", ""),
                        "metadata": {"document_id": doc.id},
                    }
                    for e in entities
                ]
                edges = [
                    {"source": e.get("id", e.get("name", "")), "target": r, "type": "related"}
                    for e in entities
                    for r in e.get("relations", [])
                ]
                if nodes:
                    await self._graph_store.add_nodes(nodes)
                if edges:
                    await self._graph_store.add_edges(edges)

    async def query(
        self, query: str, opts: RetrieverOptions | None = None
    ) -> list[RetrievalResult]:
        limit = (opts or RetrieverOptions()).limit
        base = self._hybrid or self._keyword
        results = await base.retrieve(query, opts)
        if not self._graph_retriever:
            return results
        graph_results = await self._graph_retriever.retrieve(query, RetrieverOptions(limit=limit))
        # RRF merge of base + graph
        scores: dict[str, float] = {}
        chunks: dict[str, Any] = {}
        for rank, r in enumerate(results):
            scores[r.chunk.id] = 0.6 / (rank + 1)
            chunks[r.chunk.id] = r.chunk
        for rank, r in enumerate(graph_results):
            scores[r.chunk.id] = scores.get(r.chunk.id, 0) + 0.4 / (rank + 1)
            chunks[r.chunk.id] = r.chunk
        fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [RetrievalResult(chunk=chunks[cid], score=s) for cid, s in fused]

    async def delete(self, document_ids: list[str]) -> None:
        for did in document_ids:
            self._keyword.remove_by_document(did)
            chunks = self._docs.pop(did, [])
            if self._vector_store and chunks:
                await self._vector_store.delete([c.id for c in chunks])
