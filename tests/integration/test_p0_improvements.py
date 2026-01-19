"""
P0改进功能测试 - 事实提取和L4语义检索

验证优化分析文档中的P0改进：
1. 事实提取机制
2. L4语义检索集成
"""

import pytest

from loom.memory import LoomMemory
from loom.memory.types import Fact, FactType, MemoryTier
from loom.protocol import Task, TaskStatus


class TestFactExtraction:
    """测试事实提取功能"""

    @pytest.mark.asyncio
    async def test_extract_api_facts(self):
        """测试API事实提取"""
        memory = LoomMemory(node_id="test_node")

        # 创建API调用Task
        task = Task(action="api_call", parameters={"endpoint": "/users", "method": "GET"})
        task.status = TaskStatus.COMPLETED

        # 提取事实
        facts = await memory.fact_extractor.extract_facts(task)

        # 验证提取结果
        assert len(facts) > 0
        api_fact = facts[0]
        assert api_fact.fact_type == FactType.API_SCHEMA
        assert "/users" in api_fact.content
        assert "GET" in api_fact.content

    @pytest.mark.asyncio
    async def test_extract_error_facts(self):
        """测试错误事实提取"""
        memory = LoomMemory(node_id="test_node")

        # 创建失败的Task
        task = Task(action="test_action", parameters={})
        task.status = TaskStatus.FAILED
        task.error = "Connection timeout"

        # 提取事实
        facts = await memory.fact_extractor.extract_facts(task)

        # 验证提取结果
        assert len(facts) > 0
        error_fact = facts[0]
        assert error_fact.fact_type == FactType.ERROR_PATTERN
        assert "test_action" in error_fact.content
        assert "Connection timeout" in error_fact.content

    @pytest.mark.asyncio
    async def test_extract_tool_facts(self):
        """测试工具使用事实提取"""
        memory = LoomMemory(node_id="test_node")

        # 创建工具调用Task
        task = Task(action="tool_call", parameters={"tool": "calculator"})
        task.result = {"output": 42}
        task.status = TaskStatus.COMPLETED

        # 提取事实
        facts = await memory.fact_extractor.extract_facts(task)

        # 验证提取结果
        assert len(facts) > 0
        tool_fact = facts[0]
        assert tool_fact.fact_type == FactType.TOOL_USAGE
        assert "calculator" in tool_fact.content


class TestFactStorage:
    """测试事实存储功能"""

    def test_fact_index(self):
        """测试Fact索引"""
        memory = LoomMemory(node_id="test_node")

        # 创建并存储Fact
        fact = Fact(
            fact_id="test_fact_1",
            content="Test fact content",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            confidence=0.9,
            tags=["test"],
        )
        memory._fact_index[fact.fact_id] = fact

        # 验证存储
        assert "test_fact_1" in memory._fact_index
        retrieved = memory._fact_index["test_fact_1"]
        assert retrieved.content == "Test fact content"
        assert retrieved.confidence == 0.9

    def test_fact_access_tracking(self):
        """测试Fact访问追踪"""
        fact = Fact(
            fact_id="test_fact_2",
            content="Another fact",
            fact_type=FactType.BEST_PRACTICE,
            tags=["practice"],
        )

        # 初始访问次数为0
        assert fact.access_count == 0

        # 更新访问
        fact.update_access()
        assert fact.access_count == 1

        # 再次更新
        fact.update_access()
        assert fact.access_count == 2


class TestFactSearch:
    """测试事实检索功能"""

    def test_simple_search_facts(self):
        """测试简单文本搜索事实"""
        memory = LoomMemory(node_id="test_node", enable_l4_vectorization=False)

        # 添加多个Fact
        fact1 = Fact(
            fact_id="fact_1",
            content="Python is a programming language",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            tags=["python", "programming"],
        )
        fact2 = Fact(
            fact_id="fact_2",
            content="JavaScript is used for web development",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            tags=["javascript", "web"],
        )
        fact3 = Fact(
            fact_id="fact_3",
            content="Python is great for data science",
            fact_type=FactType.BEST_PRACTICE,
            tags=["python", "data"],
        )

        memory._fact_index[fact1.fact_id] = fact1
        memory._fact_index[fact2.fact_id] = fact2
        memory._fact_index[fact3.fact_id] = fact3

        # 搜索包含"python"的事实
        results = memory._simple_search_facts("python", limit=5)

        # 验证结果
        assert len(results) == 2
        assert all(
            "python" in r.content.lower() or "python" in [t.lower() for t in r.tags]
            for r in results
        )

    def test_simple_search_facts_by_tags(self):
        """测试通过标签搜索事实"""
        memory = LoomMemory(node_id="test_node", enable_l4_vectorization=False)

        # 添加Fact
        fact = Fact(
            fact_id="fact_api",
            content="API endpoint definition",
            fact_type=FactType.API_SCHEMA,
            tags=["api", "rest", "endpoint"],
        )
        memory._fact_index[fact.fact_id] = fact

        # 通过标签搜索
        results = memory._simple_search_facts("rest", limit=5)

        # 验证结果
        assert len(results) == 1
        assert results[0].fact_id == "fact_api"


class TestAsyncCompression:
    """测试异步压缩功能"""

    @pytest.mark.asyncio
    async def test_promote_tasks_async(self):
        """测试异步压缩方法"""
        memory = LoomMemory(node_id="test_node", max_l1_size=5, max_l2_size=3)

        # 添加多个重要Task到L1
        for i in range(5):
            task = Task(action=f"action_{i}", parameters={"index": i})
            task.metadata["importance"] = 0.7  # 超过0.6阈值
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 触发异步压缩
        await memory.promote_tasks_async()

        # 验证L1→L2提升
        l2_tasks = memory.get_l2_tasks()
        assert len(l2_tasks) > 0  # 应该有Task被提升到L2

    @pytest.mark.asyncio
    async def test_promote_l3_to_l4_without_vectorization(self):
        """测试L3→L4压缩（无向量化）"""
        memory = LoomMemory(node_id="test_node", enable_l4_vectorization=False)

        # 添加摘要到L3
        from datetime import datetime

        from loom.memory.types import TaskSummary

        for i in range(10):
            summary = TaskSummary(
                task_id=f"task_{i}",
                action=f"action_{i}",
                param_summary="params",
                result_summary="results",
                importance=0.5,
                created_at=datetime.now(),
            )
            memory._l3_summaries.append(summary)

        # 触发L3→L4压缩（应该跳过，因为没有向量化）
        await memory._promote_l3_to_l4()

        # 验证L3没有被清空（因为没有向量化）
        assert len(memory._l3_summaries) == 10
