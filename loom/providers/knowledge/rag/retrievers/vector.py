"""
向量检索器
"""

from typing import Any

from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.retrievers.base import BaseRetriever
from loom.providers.knowledge.rag.stores.chunk_store import ChunkStore


class EmbeddingProvider:
    """Embedding 提供者接口（占位，实际使用框架的 EmbeddingProvider）"""

    async def embed(self, text: str) -> list[float]:
        """生成文本向量"""
        raise NotImplementedError


class VectorRetriever(BaseRetriever):
    """
    向量检索器

    基于向量相似度进行语义检索
    """

    def __init__(
        self,
        chunk_store: ChunkStore,
        embedding_provider: Any,  # EmbeddingProvider
    ):
        """
        初始化向量检索器

        Args:
            chunk_store: 文本块存储
            embedding_provider: Embedding 提供者
        """
        self.chunk_store = chunk_store
        self.embedding_provider = embedding_provider

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.0,
        **_kwargs: Any,
    ) -> list[tuple[TextChunk, float]]:
        """
        向量检索

        Args:
            query: 查询文本
            limit: 返回数量限制
            threshold: 相似度阈值

        Returns:
            [(chunk, similarity_score), ...] 按相似度降序排列
        """
        # 生成查询向量
        query_embedding = await self.embedding_provider.embed(query)

        # 向量搜索
        results = await self.chunk_store.search_by_vector(query_embedding, limit, threshold)

        return results
