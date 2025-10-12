"""Embedding 接口定义"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class BaseEmbedding(ABC):
    """
    Embedding 基类

    文本向量化的统一接口，支持：
    - 单个文本向量化（查询）
    - 批量文本向量化（文档）
    """

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """
        对单个查询文本进行向量化

        Parameters:
            text: 查询文本

        Returns:
            向量（浮点数列表）
        """
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量向量化文档

        Parameters:
            texts: 文本列表

        Returns:
            向量列表，与输入文本列表一一对应
        """
        pass

    def get_dimension(self) -> int:
        """
        返回向量维度

        Returns:
            向量的维度（例如 384, 768, 1536）
        """
        raise NotImplementedError("Subclasses should implement get_dimension()")
