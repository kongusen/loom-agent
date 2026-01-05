"""
Vector Store Abstraction Layer
Provides pluggable interface for different vector database backends.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np


@dataclass
class VectorSearchResult:
    """Result from vector search"""
    id: str
    score: float
    metadata: Dict[str, Any]


class VectorStoreProvider(ABC):
    """
    Abstract base class for vector store implementations.
    Users can implement this interface to integrate their preferred vector DB.
    """

    @abstractmethod
    async def add(
        self,
        id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add a vector to the store.

        Args:
            id: Unique identifier
            text: Original text content
            embedding: Vector embedding
            metadata: Additional metadata

        Returns:
            Success status
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of search results with scores
        """
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete a vector by ID."""
        pass

    @abstractmethod
    async def update(
        self,
        id: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update vector or metadata."""
        pass

    @abstractmethod
    async def get(self, id: str) -> Optional[VectorSearchResult]:
        """Retrieve a specific vector by ID."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all vectors."""
        pass


class InMemoryVectorStore(VectorStoreProvider):
    """
    Simple in-memory vector store using numpy.
    Suitable for development and small-scale deployments.
    """

    def __init__(self):
        self._vectors: Dict[str, np.ndarray] = {}
        self._texts: Dict[str, str] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    async def add(
        self,
        id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        self._vectors[id] = np.array(embedding)
        self._texts[id] = text
        self._metadata[id] = metadata or {}
        return True

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        if not self._vectors:
            return []

        query_vec = np.array(query_embedding)

        # Calculate cosine similarity
        scores = []
        for id, vec in self._vectors.items():
            # Apply metadata filter if provided
            if filter_metadata:
                if not self._matches_filter(self._metadata[id], filter_metadata):
                    continue

            # Cosine similarity
            similarity = np.dot(query_vec, vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(vec)
            )
            scores.append((id, float(similarity)))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top K
        results = []
        for id, score in scores[:top_k]:
            results.append(VectorSearchResult(
                id=id,
                score=score,
                metadata=self._metadata[id]
            ))

        return results

    async def delete(self, id: str) -> bool:
        if id in self._vectors:
            del self._vectors[id]
            del self._texts[id]
            del self._metadata[id]
            return True
        return False

    async def update(
        self,
        id: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if id not in self._vectors:
            return False

        if embedding:
            self._vectors[id] = np.array(embedding)
        if metadata:
            self._metadata[id].update(metadata)

        return True

    async def get(self, id: str) -> Optional[VectorSearchResult]:
        if id not in self._vectors:
            return None

        return VectorSearchResult(
            id=id,
            score=1.0,
            metadata=self._metadata[id]
        )

    async def clear(self) -> bool:
        self._vectors.clear()
        self._texts.clear()
        self._metadata.clear()
        return True

    def _matches_filter(self, metadata: Dict, filter_dict: Dict) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True


# Example implementations for popular vector DBs

class QdrantVectorStore(VectorStoreProvider):
    """
    Qdrant vector store implementation.

    Usage:
        store = QdrantVectorStore(
            url="http://localhost:6333",
            collection_name="loom_memory"
        )
    """

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection_name: str = "loom_memory",
        vector_size: int = 1536  # OpenAI embedding size
    ):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError:
            raise ImportError(
                "qdrant-client not installed. "
                "Install with: pip install qdrant-client"
            )

        self.client = QdrantClient(url=url)
        self.collection_name = collection_name

        # Create collection if not exists
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
        except:
            pass  # Collection already exists

    async def add(
        self,
        id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        from qdrant_client.models import PointStruct

        payload = {"text": text, **(metadata or {})}

        self.client.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(
                id=id,
                vector=embedding,
                payload=payload
            )]
        )
        return True

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        # Build filter if provided
        query_filter = None
        if filter_metadata:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_metadata.items()
            ]
            query_filter = Filter(must=conditions)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            query_filter=query_filter
        )

        return [
            VectorSearchResult(
                id=str(r.id),
                score=r.score,
                metadata=r.payload
            )
            for r in results
        ]

    async def delete(self, id: str) -> bool:
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[id]
        )
        return True

    async def update(
        self,
        id: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        # Qdrant doesn't have direct update, use upsert
        if embedding:
            from qdrant_client.models import PointStruct
            self.client.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(id=id, vector=embedding, payload=metadata or {})]
            )
        elif metadata:
            self.client.set_payload(
                collection_name=self.collection_name,
                payload=metadata,
                points=[id]
            )
        return True

    async def get(self, id: str) -> Optional[VectorSearchResult]:
        results = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[id]
        )

        if not results:
            return None

        r = results[0]
        return VectorSearchResult(
            id=str(r.id),
            score=1.0,
            metadata=r.payload
        )

    async def clear(self) -> bool:
        self.client.delete_collection(self.collection_name)
        return True


class ChromaVectorStore(VectorStoreProvider):
    """
    ChromaDB vector store implementation.

    Usage:
        store = ChromaVectorStore(
            persist_directory="./chroma_db",
            collection_name="loom_memory"
        )
    """

    def __init__(
        self,
        persist_directory: Optional[str] = None,
        collection_name: str = "loom_memory"
    ):
        try:
            import chromadb
        except ImportError:
            raise ImportError(
                "chromadb not installed. "
                "Install with: pip install chromadb"
            )

        if persist_directory:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.Client()

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    async def add(
        self,
        id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        self.collection.add(
            ids=[id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata or {}]
        )
        return True

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata
        )

        search_results = []
        for i in range(len(results['ids'][0])):
            search_results.append(VectorSearchResult(
                id=results['ids'][0][i],
                score=1.0 - results['distances'][0][i],  # Convert distance to similarity
                metadata=results['metadatas'][0][i]
            ))

        return search_results

    async def delete(self, id: str) -> bool:
        self.collection.delete(ids=[id])
        return True

    async def update(
        self,
        id: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        if embedding:
            self.collection.update(
                ids=[id],
                embeddings=[embedding],
                metadatas=[metadata or {}]
            )
        elif metadata:
            self.collection.update(
                ids=[id],
                metadatas=[metadata]
            )
        return True

    async def get(self, id: str) -> Optional[VectorSearchResult]:
        results = self.collection.get(ids=[id])

        if not results['ids']:
            return None

        return VectorSearchResult(
            id=results['ids'][0],
            score=1.0,
            metadata=results['metadatas'][0]
        )

    async def clear(self) -> bool:
        self.client.delete_collection(self.collection.name)
        return True
