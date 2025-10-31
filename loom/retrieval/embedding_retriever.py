"""
Embedding-based Retriever

Core retrieval system using embeddings and vector search.
Provides semantic search with lazy loading and caching.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from loom.interfaces.retriever import BaseRetriever, Document
from loom.interfaces.embedding import BaseEmbedding
from loom.interfaces.vector_store import BaseVectorStore
from loom.retrieval.domain_adapter import DomainAdapter

logger = logging.getLogger(__name__)


class IndexStrategy(str, Enum):
    """Indexing strategy"""
    EAGER = "eager"
    """Index all documents at initialization"""

    LAZY = "lazy"
    """Index metadata at initialization, load full documents on demand"""

    INCREMENTAL = "incremental"
    """Index documents incrementally as they are accessed"""


@dataclass
class RetrievalConfig:
    """Retrieval configuration"""

    top_k: int = 5
    """Number of documents to retrieve"""

    similarity_threshold: float = 0.7
    """Minimum similarity score (0-1) for retrieved documents"""

    index_strategy: IndexStrategy = IndexStrategy.LAZY
    """Indexing strategy"""

    enable_cache: bool = True
    """Enable caching of embeddings and documents"""

    cache_ttl: int = 3600
    """Cache time-to-live in seconds"""

    batch_size: int = 100
    """Batch size for embedding generation"""


class EmbeddingRetriever(BaseRetriever):
    """
    Embedding-based retriever

    Provides semantic search using embeddings and vector stores.
    Supports lazy loading, caching, and domain adaptation.

    Key features:
    - Semantic search using embeddings
    - Multiple indexing strategies (eager/lazy/incremental)
    - Caching of embeddings and documents
    - Domain adaptation via DomainAdapter

    Example:
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

    def __init__(
        self,
        embedding: BaseEmbedding,
        vector_store: BaseVectorStore,
        domain_adapter: Optional[DomainAdapter] = None,
        config: Optional[RetrievalConfig] = None
    ):
        """
        Args:
            embedding: Embedding model
            vector_store: Vector storage backend
            domain_adapter: Domain adapter for data extraction
            config: Retrieval configuration
        """
        self.embedding = embedding
        self.vector_store = vector_store
        self.domain_adapter = domain_adapter
        self.config = config or RetrievalConfig()

        # Caches
        self._embedding_cache: Dict[str, List[float]] = {}
        self._document_cache: Dict[str, Document] = {}

        # State
        self._initialized = False
        self._indexed_doc_count = 0

    async def initialize(self) -> None:
        """Initialize the retriever"""
        if self._initialized:
            logger.debug("Retriever already initialized")
            return

        logger.info(f"Initializing retriever with strategy: {self.config.index_strategy}")

        try:
            if self.config.index_strategy == IndexStrategy.EAGER:
                await self._index_all_documents()
            elif self.config.index_strategy == IndexStrategy.LAZY:
                await self._index_metadata_only()
            # INCREMENTAL strategy indexes on-demand, no initialization needed

            self._initialized = True
            logger.info(f"Retriever initialized successfully. Indexed {self._indexed_doc_count} documents")

        except Exception as e:
            logger.error(f"Failed to initialize retriever: {e}", exc_info=True)
            raise

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Retrieve relevant documents

        Args:
            query: Query text
            top_k: Number of documents to retrieve (overrides config)
            filters: Metadata filters

        Returns:
            List of relevant documents sorted by similarity

        Example:
            results = await retriever.retrieve(
                query="Find user-related tables",
                top_k=5,
                filters={"type": "table"}
            )
        """
        if not self._initialized:
            await self.initialize()

        k = top_k or self.config.top_k

        try:
            # 1. Generate query embedding
            query_embedding = await self._get_query_embedding(query)

            # 2. Vector search
            candidates = await self.vector_store.search(
                query_embedding=query_embedding,
                top_k=k * 2,  # Get more candidates for filtering
                filters=filters
            )

            logger.debug(f"Vector search returned {len(candidates)} candidates")

            # 3. Filter by similarity threshold
            filtered_candidates = [
                doc for doc in candidates
                if doc.score is not None and doc.score >= self.config.similarity_threshold
            ]

            logger.debug(f"After filtering: {len(filtered_candidates)} documents")

            # 4. Lazy load full documents if needed
            if self.config.index_strategy == IndexStrategy.LAZY:
                filtered_candidates = await self._lazy_load_documents(filtered_candidates)

            # 5. Return top-k
            return filtered_candidates[:k]

        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            raise

    async def add_documents(
        self,
        documents: List[Document]
    ) -> None:
        """
        Add documents to the retrieval system

        Args:
            documents: Documents to add

        Example:
            await retriever.add_documents([
                Document(doc_id="1", content="Document 1"),
                Document(doc_id="2", content="Document 2"),
            ])
        """
        if not self._initialized:
            await self.initialize()

        # Filter documents
        if self.domain_adapter:
            documents = [doc for doc in documents if self.domain_adapter.should_index(doc)]

        # Index documents
        await self._index_documents_batch(documents)

    async def _get_query_embedding(self, query: str) -> List[float]:
        """
        Get query embedding with caching

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        # Check cache
        if self.config.enable_cache and query in self._embedding_cache:
            logger.debug(f"Query embedding cache hit: {query[:50]}...")
            return self._embedding_cache[query]

        # Generate embedding
        logger.debug(f"Generating embedding for query: {query[:50]}...")
        embedding = await self.embedding.embed_query(query)

        # Cache
        if self.config.enable_cache:
            self._embedding_cache[query] = embedding

        return embedding

    async def _lazy_load_documents(
        self,
        document_refs: List[Document]
    ) -> List[Document]:
        """
        Lazy load full document details

        Args:
            document_refs: Document references (may contain only metadata)

        Returns:
            Full documents with details
        """
        if not self.domain_adapter:
            return document_refs

        loaded_docs = []

        for doc_ref in document_refs:
            # Check cache
            if doc_ref.doc_id in self._document_cache:
                full_doc = self._document_cache[doc_ref.doc_id]
                full_doc.score = doc_ref.score
                loaded_docs.append(full_doc)
                continue

            try:
                # Load from adapter
                full_doc = await self.domain_adapter.load_document_details(doc_ref.doc_id)
                full_doc.score = doc_ref.score

                # Cache
                if self.config.enable_cache:
                    self._document_cache[doc_ref.doc_id] = full_doc

                loaded_docs.append(full_doc)

            except Exception as e:
                logger.warning(f"Failed to load document {doc_ref.doc_id}: {e}")
                # Fallback to reference
                loaded_docs.append(doc_ref)

        return loaded_docs

    async def _index_all_documents(self) -> None:
        """Index all documents (EAGER strategy)"""
        if not self.domain_adapter:
            logger.warning("No domain adapter provided, skipping indexing")
            return

        logger.info("Indexing all documents (EAGER strategy)")

        # Extract all documents
        documents = await self.domain_adapter.extract_documents(
            metadata_only=False
        )

        # Filter documents
        documents = [doc for doc in documents if self.domain_adapter.should_index(doc)]

        logger.info(f"Extracted {len(documents)} documents to index")

        # Index in batches
        await self._index_documents_batch(documents)

    async def _index_metadata_only(self) -> None:
        """Index metadata only (LAZY strategy)"""
        if not self.domain_adapter:
            logger.warning("No domain adapter provided, skipping indexing")
            return

        logger.info("Indexing metadata only (LAZY strategy)")

        # Extract lightweight documents
        documents = await self.domain_adapter.extract_documents(
            metadata_only=True
        )

        # Filter documents
        documents = [doc for doc in documents if self.domain_adapter.should_index(doc)]

        logger.info(f"Extracted {len(documents)} lightweight documents to index")

        # Index in batches
        await self._index_documents_batch(documents)

    async def _index_documents_batch(self, documents: List[Document]) -> None:
        """
        Index documents in batches

        Args:
            documents: Documents to index
        """
        batch_size = self.config.batch_size

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            # Format documents for embedding
            texts = [
                self.domain_adapter.format_for_embedding(doc)
                if self.domain_adapter else doc.content
                for doc in batch
            ]

            # Generate embeddings
            logger.debug(f"Generating embeddings for batch {i//batch_size + 1}")
            embeddings = await self.embedding.embed_documents(texts)

            # Store in vector store
            await self.vector_store.add_documents(batch, embeddings)

            # Cache documents
            if self.config.enable_cache:
                for doc in batch:
                    self._document_cache[doc.doc_id] = doc

            self._indexed_doc_count += len(batch)

        logger.info(f"Indexed {self._indexed_doc_count} documents")

    def clear_cache(self) -> None:
        """Clear all caches"""
        self._embedding_cache.clear()
        self._document_cache.clear()
        logger.info("Caches cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get retriever statistics

        Returns:
            Statistics dictionary
        """
        return {
            "initialized": self._initialized,
            "indexed_documents": self._indexed_doc_count,
            "embedding_cache_size": len(self._embedding_cache),
            "document_cache_size": len(self._document_cache),
            "index_strategy": self.config.index_strategy.value,
            "top_k": self.config.top_k,
            "similarity_threshold": self.config.similarity_threshold
        }
