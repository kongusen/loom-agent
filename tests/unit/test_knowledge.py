"""Unit tests for knowledge module (retrievers, chunkers, base)."""

import pytest
from loom.knowledge.retrievers import KeywordRetriever, InMemoryVectorStore, VectorRetriever, HybridRetriever, GraphRetriever
from loom.knowledge.chunkers import FixedSizeChunker, RecursiveChunker
from loom.knowledge.base import KnowledgeBase
from loom.types import Chunk, Document, RetrieverOptions
from tests.conftest import MockEmbeddingProvider, MockGraphStore, MockEntityExtractor


class TestKeywordRetriever:
    async def test_retrieve_matches(self):
        kr = KeywordRetriever()
        kr.add_chunks([Chunk(id="1", content="python programming language")])
        results = await kr.retrieve("python")
        assert len(results) == 1

    async def test_retrieve_no_match(self):
        kr = KeywordRetriever()
        kr.add_chunks([Chunk(id="1", content="java code")])
        results = await kr.retrieve("python")
        assert len(results) == 0

    def test_remove_by_document(self):
        kr = KeywordRetriever()
        kr.add_chunks([Chunk(id="1", content="a", document_id="d1"), Chunk(id="2", content="b", document_id="d2")])
        kr.remove_by_document("d1")
        assert len(kr._chunks) == 1


class TestInMemoryVectorStore:
    async def test_upsert_and_query(self):
        store = InMemoryVectorStore()
        await store.upsert([{"id": "a", "vector": [1.0, 0.0], "content": "hello"}])
        results = await store.query([1.0, 0.0], limit=1)
        assert len(results) == 1
        assert results[0]["id"] == "a"

    async def test_delete(self):
        store = InMemoryVectorStore()
        await store.upsert([{"id": "a", "vector": [1.0], "content": "x"}])
        await store.delete(["a"])
        results = await store.query([1.0], limit=5)
        assert len(results) == 0


class TestFixedSizeChunker:
    def test_single_chunk(self):
        chunker = FixedSizeChunker(size=100)
        doc = Document(id="d1", content="short text")
        chunks = chunker.chunk(doc)
        assert len(chunks) == 1

    def test_multiple_chunks(self):
        chunker = FixedSizeChunker(size=10, overlap=2)
        doc = Document(id="d1", content="a" * 30)
        chunks = chunker.chunk(doc)
        assert len(chunks) > 1


class TestRecursiveChunker:
    def test_small_text_single_chunk(self):
        chunker = RecursiveChunker(max_size=1000)
        doc = Document(id="d1", content="small")
        assert len(chunker.chunk(doc)) == 1

    def test_splits_on_separator(self):
        chunker = RecursiveChunker(max_size=20)
        doc = Document(id="d1", content="first paragraph\n\nsecond paragraph")
        chunks = chunker.chunk(doc)
        assert len(chunks) >= 2


class TestKnowledgeBase:
    async def test_ingest_keyword_only(self):
        kb = KnowledgeBase()
        await kb.ingest([Document(id="d1", content="python programming")])
        results = await kb.query("python")
        assert len(results) >= 1

    async def test_ingest_with_embedder(self, mock_embedder):
        store = InMemoryVectorStore()
        kb = KnowledgeBase(embedder=mock_embedder, vector_store=store)
        await kb.ingest([Document(id="d1", content="machine learning")])
        results = await kb.query("machine")
        assert len(results) >= 1

    async def test_ingest_with_graph(self, mock_embedder, mock_graph_store, mock_entity_extractor):
        kb = KnowledgeBase(
            embedder=mock_embedder, vector_store=InMemoryVectorStore(),
            graph_store=mock_graph_store, entity_extractor=mock_entity_extractor,
        )
        await kb.ingest([Document(id="d1", content="Alice knows Bob")])
        assert len(mock_graph_store.nodes) > 0

    async def test_delete(self):
        kb = KnowledgeBase()
        await kb.ingest([Document(id="d1", content="to delete")])
        await kb.delete(["d1"])
        results = await kb.query("delete")
        assert len(results) == 0
