"""
Vector Knowledge Base Unit Tests

测试向量知识库实现
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.providers.knowledge.base import KnowledgeItem
from loom.providers.knowledge.vector import VectorKnowledgeBase


class TestVectorKnowledgeBaseInit:
    """测试VectorKnowledgeBase初始化"""

    def test_init(self):
        """测试基本初始化"""
        mock_embedding = Mock()
        mock_vector_store = Mock()

        kb = VectorKnowledgeBase(mock_embedding, mock_vector_store)

        assert kb.embedding_provider == mock_embedding
        assert kb.vector_store == mock_vector_store
        assert kb.items == {}


class TestAddItem:
    """测试添加知识条目"""

    @pytest.mark.asyncio
    async def test_add_item(self):
        """测试添加单个条目"""
        mock_embedding = Mock()
        mock_embedding.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_vector_store = Mock()
        mock_vector_store.add = AsyncMock()

        kb = VectorKnowledgeBase(mock_embedding, mock_vector_store)
        item = KnowledgeItem(
            id="item-1",
            content="Test content",
            source="test",
        )

        await kb.add_item(item)

        assert len(kb.items) == 1
        assert kb.items["item-1"] == item
        mock_embedding.embed.assert_called_once_with("Test content")
        mock_vector_store.add.assert_called_once()


class TestQuery:
    """测试查询功能"""

    @pytest.mark.asyncio
    async def test_query_with_results(self):
        """测试查询有结果"""
        mock_embedding = Mock()
        mock_embedding.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

        # Mock搜索结果
        mock_result = Mock()
        mock_result.id = "item-1"
        mock_result.score = 0.95

        mock_vector_store = Mock()
        mock_vector_store.search = AsyncMock(return_value=[mock_result])

        kb = VectorKnowledgeBase(mock_embedding, mock_vector_store)

        # 添加一个条目
        item = KnowledgeItem(id="item-1", content="Test content", source="test")
        kb.items["item-1"] = item

        results = await kb.query("test query", limit=5)

        assert len(results) == 1
        assert results[0].id == "item-1"
        assert results[0].relevance == 0.95
        mock_embedding.embed.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_query_empty_results(self):
        """测试查询空结果"""
        mock_embedding = Mock()
        mock_embedding.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_vector_store = Mock()
        mock_vector_store.search = AsyncMock(return_value=[])

        kb = VectorKnowledgeBase(mock_embedding, mock_vector_store)
        results = await kb.query("test query")

        assert len(results) == 0


class TestGetById:
    """测试根据ID获取"""

    @pytest.mark.asyncio
    async def test_get_by_id_exists(self):
        """测试获取存在的条目"""
        mock_embedding = Mock()
        mock_vector_store = Mock()
        kb = VectorKnowledgeBase(mock_embedding, mock_vector_store)

        item = KnowledgeItem(id="item-1", content="Test content", source="test")
        kb.items["item-1"] = item

        result = await kb.get_by_id("item-1")

        assert result is not None
        assert result.id == "item-1"

    @pytest.mark.asyncio
    async def test_get_by_id_not_exists(self):
        """测试获取不存在的条目"""
        mock_embedding = Mock()
        mock_vector_store = Mock()
        kb = VectorKnowledgeBase(mock_embedding, mock_vector_store)

        result = await kb.get_by_id("non-existent")

        assert result is None
