"""向量存储接口定义"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from loom.interfaces.retriever import Document


class BaseVectorStore(ABC):
    """
    向量存储基类

    向量数据库的统一接口，支持：
    - 向量的添加和删除
    - 基于向量的相似度搜索
    - 元数据过滤
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化向量存储连接

        用于建立数据库连接、创建集合/索引等初始化操作
        """
        pass

    @abstractmethod
    async def add_vectors(
        self,
        vectors: List[List[float]],
        documents: List[Document]
    ) -> None:
        """
        添加向量到存储

        Parameters:
            vectors: 向量列表，每个向量是一个浮点数列表
            documents: 对应的文档列表，与 vectors 一一对应
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        搜索相似向量

        Parameters:
            query_vector: 查询向量
            top_k: 返回结果数量
            filters: 可选的元数据过滤条件

        Returns:
            [(Document, score), ...] 列表，按相似度分数降序排列
        """
        pass

    async def delete(self, doc_ids: List[str]) -> None:
        """
        删除指定文档

        Parameters:
            doc_ids: 要删除的文档 ID 列表
        """
        pass

    async def clear(self) -> None:
        """清空所有向量"""
        pass

    async def close(self) -> None:
        """关闭连接，释放资源"""
        pass
