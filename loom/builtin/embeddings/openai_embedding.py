"""
OpenAI Embedding - Text embedding using OpenAI API

Supports OpenAI's embedding models for semantic search.
"""

from __future__ import annotations

from typing import List, Optional
import os
import logging

from loom.interfaces.embedding import BaseEmbedding


logger = logging.getLogger(__name__)


class OpenAIEmbedding:
    """
    OpenAI Embedding API wrapper.

    Supports OpenAI embedding models:
    - text-embedding-3-small (1536 dim, fast, affordable)
    - text-embedding-3-large (3072 dim, best quality)
    - text-embedding-ada-002 (1536 dim, legacy)

    Example:
        ```python
        from loom.builtin.embeddings import OpenAIEmbedding

        # Initialize
        embedding = OpenAIEmbedding(
            api_key="sk-...",  # or set OPENAI_API_KEY env var
            model="text-embedding-3-small"
        )

        # Embed single query
        query_vec = await embedding.embed_query("What is machine learning?")
        print(f"Dimension: {len(query_vec)}")

        # Batch embed documents
        docs = ["Doc 1", "Doc 2", "Doc 3"]
        doc_vecs = await embedding.embed_documents(docs)
        print(f"Embedded {len(doc_vecs)} documents")
        ```

    Performance:
    - text-embedding-3-small: ~3000 tokens/sec, $0.02/1M tokens
    - text-embedding-3-large: ~3000 tokens/sec, $0.13/1M tokens

    Dimension Control:
    You can reduce dimensions for smaller embeddings (only for v3 models):
        embedding = OpenAIEmbedding(model="text-embedding-3-small", dimension=512)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        dimension: Optional[int] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize OpenAI embedding client.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Embedding model name
                   - "text-embedding-3-small" (recommended, 1536 dim)
                   - "text-embedding-3-large" (best quality, 3072 dim)
                   - "text-embedding-ada-002" (legacy, 1536 dim)
            dimension: Optional dimension reduction (v3 models only)
                      Reduces output dimension while preserving quality
            timeout: Request timeout in seconds

        Raises:
            ImportError: If openai package is not installed
            ValueError: If API key is not provided
        """
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError:
            raise ImportError(
                "OpenAI package is required for OpenAIEmbedding. "
                "Install it with: pip install openai"
            )

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. "
                "Provide it via api_key parameter or OPENAI_API_KEY env var"
            )

        self.model = model
        self._dimension = dimension
        self.timeout = timeout

        # Initialize async client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=timeout,
        )

        logger.info(
            f"[OpenAIEmbedding] Initialized with model={model}, "
            f"dimension={self._dimension or self.get_dimension()}"
        )

    async def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query text.

        Args:
            text: Query text to embed

        Returns:
            List[float]: Embedding vector

        Example:
            ```python
            embedding = OpenAIEmbedding()
            vec = await embedding.embed_query("machine learning")
            print(f"Vector length: {len(vec)}")
            ```
        """
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
            dimensions=self._dimension,
        )

        return response.data[0].embedding

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Batch embed multiple documents.

        More efficient than calling embed_query() multiple times.

        Args:
            texts: List of texts to embed

        Returns:
            List[List[float]]: List of embedding vectors

        Example:
            ```python
            embedding = OpenAIEmbedding()
            docs = ["Doc 1", "Doc 2", "Doc 3"]
            vecs = await embedding.embed_documents(docs)
            print(f"Embedded {len(vecs)} documents")
            ```

        Note:
            OpenAI API has a maximum batch size. For large datasets,
            consider chunking the input.
        """
        if not texts:
            return []

        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            dimensions=self._dimension,
        )

        return [item.embedding for item in response.data]

    def get_dimension(self) -> int:
        """
        Get embedding dimension.

        Returns:
            int: Vector dimension

        Example:
            ```python
            embedding = OpenAIEmbedding(model="text-embedding-3-small")
            print(f"Dimension: {embedding.get_dimension()}")  # 1536
            ```
        """
        if self._dimension:
            return self._dimension

        # Default dimensions by model
        default_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

        return default_dimensions.get(self.model, 1536)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"OpenAIEmbedding(model={self.model}, "
            f"dimension={self.get_dimension()})"
        )
