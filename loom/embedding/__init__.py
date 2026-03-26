"""Embedding provider implementations."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types.embedding import EmbeddingProvider


class OpenAIEmbedding:
    """OpenAI embedding provider."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai not installed. Run: pip install openai") from None

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dims = 1536 if "small" in model else 3072

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(input=[text], model=self._model)
        return resp.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(input=texts, model=self._model)
        return [d.embedding for d in resp.data]

    @property
    def dimensions(self) -> int:
        return self._dims


class CachedEmbedding:
    """LRU cache wrapper for any embedding provider."""

    def __init__(self, provider: EmbeddingProvider, cache_size: int = 1000) -> None:
        self._provider = provider
        self._embed_cached = lru_cache(maxsize=cache_size)(self._embed_sync)

    def _embed_sync(self, text: str) -> tuple[float, ...]:
        import asyncio

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self._provider.embed(text))
        return tuple(result)

    async def embed(self, text: str) -> list[float]:
        return list(self._embed_cached(text))

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]

    @property
    def dimensions(self) -> int:
        return self._provider.dimensions


__all__ = ["OpenAIEmbedding", "CachedEmbedding"]
