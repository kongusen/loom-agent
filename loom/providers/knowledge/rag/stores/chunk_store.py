"""
文本块存储接口和实现
"""

import math
from abc import abstractmethod

from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.stores.base import BaseStore


class ChunkStore(BaseStore[TextChunk]):
    """
    文本块存储接口

    除了基本的 CRUD 操作，还提供向量搜索和关键词搜索能力
    """

    @abstractmethod
    async def search_by_vector(
        self,
        embedding: list[float],
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[tuple[TextChunk, float]]:
        """
        向量相似度搜索

        Args:
            embedding: 查询向量
            limit: 返回数量限制
            threshold: 相似度阈值

        Returns:
            (chunk, score) 列表，按相似度降序排列
        """
        pass

    @abstractmethod
    async def search_by_keyword(
        self,
        keyword: str,
        limit: int = 10,
    ) -> list[TextChunk]:
        """
        关键词搜索

        Args:
            keyword: 搜索关键词
            limit: 返回数量限制

        Returns:
            匹配的文本块列表
        """
        pass

    @abstractmethod
    async def get_by_entity(self, entity_id: str) -> list[TextChunk]:
        """
        获取与实体关联的文本块

        Args:
            entity_id: 实体ID

        Returns:
            关联的文本块列表
        """
        pass


class InMemoryChunkStore(ChunkStore):
    """
    内存文本块存储实现

    适用于开发测试和小规模数据
    """

    def __init__(self):
        self._chunks: dict[str, TextChunk] = {}
        self._entity_index: dict[str, set[str]] = {}  # entity_id -> chunk_ids

    async def add(self, chunk: TextChunk) -> None:
        """添加文本块"""
        self._chunks[chunk.id] = chunk
        # 更新实体索引
        for entity_id in chunk.entity_ids:
            if entity_id not in self._entity_index:
                self._entity_index[entity_id] = set()
            self._entity_index[entity_id].add(chunk.id)

    async def add_batch(self, chunks: list[TextChunk]) -> None:
        """批量添加"""
        for chunk in chunks:
            await self.add(chunk)

    async def get(self, chunk_id: str) -> TextChunk | None:
        """根据ID获取"""
        return self._chunks.get(chunk_id)

    async def get_by_ids(self, chunk_ids: list[str]) -> list[TextChunk]:
        """批量获取"""
        return [self._chunks[cid] for cid in chunk_ids if cid in self._chunks]

    async def delete(self, chunk_id: str) -> bool:
        """删除"""
        if chunk_id in self._chunks:
            chunk = self._chunks.pop(chunk_id)
            # 清理实体索引
            for entity_id in chunk.entity_ids:
                if entity_id in self._entity_index:
                    self._entity_index[entity_id].discard(chunk_id)
            return True
        return False

    async def clear(self) -> None:
        """清空"""
        self._chunks.clear()
        self._entity_index.clear()

    async def search_by_vector(
        self,
        embedding: list[float],
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[tuple[TextChunk, float]]:
        """向量相似度搜索（余弦相似度）"""
        results = []
        for chunk in self._chunks.values():
            if chunk.embedding:
                score = self._cosine_similarity(embedding, chunk.embedding)
                if score >= threshold:
                    results.append((chunk, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    async def search_by_keyword(
        self,
        keyword: str,
        limit: int = 10,
    ) -> list[TextChunk]:
        """关键词搜索"""
        keyword_lower = keyword.lower()
        matches = []
        for chunk in self._chunks.values():
            if keyword_lower in chunk.content.lower() or any(keyword_lower in kw.lower() for kw in chunk.keywords):
                matches.append(chunk)
        return matches[:limit]

    async def get_by_entity(self, entity_id: str) -> list[TextChunk]:
        """获取与实体关联的文本块"""
        chunk_ids = self._entity_index.get(entity_id, set())
        return await self.get_by_ids(list(chunk_ids))

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)
