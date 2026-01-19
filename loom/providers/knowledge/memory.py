"""
内存知识库实现

简单的内存知识库，使用关键词匹配
"""

from typing import Any

from loom.config.knowledge import KnowledgeBaseProvider, KnowledgeItem


class InMemoryKnowledgeBase(KnowledgeBaseProvider):
    """
    简单的内存知识库实现

    特点：
    - 使用关键词匹配
    - 数据存储在内存中
    - 适合开发和小规模部署
    """

    def __init__(self):
        self.items: dict[str, KnowledgeItem] = {}

    def add_item(self, item: KnowledgeItem) -> None:
        """
        添加知识条目

        Args:
            item: 知识条目
        """
        self.items[item.id] = item

    async def query(
        self,
        query: str,
        limit: int = 5,
        _filters: dict[str, Any] | None = None,
    ) -> list[KnowledgeItem]:
        """
        简单的关键词匹配查询

        Args:
            query: 查询文本
            limit: 返回结果数量
            _filters: 过滤条件（暂未使用）

        Returns:
            匹配的知识条目列表
        """
        query_lower = query.lower()
        matches = []

        for item in self.items.values():
            if query_lower in item.content.lower():
                matches.append(item)

        # 按匹配次数排序（简单的相关度计算）
        matches.sort(key=lambda x: x.content.lower().count(query_lower), reverse=True)

        return matches[:limit]

    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None:
        """
        根据ID获取知识条目

        Args:
            knowledge_id: 知识条目ID

        Returns:
            知识条目，如果不存在则返回None
        """
        return self.items.get(knowledge_id)
