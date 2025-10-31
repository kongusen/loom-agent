"""
Integration tests for EmbeddingRetriever with ContextRetriever and Agent
"""

import pytest
from typing import List

from loom.retrieval import (
    EmbeddingRetriever,
    SimpleDomainAdapter,
    IndexStrategy,
    RetrievalConfig
)
from loom.builtin.retriever.faiss_store import FAISSVectorStore
from loom.core.context_retriever import ContextRetriever
from loom.interfaces.retriever import Document


class MockEmbedding:
    """Mock embedding for testing"""

    async def embed_query(self, text: str) -> List[float]:
        # Simple deterministic embedding
        return [float(ord(c)) / 256.0 for c in text[:128].ljust(128)]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_query(text) for text in texts]


@pytest.fixture
def knowledge_base_documents():
    """Sample knowledge base documents"""
    return [
        Document(
            doc_id="kb1",
            content="Loom is an AI agent framework that supports tool calling and RAG",
            metadata={"source": "docs", "section": "overview"}
        ),
        Document(
            doc_id="kb2",
            content="The Agent class is the main entry point. Use agent() to create instances",
            metadata={"source": "docs", "section": "api"}
        ),
        Document(
            doc_id="kb3",
            content="EmbeddingRetriever provides semantic search using vector embeddings",
            metadata={"source": "docs", "section": "retrieval"}
        ),
        Document(
            doc_id="kb4",
            content="DomainAdapter allows you to adapt any data source for retrieval",
            metadata={"source": "docs", "section": "retrieval"}
        ),
        Document(
            doc_id="kb5",
            content="You can use FAISS, Milvus, or Qdrant as vector stores",
            metadata={"source": "docs", "section": "backends"}
        ),
    ]


@pytest.mark.skipif(
    not pytest.importorskip("faiss", reason="FAISS not installed"),
    reason="FAISS not installed"
)
class TestEmbeddingRetrieverIntegration:
    """Integration tests for EmbeddingRetriever"""

    @pytest.mark.asyncio
    async def test_end_to_end_retrieval(self, knowledge_base_documents):
        """Test end-to-end retrieval workflow"""
        # Setup
        embedding = MockEmbedding()
        vector_store = FAISSVectorStore(dimension=128)
        adapter = SimpleDomainAdapter(knowledge_base_documents)

        retriever = EmbeddingRetriever(
            embedding=embedding,
            vector_store=vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(
                index_strategy=IndexStrategy.EAGER,
                top_k=3,
                similarity_threshold=0.0  # Low threshold for testing
            )
        )

        # Initialize
        await retriever.initialize()

        # Retrieve - query about framework
        results = await retriever.retrieve("What is Loom framework?")

        assert len(results) > 0
        assert len(results) <= 3
        # First result should be about Loom
        assert "Loom" in results[0].content or "framework" in results[0].content

    @pytest.mark.asyncio
    async def test_lazy_loading_workflow(self, knowledge_base_documents):
        """Test lazy loading workflow"""
        embedding = MockEmbedding()
        vector_store = FAISSVectorStore(dimension=128)
        adapter = SimpleDomainAdapter(knowledge_base_documents)

        retriever = EmbeddingRetriever(
            embedding=embedding,
            vector_store=vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(
                index_strategy=IndexStrategy.LAZY,
                top_k=2
            )
        )

        # Initialize (should index metadata only)
        await retriever.initialize()

        assert retriever._indexed_doc_count == 5

        # Retrieve (should lazy load full documents)
        results = await retriever.retrieve("vector embeddings")

        assert len(results) > 0
        # Full documents should be loaded
        for doc in results:
            assert len(doc.content) > 100  # Not truncated

    @pytest.mark.asyncio
    async def test_with_context_retriever(self, knowledge_base_documents):
        """Test integration with ContextRetriever"""
        embedding = MockEmbedding()
        vector_store = FAISSVectorStore(dimension=128)
        adapter = SimpleDomainAdapter(knowledge_base_documents)

        embedding_retriever = EmbeddingRetriever(
            embedding=embedding,
            vector_store=vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(
                index_strategy=IndexStrategy.EAGER,
                top_k=3
            )
        )

        await embedding_retriever.initialize()

        # Wrap in ContextRetriever
        context_retriever = ContextRetriever(
            retriever=embedding_retriever,
            top_k=3,
            auto_retrieve=True
        )

        # Retrieve context for query
        query = "How do I use the agent?"
        docs = await context_retriever.retrieve_for_query(query, top_k=3)

        assert len(docs) > 0
        assert all(isinstance(doc, Document) for doc in docs)

        # Format as context
        formatted = context_retriever.format_documents(docs)

        assert "Retrieved Context" in formatted
        assert "Document" in formatted

    @pytest.mark.asyncio
    async def test_metadata_filtering(self, knowledge_base_documents):
        """Test metadata filtering in retrieval"""
        embedding = MockEmbedding()
        vector_store = FAISSVectorStore(dimension=128)
        adapter = SimpleDomainAdapter(knowledge_base_documents)

        retriever = EmbeddingRetriever(
            embedding=embedding,
            vector_store=vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(index_strategy=IndexStrategy.EAGER)
        )

        await retriever.initialize()

        # Search with filter
        results = await retriever.retrieve(
            query="retrieval system",
            filters={"section": "retrieval"}
        )

        # All results should be from retrieval section
        assert all(
            doc.metadata.get("section") == "retrieval"
            for doc in results
        )

    @pytest.mark.asyncio
    async def test_caching_behavior(self, knowledge_base_documents):
        """Test caching improves performance"""
        embedding = MockEmbedding()
        vector_store = FAISSVectorStore(dimension=128)
        adapter = SimpleDomainAdapter(knowledge_base_documents)

        retriever = EmbeddingRetriever(
            embedding=embedding,
            vector_store=vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(
                index_strategy=IndexStrategy.LAZY,
                enable_cache=True
            )
        )

        await retriever.initialize()

        query = "vector search"

        # First retrieval
        await retriever.retrieve(query)

        assert query in retriever._embedding_cache

        # Second retrieval (should use cache)
        await retriever.retrieve(query)

        # Embedding cache should still have the query
        assert query in retriever._embedding_cache

        # Document cache should have loaded documents
        assert len(retriever._document_cache) > 0

    @pytest.mark.asyncio
    async def test_multiple_retrievals(self, knowledge_base_documents):
        """Test multiple different retrievals"""
        embedding = MockEmbedding()
        vector_store = FAISSVectorStore(dimension=128)
        adapter = SimpleDomainAdapter(knowledge_base_documents)

        retriever = EmbeddingRetriever(
            embedding=embedding,
            vector_store=vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(index_strategy=IndexStrategy.EAGER)
        )

        await retriever.initialize()

        # Multiple queries
        queries = [
            "What is Loom?",
            "How to use agents?",
            "Vector store backends",
        ]

        for query in queries:
            results = await retriever.retrieve(query, top_k=2)

            assert len(results) > 0
            assert len(results) <= 2
            assert all(hasattr(doc, 'score') for doc in results)

    @pytest.mark.asyncio
    async def test_stats_tracking(self, knowledge_base_documents):
        """Test statistics tracking"""
        embedding = MockEmbedding()
        vector_store = FAISSVectorStore(dimension=128)
        adapter = SimpleDomainAdapter(knowledge_base_documents)

        retriever = EmbeddingRetriever(
            embedding=embedding,
            vector_store=vector_store,
            domain_adapter=adapter,
            config=RetrievalConfig(index_strategy=IndexStrategy.EAGER)
        )

        await retriever.initialize()

        # Perform some retrievals
        await retriever.retrieve("query 1")
        await retriever.retrieve("query 2")

        stats = retriever.get_stats()

        assert stats["initialized"] is True
        assert stats["indexed_documents"] == 5
        assert stats["embedding_cache_size"] == 2
        assert stats["top_k"] == 5
