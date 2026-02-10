"""
混合检索策略
"""

from typing import Any

from loom.providers.knowledge.rag.models.result import RetrievalResult
from loom.providers.knowledge.rag.retrievers.graph import GraphRetriever
from loom.providers.knowledge.rag.retrievers.vector import VectorRetriever
from loom.providers.knowledge.rag.strategies.base import (
    RetrievalStrategy,
    StrategyType,
)


class HybridStrategy(RetrievalStrategy):
    """
    混合检索策略

    并行执行图检索和向量检索，融合结果
    """

    def __init__(
        self,
        graph_retriever: GraphRetriever,
        vector_retriever: VectorRetriever,
        n_hop: int = 2,
        graph_weight: float = 0.5,
        vector_weight: float = 0.5,
    ):
        self.graph_retriever = graph_retriever
        self.vector_retriever = vector_retriever
        self.n_hop = n_hop
        self.graph_weight = graph_weight
        self.vector_weight = vector_weight

    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.HYBRID

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> RetrievalResult:
        """混合检索"""
        # 并行执行两种检索
        import asyncio

        graph_task = self.graph_retriever.retrieve(
            query, n_hop=self.n_hop, limit=limit
        )
        vector_task = self.vector_retriever.retrieve(query, limit)

        (entities, relations, graph_chunks), vector_results = await asyncio.gather(
            graph_task, vector_task
        )

        # 融合分数
        scores: dict[str, float] = {}
        all_chunks_map: dict[str, Any] = {}

        # 图检索结果（基础分数）
        for i, chunk in enumerate(graph_chunks):
            base_score = 1.0 - (i / len(graph_chunks)) if graph_chunks else 0
            scores[chunk.id] = base_score * self.graph_weight
            all_chunks_map[chunk.id] = chunk

        # 向量检索结果
        for chunk, score in vector_results:
            if chunk.id in scores:
                scores[chunk.id] += score * self.vector_weight
            else:
                scores[chunk.id] = score * self.vector_weight
            all_chunks_map[chunk.id] = chunk

        # 排序取 Top-K
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        top_chunks = [all_chunks_map[cid] for cid in sorted_ids[:limit]]

        return RetrievalResult(
            chunks=top_chunks,
            entities=entities,
            relations=relations,
            scores={cid: scores[cid] for cid in sorted_ids[:limit]},
        )
