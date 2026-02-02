"""
In-Memory Knowledge Base Unit Tests

测试内存知识库实现
"""

import pytest

from loom.providers.knowledge.base import KnowledgeItem
from loom.providers.knowledge.memory import InMemoryKnowledgeBase


class TestInMemoryKnowledgeBaseInit:
    """测试InMemoryKnowledgeBase初始化"""

    def test_init(self):
        """测试基本初始化"""
        kb = InMemoryKnowledgeBase()

        assert kb.items == {}
        assert isinstance(kb.items, dict)


class TestAddItem:
    """测试添加知识条目"""

    def test_add_item_single(self):
        """测试添加单个条目"""
        kb = InMemoryKnowledgeBase()
        item = KnowledgeItem(
            id="item-1",
            content="Test content",
            source="test",
        )

        kb.add_item(item)

        assert len(kb.items) == 1
        assert kb.items["item-1"] == item

    def test_add_item_multiple(self):
        """测试添加多个条目"""
        kb = InMemoryKnowledgeBase()
        item1 = KnowledgeItem(id="item-1", content="First", source="test")
        item2 = KnowledgeItem(id="item-2", content="Second", source="test")

        kb.add_item(item1)
        kb.add_item(item2)

        assert len(kb.items) == 2


class TestQuery:
    """测试查询功能"""

    @pytest.mark.asyncio
    async def test_query_match(self):
        """测试查询匹配"""
        kb = InMemoryKnowledgeBase()
        item1 = KnowledgeItem(id="item-1", content="Python programming", source="test")
        item2 = KnowledgeItem(id="item-2", content="Java programming", source="test")
        kb.add_item(item1)
        kb.add_item(item2)

        results = await kb.query("programming")

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_query_no_match(self):
        """测试查询无匹配"""
        kb = InMemoryKnowledgeBase()
        item = KnowledgeItem(id="item-1", content="Python programming", source="test")
        kb.add_item(item)

        results = await kb.query("javascript")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_query_with_limit(self):
        """测试带限制的查询"""
        kb = InMemoryKnowledgeBase()
        for i in range(5):
            item = KnowledgeItem(id=f"item-{i}", content=f"Test content {i}", source="test")
            kb.add_item(item)

        results = await kb.query("content", limit=2)

        assert len(results) == 2


class TestGetById:
    """测试根据ID获取"""

    @pytest.mark.asyncio
    async def test_get_by_id_exists(self):
        """测试获取存在的条目"""
        kb = InMemoryKnowledgeBase()
        item = KnowledgeItem(id="item-1", content="Test content", source="test")
        kb.add_item(item)

        result = await kb.get_by_id("item-1")

        assert result is not None
        assert result.id == "item-1"
        assert result.content == "Test content"

    @pytest.mark.asyncio
    async def test_get_by_id_not_exists(self):
        """测试获取不存在的条目"""
        kb = InMemoryKnowledgeBase()

        result = await kb.get_by_id("non-existent")

        assert result is None
