"""
Embedding Provider Abstraction
Allows users to plug in their preferred embedding service.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import hashlib


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    Users can implement this to use their preferred embedding service.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of embeddings produced."""
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider.

    Usage:
        provider = OpenAIEmbeddingProvider(
            api_key="sk-...",
            model="text-embedding-3-small"
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        dimensions: Optional[int] = None
    ):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai not installed. "
                "Install with: pip install openai"
            )

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self._dimensions = dimensions

        # Model dimension mapping
        self._model_dims = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }

    async def embed_text(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            input=text,
            model=self.model,
            dimensions=self._dimensions
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        response = await self.client.embeddings.create(
            input=texts,
            model=self.model,
            dimensions=self._dimensions
        )
        return [item.embedding for item in response.data]

    @property
    def dimension(self) -> int:
        if self._dimensions:
            return self._dimensions
        return self._model_dims.get(self.model, 1536)


class CachedEmbeddingProvider(EmbeddingProvider):
    """
    Wrapper that adds caching to any embedding provider.
    Useful to avoid redundant API calls for the same text.

    Usage:
        base_provider = OpenAIEmbeddingProvider()
        provider = CachedEmbeddingProvider(base_provider)
    """

    def __init__(self, base_provider: EmbeddingProvider, max_cache_size: int = 10000):
        self.base_provider = base_provider
        self.max_cache_size = max_cache_size
        self._cache: dict[str, List[float]] = {}

    async def embed_text(self, text: str) -> List[float]:
        cache_key = self._get_cache_key(text)

        if cache_key in self._cache:
            return self._cache[cache_key]

        embedding = await self.base_provider.embed_text(text)

        # Add to cache with LRU eviction
        if len(self._cache) >= self.max_cache_size:
            # Remove oldest entry (simple FIFO for now)
            self._cache.pop(next(iter(self._cache)))

        self._cache[cache_key] = embedding
        return embedding

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        results = []
        uncached_texts = []
        uncached_indices = []

        # Check cache
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                results.append(self._cache[cache_key])
            else:
                results.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Fetch uncached
        if uncached_texts:
            embeddings = await self.base_provider.embed_batch(uncached_texts)

            for idx, embedding in zip(uncached_indices, embeddings):
                cache_key = self._get_cache_key(texts[idx])
                self._cache[cache_key] = embedding
                results[idx] = embedding

        return results

    @property
    def dimension(self) -> int:
        return self.base_provider.dimension

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Mock embedding provider for testing.
    Generates deterministic random embeddings based on text hash.
    """

    def __init__(self, dimension: int = 1536):
        self._dimension = dimension

    async def embed_text(self, text: str) -> List[float]:
        import random
        # Use text hash as seed for deterministic results
        seed = hash(text) % (2**32)
        random.seed(seed)
        return [random.random() for _ in range(self._dimension)]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [await self.embed_text(text) for text in texts]

    @property
    def dimension(self) -> int:
        return self._dimension
