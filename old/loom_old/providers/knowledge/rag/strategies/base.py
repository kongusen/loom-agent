"""
检索策略基类
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from loom.providers.knowledge.rag.models.result import RetrievalResult


class StrategyType(Enum):
    """检索策略类型"""

    GRAPH_FIRST = "graph_first"  # 图优先 + 语义排序
    VECTOR_FIRST = "vector_first"  # 向量优先
    HYBRID = "hybrid"  # 并行混合


class RetrievalStrategy(ABC):
    """
    检索策略抽象接口

    定义检索策略的通用接口
    """

    @property
    @abstractmethod
    def strategy_type(self) -> StrategyType:
        """返回策略类型"""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> RetrievalResult:
        """
        执行检索

        Args:
            query: 查询文本
            limit: 返回数量限制
            **kwargs: 额外参数

        Returns:
            检索结果
        """
        pass
