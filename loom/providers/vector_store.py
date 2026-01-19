"""
Vector Store Provider - 向量存储提供者

定义向量数据库的统一接口。

设计原则：
1. 存储无关 - 支持多种向量数据库
2. 高效检索 - 支持相似度搜索
3. 批量操作 - 支持批量存储和检索
"""

from typing import Any

from loom.providers.base import Provider


class VectorStoreProvider(Provider):
    """
    向量存储提供者抽象类

    定义向量数据库的统一接口。
    """

    async def store(
        self, id: str, vector: list[float], metadata: dict[str, Any] | None = None
    ) -> bool:
        """
        存储向量

        Args:
            id: 向量ID
            vector: 向量数据
            metadata: 元数据

        Returns:
            是否成功
        """
        raise NotImplementedError

    async def search(
        self, query_vector: list[float], top_k: int = 10, filter: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        相似度搜索

        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            filter: 过滤条件

        Returns:
            搜索结果列表
        """
        raise NotImplementedError

    async def delete(self, id: str) -> bool:
        """
        删除向量

        Args:
            id: 向量ID

        Returns:
            是否成功
        """
        raise NotImplementedError
