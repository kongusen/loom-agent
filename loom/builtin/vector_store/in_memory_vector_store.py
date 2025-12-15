"""
In-Memory Vector Store - Lightweight vector storage with NumPy/FAISS

Provides zero-config vector search for RAG without external dependencies.
Supports both NumPy (pure Python) and FAISS (optimized) backends.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logging.warning("NumPy not available. InMemoryVectorStore will not work.")

from loom.interfaces.vector_store import BaseVectorStore
from loom.interfaces.retriever import Document


logger = logging.getLogger(__name__)


@dataclass
class VectorEntry:
    """Vector storage entry"""
    doc_id: str
    vector: "np.ndarray"  # type: ignore
    document: Document


class InMemoryVectorStore:
    """
    In-memory vector store with NumPy/FAISS backend.

    Features:
    - Cosine similarity search (inner product on normalized vectors)
    - Optional FAISS acceleration
    - Metadata filtering
    - Zero-config, ready to use

    Use Cases:
    - Small scale data (< 10,000 documents)
    - Development and testing
    - No persistence required

    Example:
        ```python
        from loom.builtin.vector_store import InMemoryVectorStore

        # Initialize
        store = InMemoryVectorStore(dimension=384)
        await store.initialize()

        # Add vectors
        await store.add_vectors(
            vectors=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
            documents=[
                Document(content="Doc 1", metadata={}),
                Document(content="Doc 2", metadata={})
            ]
        )

        # Search
        results = await store.search(
            query_vector=[0.1, 0.2, ...],
            top_k=5,
            filters={"category": "tutorial"}
        )

        for doc, score in results:
            print(f"Score: {score:.2f}, Content: {doc.content}")
        ```

    Performance:
    - NumPy backend: ~100 docs/sec search
    - FAISS backend: ~10,000 docs/sec search (with FAISS installed)
    """

    def __init__(
        self,
        dimension: int = 384,
        use_faiss: bool = True,
    ):
        """
        Initialize vector store.

        Args:
            dimension: Vector dimension (must match embedding model)
            use_faiss: Whether to use FAISS acceleration (requires faiss-cpu)
        """
        if not HAS_NUMPY:
            raise RuntimeError(
                "NumPy is required for InMemoryVectorStore. "
                "Install it with: pip install numpy"
            )

        self.dimension = dimension
        self.use_faiss = use_faiss
        self._entries: List[VectorEntry] = []
        self._index = None  # FAISS index (if available)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize vector store and FAISS index if available."""
        if self._initialized:
            return

        if self.use_faiss:
            try:
                import faiss  # type: ignore

                # Use IndexFlatIP for inner product (cosine similarity on normalized vectors)
                self._index = faiss.IndexFlatIP(self.dimension)
                logger.info(
                    f"[InMemoryVectorStore] Using FAISS acceleration (dim={self.dimension})"
                )
            except ImportError:
                logger.info(
                    "[InMemoryVectorStore] FAISS not available, using NumPy fallback. "
                    "Install FAISS for better performance: pip install faiss-cpu"
                )
                self._index = None

        self._initialized = True

    async def add_vectors(
        self,
        vectors: List[List[float]],
        documents: List[Document],
    ) -> None:
        """
        Add vectors to the store.

        Vectors are automatically normalized for cosine similarity search.

        Args:
            vectors: List of vectors (each vector is a list of floats)
            documents: Corresponding documents (must match vectors length)

        Raises:
            ValueError: If vectors and documents have different lengths
        """
        if not self._initialized:
            await self.initialize()

        if len(vectors) != len(documents):
            raise ValueError(
                f"Vectors and documents must have same length: "
                f"got {len(vectors)} vectors and {len(documents)} documents"
            )

        for vec, doc in zip(vectors, documents):
            # Convert to numpy and normalize
            vec_np = np.array(vec, dtype=np.float32)

            # Normalize for cosine similarity (L2 norm)
            norm = np.linalg.norm(vec_np)
            if norm > 0:
                vec_np = vec_np / norm

            # Generate doc_id if not provided
            doc_id = doc.doc_id or self._generate_id()

            # Create entry
            entry = VectorEntry(
                doc_id=doc_id,
                vector=vec_np,
                document=Document(
                    content=doc.content,
                    metadata=doc.metadata,
                    score=doc.score,
                    doc_id=doc_id,
                ),
            )
            self._entries.append(entry)

            # Add to FAISS index if available
            if self._index is not None:
                self._index.add(vec_np.reshape(1, -1))

        logger.debug(
            f"[InMemoryVectorStore] Added {len(vectors)} vectors. "
            f"Total: {len(self._entries)} vectors"
        )

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Document, float]]:
        """
        Search for similar vectors.

        Uses cosine similarity (inner product on normalized vectors).
        Higher scores indicate higher similarity.

        Args:
            query_vector: Query vector
            top_k: Number of results to return
            filters: Optional metadata filters (e.g., {"category": "tutorial"})

        Returns:
            List of (Document, score) tuples, sorted by score (descending)

        Example:
            ```python
            results = await store.search(
                query_vector=[0.1, 0.2, ...],
                top_k=3,
                filters={"tier": "longterm"}
            )

            for doc, score in results:
                print(f"Relevance: {score:.2f}")
                print(f"Content: {doc.content}")
                print(f"Metadata: {doc.metadata}")
            ```
        """
        if not self._entries:
            return []

        # Normalize query vector
        query_np = np.array(query_vector, dtype=np.float32)
        norm = np.linalg.norm(query_np)
        if norm > 0:
            query_np = query_np / norm

        if self._index is not None:
            # Use FAISS for search
            return await self._search_with_faiss(query_np, top_k, filters)
        else:
            # Fallback to NumPy
            return await self._search_with_numpy(query_np, top_k, filters)

    async def _search_with_faiss(
        self,
        query_np: "np.ndarray",  # type: ignore
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Tuple[Document, float]]:
        """Search using FAISS index."""
        # Search more than top_k to account for filtered results
        search_k = min(top_k * 3, len(self._entries))

        scores, indices = self._index.search(query_np.reshape(1, -1), search_k)
        scores = scores[0]
        indices = indices[0]

        # Apply filters and collect results
        results = []
        for idx, score in zip(indices, scores):
            if idx < 0 or idx >= len(self._entries):
                continue

            entry = self._entries[idx]

            # Apply metadata filters
            if self._match_filters(entry.document, filters):
                # Update document score
                doc_with_score = Document(
                    content=entry.document.content,
                    metadata=entry.document.metadata,
                    score=float(score),
                    doc_id=entry.document.doc_id,
                )
                results.append((doc_with_score, float(score)))

                if len(results) >= top_k:
                    break

        return results

    async def _search_with_numpy(
        self,
        query_np: "np.ndarray",  # type: ignore
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Tuple[Document, float]]:
        """Search using NumPy (slower but no dependencies)."""
        similarities = []

        for entry in self._entries:
            # Apply filters first
            if not self._match_filters(entry.document, filters):
                continue

            # Compute cosine similarity (dot product of normalized vectors)
            similarity = float(np.dot(query_np, entry.vector))

            doc_with_score = Document(
                content=entry.document.content,
                metadata=entry.document.metadata,
                score=similarity,
                doc_id=entry.document.doc_id,
            )
            similarities.append((doc_with_score, similarity))

        # Sort by similarity (descending) and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def _match_filters(
        self,
        doc: Document,
        filters: Optional[Dict[str, Any]],
    ) -> bool:
        """Check if document matches metadata filters."""
        if not filters:
            return True

        for key, value in filters.items():
            if doc.metadata.get(key) != value:
                return False

        return True

    async def delete(self, doc_ids: List[str]) -> None:
        """
        Delete documents by IDs.

        Note: This rebuilds the index, which can be slow for large datasets.

        Args:
            doc_ids: List of document IDs to delete
        """
        # Remove entries
        self._entries = [e for e in self._entries if e.doc_id not in doc_ids]

        # Rebuild FAISS index
        if self._index is not None:
            import faiss  # type: ignore

            self._index = faiss.IndexFlatIP(self.dimension)

            if self._entries:
                # Re-add all vectors
                vectors = np.stack([e.vector for e in self._entries])
                self._index.add(vectors)

        logger.debug(
            f"[InMemoryVectorStore] Deleted {len(doc_ids)} documents. "
            f"Remaining: {len(self._entries)}"
        )

    async def clear(self) -> None:
        """Clear all vectors from the store."""
        self._entries.clear()

        if self._index is not None:
            import faiss  # type: ignore

            self._index = faiss.IndexFlatIP(self.dimension)

        logger.debug("[InMemoryVectorStore] Cleared all vectors")

    async def close(self) -> None:
        """Close the store (no-op for in-memory storage)."""
        pass

    def _generate_id(self) -> str:
        """Generate unique document ID."""
        from uuid import uuid4
        return str(uuid4())

    def __len__(self) -> int:
        """Return number of vectors in the store."""
        return len(self._entries)

    def __repr__(self) -> str:
        """String representation."""
        backend = "FAISS" if self._index is not None else "NumPy"
        return (
            f"InMemoryVectorStore(dimension={self.dimension}, "
            f"vectors={len(self._entries)}, backend={backend})"
        )
