"""
Knowledge RAG Integration Tests

测试智能RAG功能：
1. KnowledgeContextSource基础功能
2. 缓存检查机制
3. 按需查询
4. Fractal Memory集成
"""

from unittest.mock import AsyncMock

import pytest

from loom.memory.knowledge_context import KnowledgeContextSource
from loom.protocol import Task


class MockKnowledgeItem:
    """模拟知识条目"""

    def __init__(self, id: str, content: str, source: str, relevance: float):
        self.id = id
        self.content = content
        self.source = source
        self.relevance = relevance


class MockKnowledgeBase:
    """模拟知识库提供者"""

    def __init__(self):
        self.query_count = 0
        self.last_query = None

    async def query(self, query: str, limit: int = 3):
        """模拟查询知识库"""
        self.query_count += 1
        self.last_query = query

        # 返回模拟的知识条目
        return [
            MockKnowledgeItem(
                id=f"knowledge_{i}",
                content=f"Knowledge about {query} - item {i}",
                source=f"source_{i}",
                relevance=0.9 - (i * 0.1),
            )
            for i in range(min(limit, 3))
        ]


class TestKnowledgeContextSourceBasic:
    """测试KnowledgeContextSource基础功能"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        kb = MockKnowledgeBase()
        source = KnowledgeContextSource(
            knowledge_base=kb,
            max_items=3,
            relevance_threshold=0.7,
        )

        assert source.knowledge_base == kb
        assert source.max_items == 3
        assert source.relevance_threshold == 0.7
        assert source._memory is None

    @pytest.mark.asyncio
    async def test_get_context_no_content(self):
        """测试没有内容的任务"""
        kb = MockKnowledgeBase()
        source = KnowledgeContextSource(knowledge_base=kb)

        task = Task(task_id="task1", action="test", parameters={})
        messages = await source.get_context(task)

        assert len(messages) == 0
        assert kb.query_count == 0

    @pytest.mark.asyncio
    async def test_get_context_with_content(self):
        """测试有内容的任务"""
        kb = MockKnowledgeBase()
        source = KnowledgeContextSource(knowledge_base=kb)

        task = Task(
            task_id="task1",
            action="test",
            parameters={"content": "Python programming"},
        )
        messages = await source.get_context(task)

        assert len(messages) == 3
        assert kb.query_count == 1
        assert kb.last_query == "Python programming"

        # 验证消息格式
        for msg in messages:
            assert msg.parameters.get("context_role") == "system"
            assert "Domain Knowledge" in msg.parameters.get("content", "")
            assert "Python programming" in msg.parameters.get("content", "")

    @pytest.mark.asyncio
    async def test_relevance_filtering(self):
        """测试相关度过滤"""
        kb = MockKnowledgeBase()
        source = KnowledgeContextSource(
            knowledge_base=kb,
            relevance_threshold=0.85,  # 高阈值
        )

        task = Task(
            task_id="task1",
            action="test",
            parameters={"content": "test query"},
        )
        messages = await source.get_context(task)

        # 只有relevance >= 0.85的知识会被包含
        # MockKnowledgeBase返回: 0.9, 0.8, 0.7
        # 只有0.9满足条件
        assert len(messages) == 1
        assert "item 0" in messages[0].parameters.get("content", "")


class TestKnowledgeContextSourceCache:
    """测试缓存机制"""

    @pytest.mark.asyncio
    async def test_cache_miss_queries_kb(self):
        """测试缓存未命中时查询知识库"""
        kb = MockKnowledgeBase()

        # 模拟 MemoryManager，返回 None（缓存未命中）
        mock_memory = AsyncMock()
        mock_memory.read = AsyncMock(return_value=None)

        source = KnowledgeContextSource(
            knowledge_base=kb,
            memory=mock_memory,
        )

        task = Task(
            task_id="task1",
            action="test",
            parameters={"content": "test query"},
        )
        messages = await source.get_context(task)

        # 应该查询了知识库
        assert kb.query_count == 1
        assert len(messages) == 3

        # 应该尝试从缓存读取
        assert mock_memory.read.called

        # 应该写入缓存
        assert mock_memory.write.called

    @pytest.mark.asyncio
    async def test_cache_hit_skips_kb(self):
        """测试缓存命中时跳过知识库查询"""
        kb = MockKnowledgeBase()

        # 模拟 MemoryManager.read 返回 MemoryEntry 形态（带 .content）
        import json

        cached_data = json.dumps(
            [
                {
                    "id": "cached_1",
                    "content": "Cached knowledge",
                    "source": "cache",
                    "relevance": 0.95,
                }
            ]
        )
        mock_entry = type("MemoryEntry", (), {"content": cached_data})()

        mock_memory = AsyncMock()
        mock_memory.read = AsyncMock(return_value=mock_entry)

        source = KnowledgeContextSource(
            knowledge_base=kb,
            memory=mock_memory,
        )

        task = Task(
            task_id="task1",
            action="test",
            parameters={"content": "test query"},
        )
        messages = await source.get_context(task)

        # 不应该查询知识库
        assert kb.query_count == 0

        # 应该返回缓存的知识
        assert len(messages) == 1
        assert "Cached Knowledge" in messages[0].parameters.get("content", "")
        assert "Cached" in messages[0].parameters.get("content", "")


class TestKnowledgeContextSourceConfiguration:
    """测试配置可配置性"""

    @pytest.mark.asyncio
    async def test_custom_max_items(self):
        """测试自定义max_items配置"""
        kb = MockKnowledgeBase()
        source = KnowledgeContextSource(
            knowledge_base=kb,
            max_items=5,  # 自定义值
        )

        task = Task(
            task_id="task1",
            action="test",
            parameters={"content": "test query"},
        )
        messages = await source.get_context(task)

        # 应该返回5个条目（MockKnowledgeBase最多返回3个，所以实际是3个）
        assert len(messages) == 3
        assert source.max_items == 5

    @pytest.mark.asyncio
    async def test_custom_relevance_threshold(self):
        """测试自定义relevance_threshold配置"""
        kb = MockKnowledgeBase()
        source = KnowledgeContextSource(
            knowledge_base=kb,
            relevance_threshold=0.95,  # 非常高的阈值
        )

        task = Task(
            task_id="task1",
            action="test",
            parameters={"content": "test query"},
        )
        messages = await source.get_context(task)

        # MockKnowledgeBase返回: 0.9, 0.8, 0.7
        # 没有任何条目满足0.95的阈值
        assert len(messages) == 0
        assert source.relevance_threshold == 0.95
