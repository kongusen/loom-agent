"""
Knowledge Configuration Unit Tests

测试知识库配置和接口
"""

import pytest

from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem


class TestKnowledgeItem:
    """测试KnowledgeItem数据类"""

    def test_knowledge_item_init_minimal(self):
        """测试最小化初始化"""
        item = KnowledgeItem(
            id="item-1",
            content="Test content",
            source="test",
        )

        assert item.id == "item-1"
        assert item.content == "Test content"
        assert item.source == "test"
        assert item.relevance == 0.0
        assert item.metadata == {}

    def test_knowledge_item_init_full(self):
        """测试完整初始化"""
        item = KnowledgeItem(
            id="item-1",
            content="Test content",
            source="test",
            relevance=0.95,
            metadata={"author": "test", "date": "2024-01-01"},
        )

        assert item.relevance == 0.95
        assert item.metadata["author"] == "test"
        assert item.metadata["date"] == "2024-01-01"


class MockKnowledgeBaseProvider(KnowledgeBaseProvider):
    """测试用的具体实现"""

    def __init__(self):
        self.items = {
            "item-1": KnowledgeItem(
                id="item-1",
                content="First item",
                source="test",
                relevance=0.9,
            ),
            "item-2": KnowledgeItem(
                id="item-2",
                content="Second item",
                source="test",
                relevance=0.8,
            ),
        }

    async def query(
        self,
        query: str,
        limit: int = 5,
        filters: dict | None = None,
    ) -> list[KnowledgeItem]:
        """查询知识库"""
        results = list(self.items.values())
        # 按相关度排序
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:limit]

    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None:
        """根据ID获取知识条目"""
        return self.items.get(knowledge_id)


class TestKnowledgeBaseProvider:
    """测试KnowledgeBaseProvider抽象基类"""

    @pytest.mark.asyncio
    async def test_query_basic(self):
        """测试基本查询"""
        provider = MockKnowledgeBaseProvider()
        results = await provider.query("test query")

        assert len(results) == 2
        # 应该按相关度排序
        assert results[0].relevance == 0.9
        assert results[1].relevance == 0.8

    @pytest.mark.asyncio
    async def test_query_with_limit(self):
        """测试带限制的查询"""
        provider = MockKnowledgeBaseProvider()
        results = await provider.query("test query", limit=1)

        assert len(results) == 1
        assert results[0].id == "item-1"

    @pytest.mark.asyncio
    async def test_get_by_id_exists(self):
        """测试获取存在的知识条目"""
        provider = MockKnowledgeBaseProvider()
        item = await provider.get_by_id("item-1")

        assert item is not None
        assert item.id == "item-1"
        assert item.content == "First item"

    @pytest.mark.asyncio
    async def test_get_by_id_not_exists(self):
        """测试获取不存在的知识条目"""
        provider = MockKnowledgeBaseProvider()
        item = await provider.get_by_id("non-existent")

        assert item is None
