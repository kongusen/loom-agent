"""
向量优先检索策略
"""

from typing import Any

from loom.providers.knowledge.rag.models.result import RetrievalResult
from loom.providers.knowledge.rag.retrievers.vector import VectorRetriever
from loom.providers.knowledge.rag.strategies.base import (
    RetrievalStrategy,
    StrategyType,
)


class VectorFirstStrategy(RetrievalStrategy):
    """
    向量优先策略

    纯向量语义检索，适用于：
    - 知识图谱不完整的场景
    - 需要快速检索的场景
    """

    def __init__(
        self,
        vector_retriever: VectorRetriever,
        threshold: float = 0.0,
    ):
        self.vector_retriever = vector_retriever
        self.threshold = threshold

    @property
    def strategy_type(self) -> StrategyType:
        return StrategyType.VECTOR_FIRST

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> RetrievalResult:
        """向量检索"""
        results = await self.vector_retriever.retrieve(
            query, limit, threshold=self.threshold
        )

        return RetrievalResult(
            chunks=[c for c, _ in results],
            scores={c.id: s for c, s in results},
        )
