"""Shared fixtures for loom test suite."""

from collections.abc import AsyncGenerator

import pytest

from loom.config import AgentConfig, ClusterConfig
from loom.types import (
    AgentNode,
    CapabilityProfile,
    CompletionParams,
    CompletionResult,
    StreamChunk,
    TaskAd,
    TokenUsage,
)

# ── Mock LLM Provider ──


class MockLLMProvider:
    """Controllable mock LLM for testing."""

    def __init__(self, responses: list[str] | None = None):
        self._responses = list(responses or ["Mock response"])
        self._call_count = 0
        self.last_params: CompletionParams | None = None

    async def complete(self, params: CompletionParams) -> CompletionResult:
        self.last_params = params
        text = self._responses[min(self._call_count, len(self._responses) - 1)]
        self._call_count += 1
        return CompletionResult(
            content=text,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )

    async def stream(self, params: CompletionParams) -> AsyncGenerator[StreamChunk, None]:
        self.last_params = params
        text = self._responses[min(self._call_count, len(self._responses) - 1)]
        self._call_count += 1
        for word in text.split():
            yield StreamChunk(text=word + " ")
        yield StreamChunk(finish_reason="stop")


# ── Mock Embedding Provider ──


class MockEmbeddingProvider:
    """Returns deterministic embeddings based on text hash."""

    async def embed(self, text: str) -> list[float]:
        return self._hash_vec(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vec(t) for t in texts]

    @staticmethod
    def _hash_vec(text: str, dim: int = 8) -> list[float]:
        h = hash(text)
        return [(h >> i & 0xFF) / 255.0 for i in range(dim)]


# ── Mock Graph Store ──


class MockGraphStore:
    def __init__(self):
        self.nodes: list[dict] = []
        self.edges: list[dict] = []

    async def add_nodes(self, nodes):
        self.nodes.extend(nodes)

    async def add_edges(self, edges):
        self.edges.extend(edges)

    async def find_related(self, query, limit):
        return [
            {"id": n["id"], "content": n.get("label", ""), "score": 0.5, "metadata": {}}
            for n in self.nodes[:limit]
        ]

    async def get_neighbors(self, node_id, depth=1):
        return [e for e in self.edges if e.get("source") == node_id]


# ── Mock Entity Extractor ──


class MockEntityExtractor:
    async def extract(self, text: str) -> list[dict]:
        words = text.split()[:3]
        return [{"id": w.lower(), "name": w, "type": "concept", "relations": []} for w in words]


# ── Fixtures ──


@pytest.fixture
def mock_llm():
    return MockLLMProvider()


@pytest.fixture
def mock_llm_json():
    """LLM that returns JSON responses for planner/complexity."""
    return MockLLMProvider(
        [
            '[{"id":"a","description":"sub1","domain":"code","dependencies":[],"estimated_complexity":0.3}]'
        ]
    )


@pytest.fixture
def mock_embedder():
    return MockEmbeddingProvider()


@pytest.fixture
def mock_graph_store():
    return MockGraphStore()


@pytest.fixture
def mock_entity_extractor():
    return MockEntityExtractor()


@pytest.fixture
def agent_config():
    return AgentConfig(max_steps=3, system_prompt="Test agent")


@pytest.fixture
def cluster_config():
    return ClusterConfig(min_nodes=1, max_nodes=5, max_depth=2)


@pytest.fixture
def sample_node():
    return AgentNode(
        id="node-1",
        depth=0,
        capabilities=CapabilityProfile(scores={"code": 0.8}, tools=["search"]),
    )


@pytest.fixture
def sample_task():
    return TaskAd(domain="code", description="Write a function", estimated_complexity=0.5)
