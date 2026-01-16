"""
Vector Store Abstraction Layer
Provides pluggable interface for different vector database backends.
"""
from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, cast

import numpy as np


@dataclass
class VectorSearchResult:
    """Result from vector search"""
    id: str
    score: float
    metadata: dict[str, Any]


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
        embedding: list[float],
        metadata: dict[str, Any] | None = None
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
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None
    ) -> list[VectorSearchResult]:
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
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> bool:
        """Update vector or metadata."""
        pass

    @abstractmethod
    async def get(self, id: str) -> VectorSearchResult | None:
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
        self._vectors: dict[str, np.ndarray] = {}
        self._texts: dict[str, str] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    async def add(
        self,
        id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None
    ) -> bool:
        self._vectors[id] = np.array(embedding)
        self._texts[id] = text
        self._metadata[id] = metadata or {}
        return True

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None
    ) -> list[VectorSearchResult]:
        if not self._vectors:
            return []

        query_vec = np.array(query_embedding)

        # Calculate cosine similarity
        scores = []
        for id, vec in self._vectors.items():
            # Apply metadata filter if provided
            if filter_metadata and not self._matches_filter(self._metadata[id], filter_metadata):
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
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> bool:
        if id not in self._vectors:
            return False

        if embedding:
            self._vectors[id] = np.array(embedding)
        if metadata:
            self._metadata[id].update(metadata)

        return True

    async def get(self, id: str) -> VectorSearchResult | None:
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

    def _matches_filter(self, metadata: dict, filter_dict: dict) -> bool:
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
            ) from None

        self.client = QdrantClient(url=url)
        self.collection_name = collection_name

        # Create collection if not exists
        with suppress(Exception):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )

    async def add(
        self,
        id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None
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
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None
    ) -> list[VectorSearchResult]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        # Build filter if provided
        query_filter = None
        if filter_metadata:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_metadata.items()
            ]
            query_filter = Filter(must=cast(Any, conditions))

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
                metadata=r.payload or {}
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
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None
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

    async def get(self, id: str) -> VectorSearchResult | None:
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
            metadata=r.payload or {}
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
        persist_directory: str | None = None,
        collection_name: str = "loom_memory"
    ):
        try:
            import chromadb
        except ImportError:
            raise ImportError(
                "chromadb not installed. "
                "Install with: pip install chromadb"
            ) from None

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
        embedding: list[float],
        metadata: dict[str, Any] | None = None
    ) -> bool:
        self.collection.add(
            ids=[id],
            embeddings=cast(Any, [embedding]),
            documents=[text],
            metadatas=[metadata or {}]
        )
        return True

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None
    ) -> list[VectorSearchResult]:
        results = self.collection.query(
            query_embeddings=cast(Any, [query_embedding]),
            n_results=top_k,
            where=filter_metadata
        )

        search_results = []
        if results['ids'] and results['distances'] and results['metadatas']:
            for i in range(len(results['ids'][0])):
                search_results.append(VectorSearchResult(
                    id=results['ids'][0][i],
                    score=1.0 - results['distances'][0][i],  # Convert distance to similarity
                    metadata=cast(dict[str, Any], results['metadatas'][0][i])
                ))

        return search_results

    async def delete(self, id: str) -> bool:
        self.collection.delete(ids=[id])
        return True

    async def update(
        self,
        id: str,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> bool:
        if embedding:
            self.collection.update(
                ids=[id],
                embeddings=cast(Any, [embedding]),
                metadatas=[metadata or {}]
            )
        elif metadata:
            self.collection.update(
                ids=[id],
                metadatas=[metadata]
            )
        return True

    async def get(self, id: str) -> VectorSearchResult | None:
        results = self.collection.get(ids=[id])

        if not results['ids']:
            return None

        metadata = results['metadatas'][0] if results['metadatas'] else {}
        return VectorSearchResult(
            id=results['ids'][0],
            score=1.0,
            metadata=cast(dict[str, Any], metadata)
        )

    async def clear(self) -> bool:
        self.client.delete_collection(self.collection.name)
        return True


class PostgreSQLVectorStore(VectorStoreProvider):
    """
    PostgreSQL vector store implementation using pgvector.

    Usage:
        store = PostgreSQLVectorStore(
            connection_string="postgresql://user:pass@localhost:5432/db",
            table_name="loom_memory"
        )
    """

    def __init__(
        self,
        connection_string: str,
        table_name: str = "loom_memory",
        vector_size: int = 1536  # OpenAI embedding size
    ):
        import importlib.util

        # Check for required dependencies
        if importlib.util.find_spec("asyncpg") is None or importlib.util.find_spec("pgvector") is None:
            raise ImportError(
                "asyncpg or pgvector not installed. "
                "Install with: pip install asyncpg pgvector"
            )

        from pgvector.asyncpg import register_vector

        self.connection_string = connection_string
        self.table_name = table_name
        self.vector_size = vector_size
        self._pool = None
        self._register_vector = register_vector

    async def _get_pool(self):
        import asyncpg
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.connection_string)
            if not self._pool:
                 raise RuntimeError("Failed to create connection pool")
            # Initialize table and extension
            async with self._pool.acquire() as conn:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                await self._register_vector(conn)

                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        text TEXT,
                        embedding vector({self.vector_size}),
                        metadata JSONB
                    )
                """)
                # Create HNSW index for faster search
                # Note: This might take time on large tables
                # We use specific name to avoid duplicate attempts errors gracefully if needed,
                # but 'IF NOT EXISTS' covers most cases.
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
                    ON {self.table_name}
                    USING hnsw (embedding vector_cosine_ops)
                """)
        return self._pool

    async def add(
        self,
        id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None
    ) -> bool:
        import json
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await self._register_vector(conn)
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} (id, text, embedding, metadata)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET
                    text = EXCLUDED.text,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
                """,
                id,
                text,
                embedding,
                json.dumps(metadata or {})
            )
        return True

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None
    ) -> list[VectorSearchResult]:
        import json
        pool = await self._get_pool()
        if not pool:
            raise RuntimeError("Failed to acquire connection pool")

        # Build filter clause
        where_clause = "1=1"
        params: list[Any] = [query_embedding]
        param_idx = 2

        if filter_metadata:
            for key, value in filter_metadata.items():
                where_clause += f" AND metadata->>'{key}' = ${param_idx}"
                params.append(str(value)) # JSONB values are often strings in simplified queries, care needed for types
                param_idx += 1

        # Use <=> operator for cosine distance (supported by pgvector)
        # We order by distance ASC (closest first)
        query = f"""
            SELECT id, text, metadata, embedding <=> $1 as distance
            FROM {self.table_name}
            WHERE {where_clause}
            ORDER BY distance ASC
            LIMIT {top_k}
        """

        async with pool.acquire() as conn:
            await self._register_vector(conn)
            rows = await conn.fetch(query, *params)

        results = []
        for row in rows:
            # Distance is 1 - CosineSimilarity usually.
            # But pgvector cosine distance is: 1 - cosine_similarity.
            # So similarity = 1 - distance.
            similarity = 1.0 - row['distance']

            metadata = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']

            results.append(VectorSearchResult(
                id=row['id'],
                score=similarity,
                metadata=metadata
            ))

        return results

    async def delete(self, id: str) -> bool:
        pool = await self._get_pool()
        if not pool:
            raise RuntimeError("Failed to acquire connection pool")
        async with pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM {self.table_name} WHERE id = $1",
                id
            )
            # execute returns string like "DELETE 1"
            return " 0" not in result

    async def update(
        self,
        id: str,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] | None = None
    ) -> bool:
        import json
        pool = await self._get_pool()
        if not pool:
            raise RuntimeError("Failed to acquire connection pool")

        if not embedding and not metadata:
            return False

        set_parts = []
        params: list[Any] = [id]
        param_idx = 2

        if embedding:
            set_parts.append(f"embedding = ${param_idx}")
            params.append(embedding)
            param_idx += 1

        if metadata:
            # We need to merge metadata, not just replace it?
            # The interface doc says "Update vector or metadata".
            # Qdrant implementation replaces metadata if provided.
            # InMemory updates/merges.
            # Let's simple Replace for now or use jsonb_concat `||` if we want merge.
            # InMemory implementation does: self._metadata[id].update(metadata), which is a merge.
            # So we should use jsonb concatenation.

            set_parts.append(f"metadata = metadata || ${param_idx}")
            params.append(json.dumps(metadata))
            param_idx += 1

        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(set_parts)}
            WHERE id = $1
        """

        async with pool.acquire() as conn:
            await self._register_vector(conn)
            result = await conn.execute(query, *params)
            return " 0" not in result

    async def get(self, id: str) -> VectorSearchResult | None:
        import json
        pool = await self._get_pool()
        if not pool:
            raise RuntimeError("Failed to acquire connection pool")
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT id, metadata FROM {self.table_name} WHERE id = $1",
                id
            )

        if not row:
            return None

        metadata = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
        return VectorSearchResult(
            id=row['id'],
            score=1.0,
            metadata=metadata
        )

    async def clear(self) -> bool:
        pool = await self._get_pool()
        if not pool:
            raise RuntimeError("Failed to acquire connection pool")
        async with pool.acquire() as conn:
            await conn.execute(f"TRUNCATE TABLE {self.table_name}")
        return True
