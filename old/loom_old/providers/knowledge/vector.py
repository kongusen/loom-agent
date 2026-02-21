"""
向量知识库实现

基于向量搜索的知识库，使用embedding进行语义匹配
"""

from typing import Any

from loom.memory.vector_store import EmbeddingProvider, VectorStoreProvider
from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem


class VectorKnowledgeBase(KnowledgeBaseProvider):
    """
    基于向量搜索的知识库实现

    特点：
    - 使用embedding向量进行语义搜索
    - 支持自然语言查询
    - 高召回率和相关度
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStoreProvider,
    ):
        """
        初始化向量知识库

        Args:
            embedding_provider: Embedding提供者
            vector_store: 向量存储提供者
        """
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.items: dict[str, KnowledgeItem] = {}

    async def add_item(self, item: KnowledgeItem) -> None:
        """
        添加知识条目（自动生成embedding）

        Args:
            item: 知识条目
        """
        # 生成embedding
        embedding = await self.embedding_provider.embed(item.content)

        # 存储到vector store
        await self.vector_store.add(
            id=item.id,
            embedding=embedding,
            metadata={"source": item.source},
        )

        # 保存原始数据
        self.items[item.id] = item

    async def query(
        self,
        query: str,
        limit: int = 5,
        _filters: dict[str, Any] | None = None,
    ) -> list[KnowledgeItem]:
        """
        向量语义搜索

        Args:
            query: 查询文本
            limit: 返回结果数量
            _filters: 过滤条件（暂未使用）

        Returns:
            匹配的知识条目列表（按相关度排序）
        """
        # 查询向量化
        query_embedding = await self.embedding_provider.embed(query)

        # 向量搜索
        results = await self.vector_store.search(query_embedding, top_k=limit)

        # 转换为KnowledgeItem
        knowledge_items = []
        for result in results:
            if result.id in self.items:
                item = self.items[result.id]
                item.relevance = result.score  # 设置相关度分数
                knowledge_items.append(item)

        return knowledge_items

    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None:
        """
        根据ID获取知识条目

        Args:
            knowledge_id: 知识条目ID

        Returns:
            知识条目，如果不存在则返回None
        """
        return self.items.get(knowledge_id)
