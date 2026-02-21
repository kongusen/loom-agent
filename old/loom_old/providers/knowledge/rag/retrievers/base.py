"""
检索器基类
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseRetriever(ABC):
    """
    检索器抽象基类

    定义检索器的通用接口
    """

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> Any:
        """
        执行检索

        Args:
            query: 查询文本
            limit: 返回数量限制
            **kwargs: 额外参数

        Returns:
            检索结果（具体类型由子类定义）
        """
        pass
