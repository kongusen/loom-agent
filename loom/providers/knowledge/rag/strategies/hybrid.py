"""
混合检索策略
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

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

logger = logging.getLogger(__name__)


class HybridStrategy(RetrievalStrategy):
    """
    混合检索策略

    并行执行图检索和向量检索，向量命中后通过 chunk→entity→relation→chunk
    进行图谱扩展，三路结果加权融合。
    """

    def __init__(
        self,
        graph_retriever: GraphRetriever,
        vector_retriever: VectorRetriever,
        n_hop: int = 2,
        graph_weight: float = 0.5,
        vector_weight: float = 0.5,
        expansion_weight: float = 0.3,
        tracer: LoomTracer | None = None,
        metrics: LoomMetrics | None = None,
    ):
        self.graph_retriever = graph_retriever
        self.vector_retriever = vector_retriever
        self.n_hop = n_hop
        self.graph_weight = graph_weight
        self.vector_weight = vector_weight
        self.expansion_weight = expansion_weight
        self.tracer = tracer
        self.metrics = metrics

    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.HYBRID

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **_kwargs: Any,
    ) -> RetrievalResult:
        """混合检索：图 + 向量 + 图谱扩展"""
        t0 = time.monotonic()

        # ---- 1. 并行执行图检索和向量检索 ----
        graph_task = self.graph_retriever.retrieve(
            query, n_hop=self.n_hop, limit=limit
        )
        vector_task = self.vector_retriever.retrieve(query, limit)

        (entities, relations, graph_chunks), vector_results = await asyncio.gather(
            graph_task, vector_task
        )
        t_parallel = time.monotonic()

        # ---- 2. 图谱扩展：向量命中 chunk → entity → relation → chunk ----
        vector_chunk_ids = {c.id for c, _ in vector_results}
        graph_chunk_ids = {c.id for c in graph_chunks}
        expansion_chunks, expansion_entities = await self._expand_via_graph(
            vector_results, existing_chunk_ids=vector_chunk_ids | graph_chunk_ids,
        )
        t_expansion = time.monotonic()

        # ---- 3. 三路分数融合 ----
        scores: dict[str, float] = {}
        all_chunks_map: dict[str, Any] = {}

        # 图检索结果（位置分数）
        for i, chunk in enumerate(graph_chunks):
            base_score = 1.0 - (i / len(graph_chunks)) if graph_chunks else 0
            scores[chunk.id] = base_score * self.graph_weight
            all_chunks_map[chunk.id] = chunk

        # 向量检索结果（相似度分数）
        for chunk, score in vector_results:
            if chunk.id in scores:
                scores[chunk.id] += score * self.vector_weight
            else:
                scores[chunk.id] = score * self.vector_weight
            all_chunks_map[chunk.id] = chunk

        # 图谱扩展结果（衰减分数）
        for i, chunk in enumerate(expansion_chunks):
            exp_score = (1.0 - (i / len(expansion_chunks)) if expansion_chunks else 0) * self.expansion_weight
            if chunk.id in scores:
                scores[chunk.id] += exp_score
            else:
                scores[chunk.id] = exp_score
            all_chunks_map[chunk.id] = chunk

        # 合并扩展发现的实体
        all_entities = list({e.id: e for e in [*entities, *expansion_entities]}.values())

        # 排序取 Top-K
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        top_ids = sorted_ids[:limit]
        top_chunks = [all_chunks_map[cid] for cid in top_ids]
        t_end = time.monotonic()

        # ---- 4. 观测指标 ----
        self._record_metrics(
            graph_count=len(graph_chunks),
            vector_count=len(vector_results),
            expansion_count=len(expansion_chunks),
            result_count=len(top_chunks),
            parallel_ms=(t_parallel - t0) * 1000,
            expansion_ms=(t_expansion - t_parallel) * 1000,
            total_ms=(t_end - t0) * 1000,
        )

        return RetrievalResult(
            chunks=top_chunks,
            entities=all_entities,
            relations=relations,
            scores={cid: scores[cid] for cid in top_ids},
        )

    async def _expand_via_graph(
        self,
        vector_results: list[tuple[Any, float]],
        existing_chunk_ids: set[str],
    ) -> tuple[list[Any], list[Any]]:
        """
        图谱扩展：向量命中的 chunk → entity → relation → neighbor entity → chunk

        只扩展 vector 独有的 chunk（graph 已覆盖的不重复扩展）。
        返回 (expansion_chunks, expansion_entities)。
        """
        entity_store = self.graph_retriever.entity_store
        relation_store = self.graph_retriever.relation_store
        chunk_store = self.graph_retriever.chunk_store

        # 收集向量命中 chunk 关联的所有 entity
        seed_entity_ids: set[str] = set()
        for chunk, _ in vector_results:
            if chunk.entity_ids:
                seed_entity_ids.update(chunk.entity_ids)

        if not seed_entity_ids:
            return [], []

        # 1-hop 遍历收集邻居实体
        visited_entity_ids: set[str] = set(seed_entity_ids)
        for eid in seed_entity_ids:
            relations = await relation_store.get_by_entity(eid, direction="both")
            for rel in relations:
                visited_entity_ids.add(rel.source_id)
                visited_entity_ids.add(rel.target_id)

        # 获取所有相关实体
        all_entities = await entity_store.get_by_ids(list(visited_entity_ids))

        # 收集扩展 chunk（排除已有的）
        expansion_chunk_ids: set[str] = set()
        for entity in all_entities:
            for cid in entity.chunk_ids:
                if cid not in existing_chunk_ids:
                    expansion_chunk_ids.add(cid)

        if not expansion_chunk_ids:
            return [], all_entities

        expansion_chunks = await chunk_store.get_by_ids(list(expansion_chunk_ids))
        return expansion_chunks, all_entities

    def _record_metrics(
        self,
        graph_count: int,
        vector_count: int,
        expansion_count: int,
        result_count: int,
        parallel_ms: float,
        expansion_ms: float,
        total_ms: float,
    ) -> None:
        """记录检索指标到观测体系"""
        if self.tracer:
            span = self.tracer.current_span
            if span:
                span.set_attribute("retrieval.strategy", "hybrid")
                span.set_attribute("retrieval.graph_count", graph_count)
                span.set_attribute("retrieval.vector_count", vector_count)
                span.set_attribute("retrieval.expansion_count", expansion_count)
                span.set_attribute("retrieval.result_count", result_count)
                span.set_attribute("retrieval.parallel_ms", round(parallel_ms, 2))
                span.set_attribute("retrieval.expansion_ms", round(expansion_ms, 2))
                span.set_attribute("retrieval.total_ms", round(total_ms, 2))
                span.set_attribute("retrieval.overlap_count",
                                   graph_count + vector_count + expansion_count - result_count)

        if self.metrics:
            from loom.observability.metrics import LoomMetrics
            self.metrics.increment(LoomMetrics.KNOWLEDGE_SEARCH_TOTAL)
            self.metrics.observe(LoomMetrics.KNOWLEDGE_SEARCH_LATENCY, total_ms)
            self.metrics.set_gauge(LoomMetrics.KNOWLEDGE_RESULTS_COUNT, result_count)
            total_sources = graph_count + vector_count + expansion_count
            if total_sources > 0:
                self.metrics.set_gauge(
                    LoomMetrics.KNOWLEDGE_HIT_RATE,
                    min(1.0, result_count / total_sources),
                )
