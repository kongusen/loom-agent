"""
向量存储抽象层

为不同的向量数据库后端提供统一接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np


@dataclass
class VectorSearchResult:
    """向量搜索结果"""

    id: str
    score: float
    metadata: dict[str, Any]


class VectorStoreProvider(ABC):
    """
    向量存储提供者抽象基类

    用户可以实现此接口来集成自己的向量数据库
    """

    @abstractmethod
    async def add(
        self,
        id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        添加向量到存储

        Args:
            id: 唯一标识符
            embedding: 向量嵌入
            metadata: 附加元数据

        Returns:
            成功状态
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        """
        搜索相似向量

        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量

        Returns:
            搜索结果列表（按相似度排序）
        """
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """清空所有向量"""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        删除向量

        Args:
            id: 向量ID

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def delete_by_metadata(self, filter: dict[str, Any]) -> int:
        """
        按元数据批量删除

        Args:
            filter: 过滤条件（支持 id__in / created_at__lt 等）

        Returns:
            删除数量
        """
        pass


class InMemoryVectorStore(VectorStoreProvider):
    """
    简单的内存向量存储（使用numpy）

    适用于开发和小规模部署
    """

    def __init__(self):
        self._vectors: dict[str, np.ndarray] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    async def add(
        self,
        id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """添加向量"""
        self._vectors[id] = np.array(embedding, dtype=np.float32)
        self._metadata[id] = metadata or {}
        return True

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[VectorSearchResult]:
        """搜索相似向量（余弦相似度）"""
        if not self._vectors:
            return []

        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        # 计算所有向量的余弦相似度
        similarities = []
        for id, vec in self._vectors.items():
            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0:
                continue

            # 余弦相似度
            similarity = np.dot(query_vec, vec) / (query_norm * vec_norm)
            similarities.append((id, float(similarity)))

        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        # 返回top_k结果
        results = []
        for id, score in similarities[:top_k]:
            results.append(
                VectorSearchResult(
                    id=id,
                    score=score,
                    metadata=self._metadata.get(id, {}),
                )
            )

        return results

    async def clear(self) -> bool:
        """清空所有向量"""
        self._vectors.clear()
        self._metadata.clear()
        return True

    async def delete(self, id: str) -> bool:
        """删除向量"""
        if id not in self._vectors:
            return False
        self._vectors.pop(id, None)
        self._metadata.pop(id, None)
        return True

    async def delete_by_metadata(self, filter: dict[str, Any]) -> int:
        """按元数据批量删除"""
        if not filter:
            return 0

        to_delete: list[str] = []
        for vid, meta in self._metadata.items():
            if self._match_filter(vid, meta, filter):
                to_delete.append(vid)

        for vid in to_delete:
            self._vectors.pop(vid, None)
            self._metadata.pop(vid, None)

        return len(to_delete)

    @staticmethod
    def _match_filter(vid: str, meta: dict[str, Any], filter: dict[str, Any]) -> bool:
        def _maybe_datetime(value: Any) -> Any:
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value)
                except ValueError:
                    return value
            return value

        for raw_key, expected in filter.items():
            if "__" in raw_key:
                key, op = raw_key.split("__", 1)
            else:
                key, op = raw_key, "eq"

            actual = vid if key == "id" else meta.get(key)
            if actual is None:
                return False

            if op == "in":
                if actual not in expected:
                    return False
            elif op == "contains":
                if isinstance(actual, (list, tuple, set)):
                    if expected not in actual:
                        return False
                elif isinstance(actual, str):
                    if str(expected) not in actual:
                        return False
                else:
                    return False
            elif op in ("lt", "lte", "gt", "gte"):
                left = _maybe_datetime(actual)
                right = _maybe_datetime(expected)
                if op == "lt" and not (left < right):
                    return False
                if op == "lte" and not (left <= right):
                    return False
                if op == "gt" and not (left > right):
                    return False
                if op == "gte" and not (left >= right):
                    return False
            else:
                if actual != expected:
                    return False

        return True


class EmbeddingProvider(ABC):
    """
    嵌入提供者抽象基类

    用于生成文本的向量嵌入
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """
        生成文本的向量嵌入

        Args:
            text: 输入文本

        Returns:
            向量嵌入
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        批量生成向量嵌入

        Args:
            texts: 输入文本列表

        Returns:
            向量嵌入列表
        """
        pass
