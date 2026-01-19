"""
向量存储抽象层

为不同的向量数据库后端提供统一接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
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
