"""
关键词检索器
"""

from typing import Any

from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.retrievers.base import BaseRetriever
from loom.providers.knowledge.rag.stores.chunk_store import ChunkStore


class KeywordRetriever(BaseRetriever):
    """
    关键词检索器

    基于关键词匹配进行检索
    """

    def __init__(self, chunk_store: ChunkStore):
        self.chunk_store = chunk_store

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[TextChunk]:
        """
        关键词检索

        Args:
            query: 查询文本
            limit: 返回数量限制

        Returns:
            匹配的文本块列表
        """
        return await self.chunk_store.search_by_keyword(query, limit)
