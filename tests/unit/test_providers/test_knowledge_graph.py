"""
Graph Knowledge Base Unit Tests

测试图知识库实现
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.providers.knowledge.graph import GraphKnowledgeBase


class TestGraphKnowledgeBaseInit:
    """测试GraphKnowledgeBase初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        mock_service = Mock()
        kb = GraphKnowledgeBase(mock_service)

        assert kb.graph_rag == mock_service
        assert kb.search_mode == "hybrid"
        assert kb.max_hops == 2
        assert kb.vector_weight == 0.5
        assert kb.graph_weight == 0.5
        assert kb.rerank_enabled is True

    def test_init_custom(self):
        """测试自定义初始化"""
        mock_service = Mock()
        kb = GraphKnowledgeBase(
            mock_service,
            search_mode="vector",
            max_hops=3,
            vector_weight=0.7,
            graph_weight=0.3,
            rerank_enabled=False,
        )

        assert kb.search_mode == "vector"
        assert kb.max_hops == 3
        assert kb.vector_weight == 0.7
        assert kb.graph_weight == 0.3
        assert kb.rerank_enabled is False


class TestQuery:
    """测试查询功能"""

    @pytest.mark.asyncio
    async def test_query_basic(self):
        """测试基本查询"""
        mock_service = Mock()
        mock_service.search = AsyncMock(
            return_value={
                "results": [
                    {
                        "id": "item-1",
                        "content": "Test content 1",
                        "source": "graph",
                        "score": 0.9,
                    },
                    {
                        "id": "item-2",
                        "content": "Test content 2",
                        "source": "graph",
                        "score": 0.8,
                    },
                ]
            }
        )

        kb = GraphKnowledgeBase(mock_service)
        results = await kb.query("test query", limit=5)

        assert len(results) == 2
        assert results[0].id == "item-1"
        assert results[0].content == "Test content 1"
        assert results[0].relevance == 0.9
        mock_service.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_empty_results(self):
        """测试查询空结果"""
        mock_service = Mock()
        mock_service.search = AsyncMock(return_value={"results": []})

        kb = GraphKnowledgeBase(mock_service)
        results = await kb.query("test query")

        assert len(results) == 0


class TestGetById:
    """测试根据ID获取"""

    @pytest.mark.asyncio
    async def test_get_by_id_always_none(self):
        """测试get_by_id总是返回None"""
        mock_service = Mock()
        kb = GraphKnowledgeBase(mock_service)

        result = await kb.get_by_id("any-id")

        assert result is None
