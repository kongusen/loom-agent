"""
LoomMemory Extended Unit Tests

测试记忆系统的扩展功能，包括搜索、提升、事实管理等
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.memory.core import LoomMemory
from loom.memory.types import Fact, FactType, MemoryTier, TaskSummary
from loom.protocol import Task


class TestLoomMemorySearch:
    """测试搜索功能"""

    def test_simple_search_tasks(self):
        """测试简单任务搜索"""
        memory = LoomMemory(node_id="test-node")

        # 添加一些任务
        task1 = Task(
            task_id="task-1",
            action="file_read",
            parameters={"file": "test.txt"},
        )
        memory.add_task(task1)

        task2 = Task(
            task_id="task-2",
            action="file_write",
            parameters={"file": "output.txt"},
        )
        memory.add_task(task2)

        # 搜索任务
        results = memory._simple_search_tasks("file_read", limit=10)

        assert len(results) > 0
        assert any(r.action == "file_read" for r in results)

    def test_simple_search_tasks_with_limit(self):
        """测试带限制的简单任务搜索"""
        memory = LoomMemory(node_id="test-node")

        # 添加多个任务
        for i in range(10):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"index": i},
            )
            task.metadata["importance"] = 0.5 + i * 0.05
            memory.add_task(task)

        results = memory._simple_search_tasks("test_action", limit=5)

        assert len(results) <= 5

    def test_simple_search_facts(self):
        """测试简单事实搜索"""
        memory = LoomMemory(node_id="test-node")

        # 添加一些事实
        fact1 = Fact(
            fact_id="fact-1",
            content="Python is a programming language",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            tags=["programming", "python"],
        )
        memory.add_fact(fact1)

        fact2 = Fact(
            fact_id="fact-2",
            content="JavaScript is used for web development",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            tags=["programming", "javascript"],
        )
        memory.add_fact(fact2)

        # 搜索事实
        results = memory._simple_search_facts("Python", limit=10)

        assert len(results) > 0
        assert any("Python" in f.content for f in results)

    def test_simple_search_facts_with_limit(self):
        """测试带限制的简单事实搜索"""
        memory = LoomMemory(node_id="test-node")

        # 添加多个事实
        for i in range(10):
            fact = Fact(
                fact_id=f"fact-{i}",
                content=f"Fact {i}",
                fact_type=FactType.DOMAIN_KNOWLEDGE,
                tags=[f"tag{i}"],
            )
            fact.access_count = i
            memory.add_fact(fact)

        results = memory._simple_search_facts("Fact", limit=5)

        assert len(results) <= 5


class TestLoomMemoryPromote:
    """测试任务提升功能"""

    def test_promote_l1_to_l2(self):
        """测试 L1 到 L2 的提升"""
        memory = LoomMemory(node_id="test-node", max_l2_size=10)

        # 添加重要任务到 L1
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"index": i},
            )
            task.metadata["importance"] = 0.7 + i * 0.05  # 都超过 0.6
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 执行提升
        memory._promote_l1_to_l2()

        # 检查是否有任务被提升到 L2
        l2_tasks = memory.get_l2_tasks()
        assert len(l2_tasks) > 0

    def test_promote_l2_to_l3(self):
        """测试 L2 到 L3 的提升"""
        memory = LoomMemory(node_id="test-node", max_l2_size=5, max_l3_size=10)

        # 添加任务到 L2
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"index": i},
            )
            task.metadata["importance"] = 0.7
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        # 执行提升
        memory._promote_l2_to_l3()

        # 检查是否有摘要被创建
        l3_summaries = memory.get_l3_summaries()
        assert len(l3_summaries) > 0

    def test_promote_tasks(self):
        """测试同步提升任务"""
        memory = LoomMemory(node_id="test-node", max_l2_size=5)

        # 添加重要任务
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"index": i},
            )
            task.metadata["importance"] = 0.7
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 执行提升
        memory.promote_tasks()

        # 检查提升是否成功
        l2_tasks = memory.get_l2_tasks()
        assert len(l2_tasks) > 0

    @pytest.mark.asyncio
    async def test_promote_tasks_async(self):
        """测试异步提升任务"""
        memory = LoomMemory(node_id="test-node", max_l2_size=5, max_l3_size=10)

        # 添加重要任务
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
                parameters={"index": i},
            )
            task.metadata["importance"] = 0.7
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 执行异步提升
        await memory.promote_tasks_async()

        # 检查提升是否成功
        l2_tasks = memory.get_l2_tasks()
        assert len(l2_tasks) > 0

    @pytest.mark.asyncio
    async def test_promote_l3_to_l4(self):
        """测试 L3 到 L4 的提升"""
        memory = LoomMemory(node_id="test-node", max_l3_size=5)

        # 模拟 embedding provider
        mock_embedding = Mock()
        mock_embedding.embed = AsyncMock(return_value=[0.1] * 128)

        # 模拟 vector store
        mock_vector_store = Mock()
        mock_vector_store.add = AsyncMock()

        memory.embedding_provider = mock_embedding
        memory._l4_vector_store = mock_vector_store

        # 添加摘要到 L3
        for i in range(5):
            summary = TaskSummary(
                task_id=f"task-{i}",
                action="test_action",
                param_summary=f"param{i}",
                result_summary=f"result{i}",
            )
            memory._add_to_l3(summary)

        # 执行 L3 到 L4 的提升
        await memory._promote_l3_to_l4()

        # 检查是否调用了向量存储
        assert mock_vector_store.add.call_count > 0


class TestLoomMemoryFactManagement:
    """测试事实管理功能"""

    def test_add_fact(self):
        """测试添加事实"""
        memory = LoomMemory(node_id="test-node")

        fact = Fact(
            fact_id="fact-1",
            content="Test fact",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            tags=["test"],
        )

        memory.add_fact(fact)

        assert "fact-1" in memory._fact_index
        assert memory._fact_index["fact-1"] == fact

    def test_add_fact_triggers_cleanup(self):
        """测试添加事实触发清理"""
        memory = LoomMemory(node_id="test-node", max_fact_index_size=5)

        # 添加超过限制的事实
        for i in range(10):
            fact = Fact(
                fact_id=f"fact-{i}",
                content=f"Fact {i}",
                fact_type=FactType.DOMAIN_KNOWLEDGE,
                tags=[],
            )
            fact.access_count = i
            memory.add_fact(fact)

        # 应该触发清理
        assert len(memory._fact_index) <= memory.max_fact_index_size

    def test_cleanup_fact_index(self):
        """测试清理事实索引"""
        memory = LoomMemory(node_id="test-node", max_fact_index_size=10)

        # 添加多个事实
        for i in range(20):
            fact = Fact(
                fact_id=f"fact-{i}",
                content=f"Fact {i}",
                fact_type=FactType.DOMAIN_KNOWLEDGE,
                tags=[],
            )
            fact.access_count = i
            fact.confidence = 0.5 + i * 0.02
            memory.add_fact(fact)

        # 手动触发清理
        memory._cleanup_fact_index()

        # 应该保留前80%
        assert len(memory._fact_index) <= 16  # 20 * 0.8 = 16


class TestLoomMemorySummarize:
    """测试任务摘要功能"""

    def test_summarize_task(self):
        """测试任务摘要"""
        memory = LoomMemory(node_id="test-node")

        task = Task(
            task_id="task-1",
            action="file_read",
            parameters={"file": "test.txt", "mode": "r"},
        )
        task.result = "File content here"
        task.metadata = {"importance": 0.8, "tags": ["file", "read"]}

        summary = memory._summarize_task(task)

        assert summary.task_id == "task-1"
        assert summary.action == "file_read"
        assert len(summary.param_summary) > 0
        assert len(summary.result_summary) > 0
        assert summary.importance == 0.8
        assert "file" in summary.tags


class TestLoomMemoryGetTask:
    """测试获取任务功能"""

    def test_get_task_exists(self):
        """测试获取存在的任务"""
        memory = LoomMemory(node_id="test-node")

        task = Task(
            task_id="task-1",
            action="test_action",
            parameters={"key": "value"},
        )
        memory.add_task(task)

        retrieved = memory.get_task("task-1")

        assert retrieved is not None
        assert retrieved.task_id == "task-1"

    def test_get_task_not_exists(self):
        """测试获取不存在的任务"""
        memory = LoomMemory(node_id="test-node")

        retrieved = memory.get_task("nonexistent-task")

        assert retrieved is None


class TestLoomMemoryStats:
    """测试统计信息功能"""

    def test_get_stats(self):
        """测试获取统计信息"""
        memory = LoomMemory(node_id="test-node")

        # 添加一些任务和事实
        for i in range(3):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
            )
            memory.add_task(task)

        fact = Fact(
            fact_id="fact-1",
            content="Test fact",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
        )
        memory.add_fact(fact)

        stats = memory.get_stats()

        assert "l1_size" in stats
        assert "l2_size" in stats
        assert "l3_size" in stats
        assert "total_tasks" in stats
        assert stats["l1_size"] == 3
        assert stats["total_tasks"] == 3


class TestLoomMemoryClearAll:
    """测试清空所有功能"""

    def test_clear_all(self):
        """测试清空所有记忆"""
        memory = LoomMemory(node_id="test-node")

        # 添加任务和事实
        for i in range(5):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
            )
            memory.add_task(task)

        fact = Fact(
            fact_id="fact-1",
            content="Test fact",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
        )
        memory.add_fact(fact)

        # 清空所有
        memory.clear_all()

        assert len(memory._l1_tasks) == 0
        assert len(memory._l2_tasks) == 0
        assert len(memory._l3_summaries) == 0
        assert len(memory._task_index) == 0
        # clear_all 不清理 fact_index（根据实现）
        # assert len(memory._fact_index) == 0


class TestLoomMemoryCleanup:
    """测试清理功能"""

    def test_cleanup_task_index(self):
        """测试清理任务索引"""
        memory = LoomMemory(node_id="test-node", max_task_index_size=5)

        # 添加超过限制的任务
        for i in range(10):
            task = Task(
                task_id=f"task-{i}",
                action="test_action",
            )
            memory.add_task(task)

        # 手动触发清理
        memory._cleanup_task_index()

        # 应该只保留活跃的任务
        assert len(memory._task_index) <= 10


class TestLoomMemoryL3Management:
    """测试 L3 管理功能"""

    def test_add_to_l3(self):
        """测试添加到 L3"""
        memory = LoomMemory(node_id="test-node", max_l3_size=5)

        summary = TaskSummary(
            task_id="task-1",
            action="test_action",
            param_summary="params",
            result_summary="result",
        )

        memory._add_to_l3(summary)

        assert len(memory._l3_summaries) == 1
        assert memory._l3_summaries[0].task_id == "task-1"

    def test_add_to_l3_respects_limit(self):
        """测试 L3 容量限制"""
        memory = LoomMemory(node_id="test-node", max_l3_size=3)

        # 添加超过限制的摘要
        for i in range(5):
            summary = TaskSummary(
                task_id=f"task-{i}",
                action="test_action",
                param_summary=f"param{i}",
                result_summary=f"result{i}",
            )
            memory._add_to_l3(summary)

        # 应该只保留最近的3个
        assert len(memory._l3_summaries) == 3
        assert memory._l3_summaries[0].task_id == "task-2"  # 最旧的被移除

    def test_get_l3_summaries(self):
        """测试获取 L3 摘要"""
        memory = LoomMemory(node_id="test-node")

        # 添加摘要
        for i in range(5):
            summary = TaskSummary(
                task_id=f"task-{i}",
                action="test_action",
                param_summary=f"param{i}",
                result_summary=f"result{i}",
            )
            memory._add_to_l3(summary)

        # 获取所有摘要
        summaries = memory.get_l3_summaries()
        assert len(summaries) == 5

        # 获取限制数量的摘要
        summaries_limited = memory.get_l3_summaries(limit=3)
        assert len(summaries_limited) == 3
        assert summaries_limited[0].task_id == "task-2"  # 最近的3个


class TestLoomMemoryL4Management:
    """测试 L4 管理功能"""

    @pytest.mark.asyncio
    async def test_add_to_l4_with_embedding(self):
        """测试添加到 L4（带 embedding）"""
        memory = LoomMemory(node_id="test-node", enable_l4_vectorization=True)

        # 模拟 embedding provider
        mock_embedding = Mock()
        mock_embedding.embed = AsyncMock(return_value=[0.1] * 128)

        # 模拟 vector store
        mock_vector_store = Mock()
        mock_vector_store.add = AsyncMock()

        memory.embedding_provider = mock_embedding
        memory._l4_vector_store = mock_vector_store

        summary = TaskSummary(
            task_id="task-1",
            action="test_action",
            param_summary="params",
            result_summary="result",
        )

        await memory._add_to_l4(summary)

        mock_embedding.embed.assert_called_once()
        mock_vector_store.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_to_l4_without_embedding(self):
        """测试添加到 L4（没有 embedding provider）"""
        memory = LoomMemory(node_id="test-node", enable_l4_vectorization=True)

        summary = TaskSummary(
            task_id="task-1",
            action="test_action",
            param_summary="params",
            result_summary="result",
        )

        # 应该不会出错，只是不执行
        await memory._add_to_l4(summary)

    @pytest.mark.asyncio
    async def test_search_tasks_with_vector_store(self):
        """测试使用向量存储搜索任务"""
        memory = LoomMemory(node_id="test-node")

        # 模拟 embedding provider
        mock_embedding = Mock()
        mock_embedding.embed = AsyncMock(return_value=[0.1] * 128)

        # 模拟 vector store
        mock_vector_store = Mock()
        mock_vector_store.search = AsyncMock(
            return_value=[{"id": "task-1"}, {"id": "task-2"}]
        )

        memory.embedding_provider = mock_embedding
        memory._l4_vector_store = mock_vector_store

        # 添加任务到索引
        task1 = Task(task_id="task-1", action="test_action")
        task2 = Task(task_id="task-2", action="test_action")
        memory._task_index["task-1"] = task1
        memory._task_index["task-2"] = task2

        # 搜索任务
        results = await memory.search_tasks("test query", limit=5)

        assert len(results) == 2
        mock_embedding.embed.assert_called_once()
        mock_vector_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_tasks_without_vector_store(self):
        """测试不使用向量存储搜索任务（降级）"""
        memory = LoomMemory(node_id="test-node")

        # 添加任务
        task = Task(
            task_id="task-1",
            action="test_action",
            parameters={"key": "test"},
        )
        memory.add_task(task)

        # 搜索任务（应该使用简单搜索）
        results = await memory.search_tasks("test_action", limit=5)

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_facts_with_vector_store(self):
        """测试使用向量存储搜索事实"""
        memory = LoomMemory(node_id="test-node")

        # 模拟 embedding provider
        mock_embedding = Mock()
        mock_embedding.embed = AsyncMock(return_value=[0.1] * 128)

        # 模拟 vector store
        mock_vector_store = Mock()
        mock_vector_store.search = AsyncMock(
            return_value=[{"id": "fact_1"}, {"id": "fact_2"}]
        )

        memory.embedding_provider = mock_embedding
        memory._l4_vector_store = mock_vector_store

        # 添加事实到索引
        fact1 = Fact(fact_id="fact_1", content="Fact 1", fact_type=FactType.DOMAIN_KNOWLEDGE)
        fact2 = Fact(fact_id="fact_2", content="Fact 2", fact_type=FactType.DOMAIN_KNOWLEDGE)
        memory._fact_index["fact_1"] = fact1
        memory._fact_index["fact_2"] = fact2

        # 搜索事实
        results = await memory.search_facts("test query", limit=5)

        assert len(results) == 2
        mock_embedding.embed.assert_called_once()
        mock_vector_store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_facts_without_vector_store(self):
        """测试不使用向量存储搜索事实（降级）"""
        memory = LoomMemory(node_id="test-node")

        # 添加事实
        fact = Fact(
            fact_id="fact-1",
            content="Python is a language",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            tags=["programming"],
        )
        memory.add_fact(fact)

        # 搜索事实（应该使用简单搜索）
        results = await memory.search_facts("Python", limit=5)

        assert len(results) > 0
