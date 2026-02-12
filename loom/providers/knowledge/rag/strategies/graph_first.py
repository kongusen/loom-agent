"""
图优先检索策略
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING, Any

from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.models.result import RetrievalResult
from loom.providers.knowledge.rag.retrievers.graph import GraphRetriever
from loom.providers.knowledge.rag.retrievers.vector import VectorRetriever
from loom.providers.knowledge.rag.strategies.base import (
    RetrievalStrategy,
    StrategyType,
)

if TYPE_CHECKING:
    from loom.observability.metrics import LoomMetrics
    from loom.observability.tracing import LoomTracer


class GraphFirstStrategy(RetrievalStrategy):
    """
    图优先策略

    核心流程：
    1. 图检索获取结构相关内容
    2. 语义排序精选结果
    3. 降级：图检索无结果时使用纯向量检索
    """

    def __init__(
        self,
        graph_retriever: GraphRetriever,
        vector_retriever: VectorRetriever,
        n_hop: int = 2,
        tracer: LoomTracer | None = None,
        metrics: LoomMetrics | None = None,
    ):
        self.graph_retriever = graph_retriever
        self.vector_retriever = vector_retriever
        self.n_hop = n_hop
        self.tracer = tracer
        self.metrics = metrics

    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.GRAPH_FIRST

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **_kwargs: Any,
    ) -> RetrievalResult:
        """图优先 + 语义排序"""
        t0 = time.monotonic()

        # 1. 图检索
        entities, relations, graph_chunks = await self.graph_retriever.retrieve(
            query, n_hop=self.n_hop, limit=limit * 2
        )
        t_graph = time.monotonic()

        if not graph_chunks:
            # 降级：纯向量检索
            vector_results = await self.vector_retriever.retrieve(query, limit)
            t_end = time.monotonic()
            self._record_metrics(
                graph_count=0, result_count=len(vector_results),
                fallback=True, total_ms=(t_end - t0) * 1000,
            )
            return RetrievalResult(
                chunks=[c for c, _ in vector_results],
                scores={c.id: s for c, s in vector_results},
            )

        # 2. 语义排序
        scored_chunks = await self._semantic_rerank(query, graph_chunks)

        # 3. 取 Top-K
        sorted_chunks = sorted(scored_chunks, key=lambda x: x[1], reverse=True)[:limit]
        t_end = time.monotonic()

        self._record_metrics(
            graph_count=len(graph_chunks), result_count=len(sorted_chunks),
            fallback=False, graph_ms=(t_graph - t0) * 1000,
            total_ms=(t_end - t0) * 1000,
        )

        return RetrievalResult(
            chunks=[c for c, _ in sorted_chunks],
            entities=entities,
            relations=relations,
            scores={c.id: s for c, s in sorted_chunks},
        )

    async def _semantic_rerank(
        self,
        query: str,
        chunks: list[TextChunk],
    ) -> list[tuple[TextChunk, float]]:
        """语义重排序"""
        query_embedding = await self.vector_retriever.embedding_provider.embed(query)

        results = []
        for chunk in chunks:
            if chunk.embedding:
                score = self._cosine_similarity(query_embedding, chunk.embedding)
            else:
                score = 0.0
            results.append((chunk, score))

        return results

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def _record_metrics(
        self,
        graph_count: int,
        result_count: int,
        fallback: bool,
        total_ms: float,
        graph_ms: float = 0.0,
    ) -> None:
        """记录检索指标到观测体系"""
        if self.tracer:
            span = self.tracer.current_span
            if span:
                span.set_attribute("retrieval.strategy", "graph_first")
                span.set_attribute("retrieval.graph_count", graph_count)
                span.set_attribute("retrieval.result_count", result_count)
                span.set_attribute("retrieval.fallback_to_vector", fallback)
                span.set_attribute("retrieval.graph_ms", round(graph_ms, 2))
                span.set_attribute("retrieval.total_ms", round(total_ms, 2))

        if self.metrics:
            from loom.observability.metrics import LoomMetrics
            self.metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL)
            self.metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, total_ms)
            self.metrics.set_gauge(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, result_count)
