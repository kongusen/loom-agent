"""
Loom Retrieval Module

Provides embedding-based semantic retrieval with lazy loading and caching.

Key components:
- EmbeddingRetriever: Core retrieval system using embeddings
- DomainAdapter: Interface for adapting domain-specific data
- IndexStrategy: Indexing strategies (EAGER/LAZY/INCREMENTAL)
- RetrievalConfig: Configuration for retrieval behavior

Example:
    from loom.retrieval import (
        EmbeddingRetriever,
        DomainAdapter,
        IndexStrategy,
        RetrievalConfig
    )
    from loom.builtin.embeddings import OpenAIEmbedding
    from loom.builtin.retriever import FAISSVectorStore

    # Create retriever
    retriever = EmbeddingRetriever(
        embedding=OpenAIEmbedding(model="text-embedding-3-small"),
        vector_store=FAISSVectorStore(dimension=1536),
        domain_adapter=my_adapter,
        config=RetrievalConfig(
            index_strategy=IndexStrategy.LAZY,
            top_k=5
        )
    )

    # Initialize
    await retriever.initialize()

    # Retrieve
    results = await retriever.retrieve("user query", top_k=5)
"""

from loom.retrieval.embedding_retriever import (
    EmbeddingRetriever,
    IndexStrategy,
    RetrievalConfig
)
from loom.retrieval.domain_adapter import (
    DomainAdapter,
    SimpleDomainAdapter
)

__all__ = [
    # Core classes
    "EmbeddingRetriever",
    "DomainAdapter",
    "SimpleDomainAdapter",

    # Enums
    "IndexStrategy",

    # Config
    "RetrievalConfig",
]
