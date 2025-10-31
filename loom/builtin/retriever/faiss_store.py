"""
FAISS Vector Store

Lightweight, in-memory vector storage using FAISS.
Ideal for development and small to medium scale deployments.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from loom.interfaces.vector_store import BaseVectorStore
from loom.interfaces.retriever import Document

logger = logging.getLogger(__name__)


class FAISSVectorStore(BaseVectorStore):
    """
    FAISS-based vector storage

    Lightweight, in-memory vector database using Facebook's FAISS library.
    Ideal for:
    - Development and testing
    - Small to medium scale deployments (< 1M documents)
    - Applications without persistence requirements

    Features:
    - Fast similarity search
    - Multiple index types (Flat, IVF, HNSW)
    - In-memory storage
    - Optional persistence

    Example:
        # Basic usage
        store = FAISSVectorStore(dimension=1536)
        await store.initialize()

        # Add documents
        await store.add_documents(
            documents=[doc1, doc2],
            embeddings=[[0.1, ...], [0.2, ...]]
        )

        # Search
        results = await store.search(
            query_embedding=[0.15, ...],
            top_k=5
        )

        # Advanced: Use IVF index for larger datasets
        store = FAISSVectorStore(
            dimension=1536,
            index_type="IVF",
            nlist=100  # Number of clusters
        )
    """

    def __init__(
        self,
        dimension: int,
        index_type: str = "Flat",
        metric: str = "L2",
        nlist: int = 100,
        nprobe: int = 10
    ):
        """
        Args:
            dimension: Embedding dimension
            index_type: Index type ("Flat", "IVF", "HNSW")
            metric: Distance metric ("L2" or "IP" for inner product)
            nlist: Number of clusters for IVF index
            nprobe: Number of clusters to search in IVF
        """
        self.dimension = dimension
        self.index_type = index_type
        self.metric = metric
        self.nlist = nlist
        self.nprobe = nprobe

        # FAISS index
        self.index = None

        # Document storage
        self.documents: Dict[str, Document] = {}
        self.id_to_index: Dict[str, int] = {}
        self.index_to_id: Dict[int, str] = {}

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize FAISS index"""
        if self._initialized:
            return

        try:
            import faiss
        except ImportError:
            raise ImportError(
                "FAISS is required for FAISSVectorStore. "
                "Install it with: pip install faiss-cpu  or  pip install faiss-gpu"
            )

        # Create index based on type
        if self.index_type == "Flat":
            if self.metric == "L2":
                self.index = faiss.IndexFlatL2(self.dimension)
            else:  # IP (Inner Product)
                self.index = faiss.IndexFlatIP(self.dimension)

        elif self.index_type == "IVF":
            if self.metric == "L2":
                quantizer = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIVFFlat(
                    quantizer,
                    self.dimension,
                    self.nlist
                )
            else:
                quantizer = faiss.IndexFlatIP(self.dimension)
                self.index = faiss.IndexIVFFlat(
                    quantizer,
                    self.dimension,
                    self.nlist
                )
            # IVF needs training (will be done when first batch is added)
            self.index.nprobe = self.nprobe

        elif self.index_type == "HNSW":
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)

        else:
            raise ValueError(f"Unknown index type: {self.index_type}")

        self._initialized = True
        logger.info(f"FAISS index initialized: type={self.index_type}, dimension={self.dimension}")

    async def add_documents(
        self,
        documents: List[Document],
        embeddings: List[List[float]]
    ) -> None:
        """
        Add documents with their embeddings

        Args:
            documents: List of documents
            embeddings: List of embedding vectors
        """
        if not self._initialized:
            await self.initialize()

        if len(documents) != len(embeddings):
            raise ValueError("Number of documents must match number of embeddings")

        import numpy as np

        # Convert embeddings to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # Train IVF index if needed
        if self.index_type == "IVF" and not self.index.is_trained:
            logger.info(f"Training IVF index with {len(embeddings)} vectors")
            self.index.train(embeddings_array)

        # Get current index size
        start_index = len(self.id_to_index)

        # Add to FAISS
        self.index.add(embeddings_array)

        # Store documents and mappings
        for i, doc in enumerate(documents):
            index = start_index + i
            self.documents[doc.doc_id] = doc
            self.id_to_index[doc.doc_id] = index
            self.index_to_id[index] = doc.doc_id

        logger.debug(f"Added {len(documents)} documents. Total: {len(self.documents)}")

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Search for similar documents

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Metadata filters (applied post-search)

        Returns:
            List of documents with similarity scores
        """
        if not self._initialized:
            await self.initialize()

        if self.index.ntotal == 0:
            logger.warning("No documents in index")
            return []

        import numpy as np

        # Convert query to numpy array
        query_array = np.array([query_embedding], dtype=np.float32)

        # Search
        # Get more results if we need to filter
        search_k = top_k * 3 if filters else top_k
        distances, indices = self.index.search(query_array, search_k)

        # Convert results to documents
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:  # FAISS returns -1 for missing results
                break

            # Get document
            doc_id = self.index_to_id[idx]
            doc = self.documents[doc_id]

            # Apply filters
            if filters and not self._match_filters(doc, filters):
                continue

            # Calculate similarity score
            distance = distances[0][i]
            score = self._distance_to_score(distance)

            # Create result document with score
            result_doc = Document(
                doc_id=doc.doc_id,
                content=doc.content,
                score=score,
                metadata=doc.metadata
            )

            results.append(result_doc)

            if len(results) >= top_k:
                break

        return results

    async def get_document(self, doc_id: str) -> Optional[Document]:
        """
        Get document by ID

        Args:
            doc_id: Document identifier

        Returns:
            Document if found, None otherwise
        """
        return self.documents.get(doc_id)

    async def delete(self, doc_ids: List[str]) -> None:
        """
        Delete documents

        Note: FAISS doesn't support efficient deletion.
        This implementation removes from metadata but not from index.
        For true deletion, rebuild the index.

        Args:
            doc_ids: List of document IDs to delete
        """
        for doc_id in doc_ids:
            if doc_id in self.documents:
                del self.documents[doc_id]
                if doc_id in self.id_to_index:
                    index = self.id_to_index[doc_id]
                    del self.id_to_index[doc_id]
                    del self.index_to_id[index]

        logger.warning(
            f"Deleted {len(doc_ids)} documents from metadata. "
            "Note: FAISS index still contains vectors. Rebuild index for full deletion."
        )

    def _match_filters(self, doc: Document, filters: Dict[str, Any]) -> bool:
        """Check if document matches metadata filters"""
        if not doc.metadata:
            return False

        for key, value in filters.items():
            if doc.metadata.get(key) != value:
                return False

        return True

    def _distance_to_score(self, distance: float) -> float:
        """
        Convert distance to similarity score

        Args:
            distance: Distance from FAISS (L2 or IP)

        Returns:
            Similarity score (0-1, higher is better)
        """
        if self.metric == "L2":
            # L2 distance: lower is better
            # Convert to similarity: 1 / (1 + distance)
            return 1.0 / (1.0 + distance)
        else:
            # Inner product: higher is better
            # Assuming normalized vectors, IP is in [-1, 1]
            # Convert to [0, 1]
            return (distance + 1.0) / 2.0

    async def persist(self, path: str) -> None:
        """
        Save index to disk

        Args:
            path: File path to save index
        """
        if not self._initialized:
            raise RuntimeError("Index not initialized")

        import faiss
        import pickle

        # Save FAISS index
        faiss.write_index(self.index, f"{path}.index")

        # Save metadata
        metadata = {
            "documents": self.documents,
            "id_to_index": self.id_to_index,
            "index_to_id": self.index_to_id,
            "dimension": self.dimension,
            "index_type": self.index_type,
            "metric": self.metric,
            "nlist": self.nlist,
            "nprobe": self.nprobe
        }

        with open(f"{path}.metadata", "wb") as f:
            pickle.dump(metadata, f)

        logger.info(f"Index persisted to {path}")

    @classmethod
    async def load(cls, path: str) -> "FAISSVectorStore":
        """
        Load index from disk

        Args:
            path: File path to load index from

        Returns:
            FAISSVectorStore instance
        """
        import faiss
        import pickle

        # Load metadata
        with open(f"{path}.metadata", "rb") as f:
            metadata = pickle.load(f)

        # Create instance
        instance = cls(
            dimension=metadata["dimension"],
            index_type=metadata["index_type"],
            metric=metadata["metric"],
            nlist=metadata["nlist"],
            nprobe=metadata["nprobe"]
        )

        # Load FAISS index
        instance.index = faiss.read_index(f"{path}.index")
        instance._initialized = True

        # Load metadata
        instance.documents = metadata["documents"]
        instance.id_to_index = metadata["id_to_index"]
        instance.index_to_id = metadata["index_to_id"]

        logger.info(f"Index loaded from {path}")

        return instance

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics

        Returns:
            Statistics dictionary
        """
        return {
            "initialized": self._initialized,
            "total_documents": len(self.documents),
            "index_size": self.index.ntotal if self.index else 0,
            "dimension": self.dimension,
            "index_type": self.index_type,
            "metric": self.metric
        }
