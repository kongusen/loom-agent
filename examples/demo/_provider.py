"""Shared real provider — loads .env, creates OpenAI provider + embedder."""

import os
from pathlib import Path
from dotenv import load_dotenv
from loom.config import AgentConfig
from loom.providers.openai import OpenAIProvider

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_KEY = os.getenv("OPENAI_API_KEY")
_BASE = os.getenv("OPENAI_BASE_URL")
_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
_EMB_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def create_provider(**kwargs) -> OpenAIProvider:
    provider_keys = {"retry", "circuit_breaker"}
    provider_kw = {k: v for k, v in kwargs.items() if k in provider_keys}
    config_kw = {k: v for k, v in kwargs.items() if k not in provider_keys}
    cfg = AgentConfig(api_key=_KEY, base_url=_BASE, model=_MODEL, **config_kw)
    return OpenAIProvider(cfg, **provider_kw)


class OpenAIEmbedder:
    """Real OpenAI embedding provider."""

    def __init__(self):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=_KEY, base_url=_BASE)
        self._model = _EMB_MODEL

    async def embed(self, text: str) -> list[float]:
        r = await self._client.embeddings.create(input=[text], model=self._model)
        return r.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        r = await self._client.embeddings.create(input=texts, model=self._model)
        return [d.embedding for d in r.data]
