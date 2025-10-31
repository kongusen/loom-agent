"""
Unit tests for FAISSVectorStore
"""

import pytest
import numpy as np
from typing import List

from loom.builtin.retriever.faiss_store import FAISSVectorStore
from loom.interfaces.retriever import Document


@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return [
        Document(
            doc_id="doc1",
            content="Machine learning is awesome",
            metadata={"category": "ML"}
        ),
        Document(
            doc_id="doc2",
            content="Databases are important",
            metadata={"category": "DB"}
        ),
        Document(
            doc_id="doc3",
            content="Web development is fun",
            metadata={"category": "Web"}
        ),
    ]


@pytest.fixture
def sample_embeddings():
    """Sample embeddings for testing"""
    return [
        [0.1] * 128,  # doc1 embedding
        [0.5] * 128,  # doc2 embedding
        [0.9] * 128,  # doc3 embedding
    ]


@pytest.mark.skipif(
    not pytest.importorskip("faiss", reason="FAISS not installed"),
    reason="FAISS not installed"
)
class TestFAISSVectorStore:
    """Tests for FAISSVectorStore"""

    @pytest.mark.asyncio
    async def test_initialization_flat(self):
        """Test flat index initialization"""
        store = FAISSVectorStore(dimension=128, index_type="Flat")
        await store.initialize()

        assert store._initialized
        assert store.index is not None
        assert store.index.ntotal == 0

    @pytest.mark.asyncio
    async def test_add_documents(self, sample_documents, sample_embeddings):
        """Test adding documents"""
        store = FAISSVectorStore(dimension=128)
        await store.initialize()

        await store.add_documents(sample_documents, sample_embeddings)

        assert len(store.documents) == 3
        assert store.index.ntotal == 3
        assert "doc1" in store.id_to_index
        assert 0 in store.index_to_id

    @pytest.mark.asyncio
    async def test_search(self, sample_documents, sample_embeddings):
        """Test similarity search"""
        store = FAISSVectorStore(dimension=128)
        await store.initialize()

        await store.add_documents(sample_documents, sample_embeddings)

        # Search with query similar to doc1
        query_embedding = [0.1] * 128
        results = await store.search(query_embedding, top_k=2)

        assert len(results) <= 2
        assert all(isinstance(doc, Document) for doc in results)
        assert all(hasattr(doc, 'score') for doc in results)
        # First result should be doc1 (most similar)
        assert results[0].doc_id == "doc1"

    @pytest.mark.asyncio
    async def test_search_with_filters(self, sample_documents, sample_embeddings):
        """Test search with metadata filters"""
        store = FAISSVectorStore(dimension=128)
        await store.initialize()

        await store.add_documents(sample_documents, sample_embeddings)

        # Search with filter
        query_embedding = [0.5] * 128
        results = await store.search(
            query_embedding,
            top_k=5,
            filters={"category": "ML"}
        )

        # Should only return ML documents
        assert all(doc.metadata.get("category") == "ML" for doc in results)

    @pytest.mark.asyncio
    async def test_get_document(self, sample_documents, sample_embeddings):
        """Test getting document by ID"""
        store = FAISSVectorStore(dimension=128)
        await store.initialize()

        await store.add_documents(sample_documents, sample_embeddings)

        doc = await store.get_document("doc1")
        assert doc is not None
        assert doc.doc_id == "doc1"
        assert doc.content == "Machine learning is awesome"

        # Non-existent document
        doc = await store.get_document("nonexistent")
        assert doc is None

    @pytest.mark.asyncio
    async def test_delete(self, sample_documents, sample_embeddings):
        """Test document deletion"""
        store = FAISSVectorStore(dimension=128)
        await store.initialize()

        await store.add_documents(sample_documents, sample_embeddings)

        await store.delete(["doc1"])

        # Document should be removed from metadata
        assert "doc1" not in store.documents
        assert "doc1" not in store.id_to_index

        # But index still has 3 vectors (FAISS limitation)
        assert store.index.ntotal == 3

    @pytest.mark.asyncio
    async def test_ivf_index(self, sample_documents):
        """Test IVF index type"""
        store = FAISSVectorStore(
            dimension=128,
            index_type="IVF",
            nlist=2  # Small nlist for testing
        )
        await store.initialize()

        # IVF requires training
        # Generate more documents for training
        docs = sample_documents * 10  # 30 documents
        embeddings = [[float(i % 10) / 10] * 128 for i in range(30)]

        await store.add_documents(docs, embeddings)

        assert store.index.is_trained
        assert store.index.ntotal == 30

    @pytest.mark.asyncio
    async def test_persistence(self, sample_documents, sample_embeddings, tmp_path):
        """Test saving and loading index"""
        store = FAISSVectorStore(dimension=128)
        await store.initialize()

        await store.add_documents(sample_documents, sample_embeddings)

        # Save
        path = str(tmp_path / "test_index")
        await store.persist(path)

        # Load
        loaded_store = await FAISSVectorStore.load(path)

        assert loaded_store._initialized
        assert len(loaded_store.documents) == 3
        assert loaded_store.index.ntotal == 3

        # Test search on loaded index
        query_embedding = [0.1] * 128
        results = await loaded_store.search(query_embedding, top_k=2)

        assert len(results) <= 2
        assert results[0].doc_id == "doc1"

    @pytest.mark.asyncio
    async def test_get_stats(self, sample_documents, sample_embeddings):
        """Test statistics"""
        store = FAISSVectorStore(dimension=128, index_type="Flat")
        await store.initialize()

        await store.add_documents(sample_documents, sample_embeddings)

        stats = store.get_stats()

        assert stats["initialized"] is True
        assert stats["total_documents"] == 3
        assert stats["index_size"] == 3
        assert stats["dimension"] == 128
        assert stats["index_type"] == "Flat"

    @pytest.mark.asyncio
    async def test_empty_search(self):
        """Test search on empty index"""
        store = FAISSVectorStore(dimension=128)
        await store.initialize()

        query_embedding = [0.5] * 128
        results = await store.search(query_embedding, top_k=5)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_distance_metrics(self, sample_documents, sample_embeddings):
        """Test different distance metrics"""
        # L2 metric
        store_l2 = FAISSVectorStore(dimension=128, metric="L2")
        await store_l2.initialize()
        await store_l2.add_documents(sample_documents, sample_embeddings)

        # Inner product metric
        store_ip = FAISSVectorStore(dimension=128, metric="IP")
        await store_ip.initialize()
        await store_ip.add_documents(sample_documents, sample_embeddings)

        query_embedding = [0.1] * 128

        # Both should return results
        results_l2 = await store_l2.search(query_embedding, top_k=3)
        results_ip = await store_ip.search(query_embedding, top_k=3)

        assert len(results_l2) > 0
        assert len(results_ip) > 0

    @pytest.mark.asyncio
    async def test_batch_add(self):
        """Test adding documents in batches"""
        store = FAISSVectorStore(dimension=128)
        await store.initialize()

        # Add first batch
        docs1 = [
            Document(doc_id=f"doc{i}", content=f"Content {i}")
            for i in range(10)
        ]
        embeddings1 = [[float(i) / 10] * 128 for i in range(10)]

        await store.add_documents(docs1, embeddings1)

        # Add second batch
        docs2 = [
            Document(doc_id=f"doc{i}", content=f"Content {i}")
            for i in range(10, 20)
        ]
        embeddings2 = [[float(i) / 10] * 128 for i in range(10, 20)]

        await store.add_documents(docs2, embeddings2)

        assert len(store.documents) == 20
        assert store.index.ntotal == 20
