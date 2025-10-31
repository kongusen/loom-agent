"""
Unit tests for EmbeddingRetriever
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from loom.retrieval import (
    EmbeddingRetriever,
    DomainAdapter,
    SimpleDomainAdapter,
    IndexStrategy,
    RetrievalConfig
)
from loom.interfaces.retriever import Document


class MockEmbedding:
    """Mock embedding model"""

    async def embed_query(self, text: str) -> List[float]:
        # Simple hash-based embedding
        hash_val = hash(text) % 1000
        return [float(hash_val) / 1000.0] * 128

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_query(text) for text in texts]


class MockVectorStore:
    """Mock vector store"""

    def __init__(self):
        self.documents = []
        self.embeddings = []

    async def add_documents(
        self,
        documents: List[Document],
        embeddings: List[List[float]]
    ) -> None:
        self.documents.extend(documents)
        self.embeddings.extend(embeddings)

    async def search(
        self,
        query_embedding: List[float],
        top_k: int,
        filters=None
    ) -> List[Document]:
        # Simple mock: return first top_k documents with decreasing scores
        results = []
        for i, doc in enumerate(self.documents[:top_k]):
            doc_copy = Document(
                doc_id=doc.doc_id,
                content=doc.content,
                metadata=doc.metadata,
                score=1.0 - (i * 0.1)  # Decreasing scores
            )
            results.append(doc_copy)
        return results


@pytest.fixture
def sample_documents():
    """Sample documents for testing"""
    return [
        Document(
            doc_id="doc1",
            content="This is about machine learning",
            metadata={"topic": "ML"}
        ),
        Document(
            doc_id="doc2",
            content="This is about databases",
            metadata={"topic": "DB"}
        ),
        Document(
            doc_id="doc3",
            content="This is about web development",
            metadata={"topic": "Web"}
        ),
    ]


@pytest.fixture
def mock_embedding():
    """Mock embedding model"""
    return MockEmbedding()


@pytest.fixture
def mock_vector_store():
    """Mock vector store"""
    return MockVectorStore()


class TestDomainAdapter:
    """Tests for DomainAdapter"""

    @pytest.mark.asyncio
    async def test_simple_domain_adapter(self, sample_documents):
        """Test SimpleDomainAdapter"""
        adapter = SimpleDomainAdapter(sample_documents)

        # Extract all documents
        docs = await adapter.extract_documents()
        assert len(docs) == 3
        assert docs[0].doc_id == "doc1"

        # Extract metadata only
        metadata_docs = await adapter.extract_documents(metadata_only=True)
        assert len(metadata_docs) == 3
        # Content should be truncated
        for doc in metadata_docs:
            assert len(doc.content) <= 103  # 100 + "..."

        # Load document details
        doc = await adapter.load_document_details("doc1")
        assert doc.doc_id == "doc1"
        assert doc.content == "This is about machine learning"


class TestEmbeddingRetriever:
    """Tests for EmbeddingRetriever"""

    @pytest.mark.asyncio
    async def test_initialization_lazy(
        self,
        mock_embedding,
        mock_vector_store,
        sample_documents
    ):
        """Test lazy initialization"""
        adapter = SimpleDomainAdapter(sample_documents)

        retriever = EmbeddingRetriever(
            embedding=mock_embedding,
            vector_store=mock_vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(index_strategy=IndexStrategy.LAZY)
        )

        await retriever.initialize()

        assert retriever._initialized
        assert retriever._indexed_doc_count == 3
        assert len(mock_vector_store.documents) == 3

    @pytest.mark.asyncio
    async def test_initialization_eager(
        self,
        mock_embedding,
        mock_vector_store,
        sample_documents
    ):
        """Test eager initialization"""
        adapter = SimpleDomainAdapter(sample_documents)

        retriever = EmbeddingRetriever(
            embedding=mock_embedding,
            vector_store=mock_vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(index_strategy=IndexStrategy.EAGER)
        )

        await retriever.initialize()

        assert retriever._initialized
        assert retriever._indexed_doc_count == 3
        assert len(mock_vector_store.documents) == 3

    @pytest.mark.asyncio
    async def test_retrieve(
        self,
        mock_embedding,
        mock_vector_store,
        sample_documents
    ):
        """Test document retrieval"""
        adapter = SimpleDomainAdapter(sample_documents)

        retriever = EmbeddingRetriever(
            embedding=mock_embedding,
            vector_store=mock_vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(
                index_strategy=IndexStrategy.LAZY,
                top_k=2,
                similarity_threshold=0.5
            )
        )

        await retriever.initialize()

        # Retrieve documents
        results = await retriever.retrieve("machine learning")

        assert len(results) <= 2  # top_k=2
        assert all(doc.score >= 0.5 for doc in results)  # threshold=0.5
        assert all(hasattr(doc, 'score') for doc in results)

    @pytest.mark.asyncio
    async def test_embedding_cache(
        self,
        mock_embedding,
        mock_vector_store,
        sample_documents
    ):
        """Test embedding caching"""
        adapter = SimpleDomainAdapter(sample_documents)

        retriever = EmbeddingRetriever(
            embedding=mock_embedding,
            vector_store=mock_vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(
                index_strategy=IndexStrategy.LAZY,
                enable_cache=True
            )
        )

        await retriever.initialize()

        # First retrieval
        query = "test query"
        await retriever.retrieve(query)

        assert query in retriever._embedding_cache

        # Second retrieval (should use cache)
        await retriever.retrieve(query)

        # Cache should still have the embedding
        assert query in retriever._embedding_cache

    @pytest.mark.asyncio
    async def test_clear_cache(
        self,
        mock_embedding,
        mock_vector_store,
        sample_documents
    ):
        """Test cache clearing"""
        adapter = SimpleDomainAdapter(sample_documents)

        retriever = EmbeddingRetriever(
            embedding=mock_embedding,
            vector_store=mock_vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(enable_cache=True)
        )

        await retriever.initialize()
        await retriever.retrieve("test")

        assert len(retriever._embedding_cache) > 0

        retriever.clear_cache()

        assert len(retriever._embedding_cache) == 0
        assert len(retriever._document_cache) == 0

    @pytest.mark.asyncio
    async def test_get_stats(
        self,
        mock_embedding,
        mock_vector_store,
        sample_documents
    ):
        """Test statistics"""
        adapter = SimpleDomainAdapter(sample_documents)

        retriever = EmbeddingRetriever(
            embedding=mock_embedding,
            vector_store=mock_vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(index_strategy=IndexStrategy.LAZY)
        )

        await retriever.initialize()

        stats = retriever.get_stats()

        assert stats["initialized"] is True
        assert stats["indexed_documents"] == 3
        assert stats["index_strategy"] == "lazy"
        assert stats["top_k"] == 5

    @pytest.mark.asyncio
    async def test_without_adapter(
        self,
        mock_embedding,
        mock_vector_store
    ):
        """Test retriever without domain adapter"""
        retriever = EmbeddingRetriever(
            embedding=mock_embedding,
            vector_store=mock_vector_store,
            domain_adapter=None,
            config=RetrievalConfig()
        )

        # Should initialize without error
        await retriever.initialize()

        assert retriever._initialized
        assert retriever._indexed_doc_count == 0


@pytest.mark.asyncio
async def test_retrieval_config_defaults():
    """Test default retrieval config"""
    config = RetrievalConfig()

    assert config.top_k == 5
    assert config.similarity_threshold == 0.7
    assert config.index_strategy == IndexStrategy.LAZY
    assert config.enable_cache is True
    assert config.cache_ttl == 3600
    assert config.batch_size == 100
