"""
Task-Based Memory System Unit Tests

测试基于Task的记忆系统核心功能
"""

import pytest

from loom.memory import LoomMemory, MemoryTier
from loom.protocol import Task


class TestLoomMemoryInit:
    """测试 LoomMemory 初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        memory = LoomMemory(node_id="test_node")

        assert memory.node_id == "test_node"
        assert memory.max_l1_size == 50
        assert memory.max_l2_size == 100
        assert memory.max_l3_size == 500
        assert len(memory._l1_tasks) == 0
        assert len(memory._l2_tasks) == 0
        assert len(memory._l3_summaries) == 0

    def test_init_custom_sizes(self):
        """测试自定义大小初始化"""
        memory = LoomMemory(node_id="test_node", max_l1_size=30, max_l2_size=50, max_l3_size=200)

        assert memory.max_l1_size == 30
        assert memory.max_l2_size == 50
        assert memory.max_l3_size == 200

    def test_init_with_cleanup_limits(self):
        """测试带清理限制的初始化"""
        memory = LoomMemory(node_id="test_node", max_task_index_size=500, max_fact_index_size=2000)

        assert memory.max_task_index_size == 500
        assert memory.max_fact_index_size == 2000


class TestL1TaskStorage:
    """测试 L1 任务存储"""

    def test_add_task_to_l1(self):
        """测试添加任务到L1"""
        memory = LoomMemory(node_id="test_node", max_l1_size=3)

        task = Task(task_id="task1", action="test_action", parameters={"key": "value"})

        memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        assert len(memory._l1_tasks) == 1
        assert memory._l1_tasks[0].task_id == "task1"
        assert task.task_id in memory._task_index

    def test_l1_circular_buffer(self):
        """测试L1循环缓冲区"""
        memory = LoomMemory(node_id="test_node", max_l1_size=3)

        # 添加4个任务，应该只保留最后3个
        for i in range(4):
            task = Task(task_id=f"task{i}", action="test_action", parameters={"index": i})
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        assert len(memory._l1_tasks) == 3
        # 最旧的task0应该被驱逐
        task_ids = [t.task_id for t in memory._l1_tasks]
        assert "task0" not in task_ids
        assert "task1" in task_ids
        assert "task2" in task_ids
        assert "task3" in task_ids

    def test_get_l1_tasks(self):
        """测试获取L1任务"""
        memory = LoomMemory(node_id="test_node")

        # 添加5个任务
        for i in range(5):
            task = Task(task_id=f"task{i}", action="test")
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 获取最近3个
        recent_tasks = memory.get_l1_tasks(limit=3)
        assert len(recent_tasks) == 3
        assert recent_tasks[-1].task_id == "task4"


class TestL2TaskStorage:
    """测试 L2 工作记忆存储"""

    def test_add_task_to_l2(self):
        """测试添加任务到L2"""
        memory = LoomMemory(node_id="test_node", max_l2_size=5)

        task = Task(task_id="task1", action="test_action", parameters={"key": "value"})
        task.metadata["importance"] = 0.8

        memory.add_task(task, tier=MemoryTier.L2_WORKING)

        assert len(memory._l2_tasks) == 1
        assert memory._l2_tasks[0].task_id == "task1"

    def test_l2_importance_sorting(self):
        """测试L2按重要性排序"""
        memory = LoomMemory(node_id="test_node", max_l2_size=5)

        # 添加不同重要性的任务
        for i, importance in enumerate([0.3, 0.9, 0.5, 0.7]):
            task = Task(task_id=f"task{i}", action="test")
            task.metadata["importance"] = importance
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        # L2应该按重要性降序排列
        importances = [t.metadata.get("importance", 0.5) for t in memory._l2_tasks]
        assert importances == sorted(importances, reverse=True)
        assert memory._l2_tasks[0].task_id == "task1"  # 0.9最高

    def test_l2_capacity_limit(self):
        """测试L2容量限制"""
        memory = LoomMemory(node_id="test_node", max_l2_size=3)

        # 添加4个任务，最不重要的应该被移除
        for i, importance in enumerate([0.5, 0.8, 0.6, 0.9]):
            task = Task(task_id=f"task{i}", action="test")
            task.metadata["importance"] = importance
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        assert len(memory._l2_tasks) == 3
        # task0 (0.5) 应该被移除
        task_ids = [t.task_id for t in memory._l2_tasks]
        assert "task0" not in task_ids

    def test_get_l2_tasks(self):
        """测试获取L2任务"""
        memory = LoomMemory(node_id="test_node")

        # 添加任务
        for i in range(5):
            task = Task(task_id=f"task{i}", action="test")
            task.metadata["importance"] = 0.7
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        # 获取所有L2任务
        l2_tasks = memory.get_l2_tasks()
        assert len(l2_tasks) == 5

        # 获取前3个
        l2_tasks_limited = memory.get_l2_tasks(limit=3)
        assert len(l2_tasks_limited) == 3

    def test_clear_l2(self):
        """测试清空L2"""
        memory = LoomMemory(node_id="test_node")

        # 添加任务
        for i in range(3):
            task = Task(task_id=f"task{i}", action="test")
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        assert len(memory._l2_tasks) == 3

        # 清空L2
        memory.clear_l2()
        assert len(memory._l2_tasks) == 0


class TestL3TaskSummaries:
    """测试 L3 任务摘要"""

    def test_get_l3_summaries(self):
        """测试获取L3摘要"""
        memory = LoomMemory(node_id="test_node")

        # 直接添加摘要到L3（通过内部方法）
        from datetime import datetime

        from loom.memory.types import TaskSummary

        summary = TaskSummary(
            task_id="task1",
            action="test_action",
            param_summary="test params",
            result_summary="test result",
            importance=0.7,
            created_at=datetime.now(),
        )
        memory._add_to_l3(summary)

        summaries = memory.get_l3_summaries()
        assert len(summaries) == 1
        assert summaries[0].task_id == "task1"

    def test_l3_capacity_limit(self):
        """测试L3容量限制"""
        memory = LoomMemory(node_id="test_node", max_l3_size=3)

        from datetime import datetime

        from loom.memory.types import TaskSummary

        # 添加4个摘要
        for i in range(4):
            summary = TaskSummary(
                task_id=f"task{i}",
                action="test",
                param_summary="params",
                result_summary="result",
                created_at=datetime.now(),
            )
            memory._add_to_l3(summary)

        # 应该只保留最后3个
        assert len(memory._l3_summaries) == 3
        task_ids = [s.task_id for s in memory._l3_summaries]
        assert "task0" not in task_ids  # 最旧的被移除


class TestTaskPromotion:
    """测试任务提升机制"""

    def test_l1_to_l2_promotion(self):
        """测试L1到L2的提升"""
        memory = LoomMemory(node_id="test_node")

        # 添加高重要性任务到L1
        task = Task(task_id="important_task", action="test")
        task.metadata["importance"] = 0.8
        memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 触发提升
        memory.promote_tasks()

        # 应该被提升到L2
        assert len(memory._l2_tasks) > 0
        l2_task_ids = [t.task_id for t in memory._l2_tasks]
        assert "important_task" in l2_task_ids

    def test_low_importance_not_promoted(self):
        """测试低重要性任务不被提升"""
        memory = LoomMemory(node_id="test_node")

        # 添加低重要性任务到L1
        task = Task(task_id="low_task", action="test")
        task.metadata["importance"] = 0.3
        memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 触发提升
        memory.promote_tasks()

        # 不应该被提升到L2
        l2_task_ids = [t.task_id for t in memory._l2_tasks]
        assert "low_task" not in l2_task_ids


class TestMemoryCleanup:
    """测试内存清理机制（P0改进）"""

    def test_task_index_cleanup(self):
        """测试任务索引清理"""
        memory = LoomMemory(node_id="test_node", max_task_index_size=5)

        # 添加6个任务，触发清理
        for i in range(6):
            task = Task(task_id=f"task{i}", action="test")
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 索引应该被清理，只保留活跃的任务
        assert len(memory._task_index) <= 5

    def test_fact_index_cleanup(self):
        """测试事实索引清理"""
        memory = LoomMemory(node_id="test_node", max_fact_index_size=5)

        from loom.memory.types import Fact, FactType

        # 添加6个事实，触发清理
        for i in range(6):
            fact = Fact(
                fact_id=f"fact{i}",
                content=f"test fact {i}",
                fact_type=FactType.DOMAIN_KNOWLEDGE,
                confidence=0.8,
            )
            fact.access_count = i  # 设置不同的访问次数
            memory.add_fact(fact)

        # 索引应该被清理，保留高价值的事实
        assert len(memory._fact_index) <= 5

    def test_cleanup_preserves_active_tasks(self):
        """测试清理保留活跃任务"""
        memory = LoomMemory(node_id="test_node", max_task_index_size=10)

        # 添加任务到L1, L2, L3
        l1_task = Task(task_id="l1_task", action="test")
        memory.add_task(l1_task, tier=MemoryTier.L1_RAW_IO)

        l2_task = Task(task_id="l2_task", action="test")
        l2_task.metadata["importance"] = 0.8
        memory.add_task(l2_task, tier=MemoryTier.L2_WORKING)

        # 触发清理
        memory._cleanup_task_index()

        # 活跃任务应该被保留
        assert "l1_task" in memory._task_index
        assert "l2_task" in memory._task_index


class TestTaskRetrieval:
    """测试任务检索"""

    def test_get_task_by_id(self):
        """测试通过ID获取任务"""
        memory = LoomMemory(node_id="test_node")

        task = Task(task_id="test_task", action="test_action")
        memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        retrieved = memory.get_task("test_task")
        assert retrieved is not None
        assert retrieved.task_id == "test_task"
        assert retrieved.action == "test_action"

    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        memory = LoomMemory(node_id="test_node")

        retrieved = memory.get_task("nonexistent")
        assert retrieved is None

    def test_simple_search_tasks(self):
        """测试简单任务搜索"""
        memory = LoomMemory(node_id="test_node")

        # 添加不同的任务
        task1 = Task(task_id="task1", action="calculate_sum", parameters={"a": 1, "b": 2})
        task2 = Task(task_id="task2", action="fetch_data", parameters={"url": "example.com"})
        task3 = Task(task_id="task3", action="calculate_product", parameters={"x": 3, "y": 4})

        memory.add_task(task1, tier=MemoryTier.L1_RAW_IO)
        memory.add_task(task2, tier=MemoryTier.L1_RAW_IO)
        memory.add_task(task3, tier=MemoryTier.L1_RAW_IO)

        # 搜索包含"calculate"的任务
        results = memory._simple_search_tasks("calculate", limit=5)
        assert len(results) == 2
        result_ids = [t.task_id for t in results]
        assert "task1" in result_ids
        assert "task3" in result_ids


class TestFactManagement:
    """测试事实管理"""

    def test_add_fact(self):
        """测试添加事实"""
        memory = LoomMemory(node_id="test_node")

        from loom.memory.types import Fact, FactType

        fact = Fact(
            fact_id="fact1",
            content="Python is a programming language",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            confidence=0.9,
        )

        memory.add_fact(fact)

        assert "fact1" in memory._fact_index
        assert memory._fact_index["fact1"].content == "Python is a programming language"

    def test_simple_search_facts(self):
        """测试简单事实搜索"""
        memory = LoomMemory(node_id="test_node")

        from loom.memory.types import Fact, FactType

        # 添加多个事实
        fact1 = Fact(
            fact_id="fact1",
            content="Python is a programming language",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            tags=["python", "programming"],
        )
        fact2 = Fact(
            fact_id="fact2",
            content="JavaScript runs in browsers",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            tags=["javascript", "web"],
        )
        fact3 = Fact(
            fact_id="fact3",
            content="Python is used for data science",
            fact_type=FactType.DOMAIN_KNOWLEDGE,
            tags=["python", "data"],
        )

        memory.add_fact(fact1)
        memory.add_fact(fact2)
        memory.add_fact(fact3)

        # 搜索包含"python"的事实
        results = memory._simple_search_facts("python", limit=5)
        assert len(results) == 2
        result_ids = [f.fact_id for f in results]
        assert "fact1" in result_ids
        assert "fact3" in result_ids


class TestGeneralOperations:
    """测试通用操作"""

    def test_get_stats(self):
        """测试获取统计信息"""
        memory = LoomMemory(node_id="test_node")

        # 添加一些任务
        for i in range(3):
            task = Task(task_id=f"task{i}", action="test")
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        stats = memory.get_stats()

        assert stats["l1_size"] == 3
        assert stats["l2_size"] == 0
        assert stats["l3_size"] == 0
        assert stats["total_tasks"] == 3
        assert stats["max_l1_size"] == 50

    def test_clear_all(self):
        """测试清空所有记忆"""
        memory = LoomMemory(node_id="test_node")

        # 添加任务到各层
        task1 = Task(task_id="task1", action="test")
        memory.add_task(task1, tier=MemoryTier.L1_RAW_IO)

        task2 = Task(task_id="task2", action="test")
        task2.metadata["importance"] = 0.8
        memory.add_task(task2, tier=MemoryTier.L2_WORKING)

        assert len(memory._l1_tasks) > 0
        assert len(memory._l2_tasks) > 0

        # 清空所有
        memory.clear_all()

        assert len(memory._l1_tasks) == 0
        assert len(memory._l2_tasks) == 0
        assert len(memory._l3_summaries) == 0
        assert len(memory._task_index) == 0


class TestEventBusSubscription:
    """测试 EventBus 订阅机制"""

    def test_init_with_event_bus(self):
        """测试带EventBus的初始化"""
        from unittest.mock import Mock

        mock_event_bus = Mock()
        memory = LoomMemory(node_id="test_node", event_bus=mock_event_bus)

        # 应该订阅EventBus的通配符handler
        mock_event_bus.register_handler.assert_called_once_with("*", memory._on_task)
        assert memory._event_bus == mock_event_bus

    def test_init_without_event_bus(self):
        """测试不带EventBus的初始化（向后兼容）"""
        memory = LoomMemory(node_id="test_node")

        assert memory._event_bus is None

    @pytest.mark.asyncio
    async def test_on_task_adds_to_l1(self):
        """测试_on_task自动添加Task到L1"""
        memory = LoomMemory(node_id="test_node", max_l1_size=5)

        task = Task(task_id="task1", action="test_action", parameters={"key": "value"})

        # 调用_on_task handler
        result = await memory._on_task(task)

        # 应该添加到L1
        assert len(memory._l1_tasks) == 1
        assert memory._l1_tasks[0].task_id == "task1"

        # 应该返回原始Task
        assert result.task_id == "task1"

    @pytest.mark.asyncio
    async def test_on_task_selective_l2_storage(self):
        """测试_on_task根据重要性选择性添加到L2"""
        memory = LoomMemory(node_id="test_node", max_l2_size=10)

        # 低重要性任务（不应该添加到L2）
        task1 = Task(task_id="task1", action="test")
        task1.metadata["importance"] = 0.5
        await memory._on_task(task1)

        # 高重要性任务（应该添加到L2）
        task2 = Task(task_id="task2", action="test")
        task2.metadata["importance"] = 0.8
        await memory._on_task(task2)

        # L1应该有两个任务
        assert len(memory._l1_tasks) == 2

        # L2应该只有高重要性任务
        assert len(memory._l2_tasks) == 1
        assert memory._l2_tasks[0].task_id == "task2"

    @pytest.mark.asyncio
    async def test_on_task_importance_threshold(self):
        """测试_on_task的重要性阈值（0.6）"""
        memory = LoomMemory(node_id="test_node", max_l2_size=10)

        # 测试边界值
        test_cases = [
            (0.5, False),  # 低于阈值
            (0.6, False),  # 等于阈值（不包含）
            (0.61, True),  # 高于阈值
            (0.8, True),   # 明显高于阈值
        ]

        for i, (importance, should_be_in_l2) in enumerate(test_cases):
            task = Task(task_id=f"task{i}", action="test")
            task.metadata["importance"] = importance
            await memory._on_task(task)

        # 检查L2中的任务
        l2_task_ids = [t.task_id for t in memory._l2_tasks]
        assert "task0" not in l2_task_ids  # 0.5
        assert "task1" not in l2_task_ids  # 0.6
        assert "task2" in l2_task_ids      # 0.61
        assert "task3" in l2_task_ids      # 0.8

    @pytest.mark.asyncio
    async def test_on_task_default_importance(self):
        """测试_on_task处理没有importance的Task"""
        memory = LoomMemory(node_id="test_node", max_l2_size=10)

        # 没有设置importance的任务（默认0.5）
        task = Task(task_id="task1", action="test")
        await memory._on_task(task)

        # 应该添加到L1
        assert len(memory._l1_tasks) == 1

        # 不应该添加到L2（默认0.5 <= 0.6）
        assert len(memory._l2_tasks) == 0

    @pytest.mark.asyncio
    async def test_on_task_returns_original_task(self):
        """测试_on_task返回原始Task不修改"""
        memory = LoomMemory(node_id="test_node")

        task = Task(task_id="task1", action="test_action", parameters={"key": "value"})
        task.metadata["importance"] = 0.8

        result = await memory._on_task(task)

        # 应该返回相同的Task对象
        assert result is task
        assert result.task_id == "task1"
        assert result.action == "test_action"

    @pytest.mark.asyncio
    async def test_integration_with_event_bus(self):
        """测试与EventBus的集成"""
        from loom.events.event_bus import EventBus

        event_bus = EventBus()
        memory = LoomMemory(node_id="test_node", event_bus=event_bus, max_l1_size=10, max_l2_size=10)

        # 通过EventBus发布任务
        task1 = Task(task_id="task1", action="test_action")
        task1.metadata["importance"] = 0.5

        task2 = Task(task_id="task2", action="test_action")
        task2.metadata["importance"] = 0.8

        await event_bus.publish(task1)
        await event_bus.publish(task2)

        # 等待异步处理完成
        import asyncio
        await asyncio.sleep(0.01)

        # Memory应该自动接收到任务
        assert len(memory._l1_tasks) == 2
        assert len(memory._l2_tasks) == 1  # 只有高重要性的task2

        l1_task_ids = [t.task_id for t in memory._l1_tasks]
        assert "task1" in l1_task_ids
        assert "task2" in l1_task_ids

        l2_task_ids = [t.task_id for t in memory._l2_tasks]
        assert "task2" in l2_task_ids

