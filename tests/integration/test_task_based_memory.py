"""
Task-Based Memory System Integration Test

验证新的Task-based记忆系统的核心功能
"""

from loom.memory import LoomMemory, MemoryTier
from loom.runtime import Task, TaskStatus


class TestTaskBasedMemory:
    """测试基于Task的记忆系统"""

    def test_l1_task_storage(self):
        """测试L1 Task存储"""
        memory = LoomMemory(node_id="test_node", max_l1_size=3)

        # 创建并添加Task
        task1 = Task(action="test_action_1", parameters={"key": "value1"})
        task2 = Task(action="test_action_2", parameters={"key": "value2"})
        task3 = Task(action="test_action_3", parameters={"key": "value3"})

        memory.add_task(task1, tier=MemoryTier.L1_RAW_IO)
        memory.add_task(task2, tier=MemoryTier.L1_RAW_IO)
        memory.add_task(task3, tier=MemoryTier.L1_RAW_IO)

        # 验证L1存储
        l1_tasks = memory.get_l1_tasks(limit=10)
        assert len(l1_tasks) == 3
        assert l1_tasks[0].action == "test_action_1"
        assert l1_tasks[2].action == "test_action_3"

    def test_l1_circular_buffer(self):
        """测试L1循环缓冲区（Token-First Design）"""
        # Each task ≈ 7 tokens ("action_X: {'index': X} -> None" ≈ 31 chars / 4)
        # Budget of 25 tokens holds 3 tasks (21 tokens) but evicts on 4th (28 tokens)
        memory = LoomMemory(node_id="test_node", l1_token_budget=25)

        # 添加4个Task，应该只保留最后3个（token 预算驱逐）
        for i in range(4):
            task = Task(action=f"action_{i}", parameters={"index": i})
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        l1_tasks = memory.get_l1_tasks(limit=10)
        assert len(l1_tasks) == 3

        # 第一个应该被移除（FIFO驱逐）
        actions = [t.action for t in l1_tasks]
        assert "action_0" not in actions
        assert "action_1" in actions
        assert "action_2" in actions
        assert "action_3" in actions

    def test_l2_importance_based_storage(self):
        """测试L2基于重要性的存储"""
        memory = LoomMemory(node_id="test_node", max_l2_size=5)

        # 创建不同重要性的Task
        task1 = Task(action="important_task", parameters={})
        task1.metadata["importance"] = 0.8

        task2 = Task(action="normal_task", parameters={})
        task2.metadata["importance"] = 0.5

        task3 = Task(action="very_important_task", parameters={})
        task3.metadata["importance"] = 0.9

        # 添加到L2
        memory.add_task(task1, tier=MemoryTier.L2_WORKING)
        memory.add_task(task2, tier=MemoryTier.L2_WORKING)
        memory.add_task(task3, tier=MemoryTier.L2_WORKING)

        # 验证L2按重要性排序
        l2_tasks = memory.get_l2_tasks()
        assert len(l2_tasks) == 3
        assert l2_tasks[0].action == "very_important_task"  # 最重要的在前
        assert l2_tasks[1].action == "important_task"
        assert l2_tasks[2].action == "normal_task"

    def test_l1_to_l2_promotion(self):
        """测试L1到L2的提升"""
        memory = LoomMemory(node_id="test_node", max_l1_size=10, max_l2_size=5)

        # 添加重要Task到L1
        important_task = Task(action="important_action", parameters={})
        important_task.metadata["importance"] = 0.7  # 超过0.6阈值

        memory.add_task(important_task, tier=MemoryTier.L1_RAW_IO)

        # 触发提升
        memory.promote_tasks()

        # 验证Task被提升到L2
        l2_tasks = memory.get_l2_tasks()
        assert len(l2_tasks) == 1
        assert l2_tasks[0].action == "important_action"

    def test_task_retrieval_by_id(self):
        """测试通过ID检索Task"""
        memory = LoomMemory(node_id="test_node")

        task = Task(action="test_action", parameters={"key": "value"})
        memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        # 通过ID检索
        retrieved = memory.get_task(task.task_id)
        assert retrieved is not None
        assert retrieved.action == "test_action"
        assert retrieved.task_id == task.task_id

    def test_memory_stats(self):
        """测试记忆统计信息（Token-First Design）"""
        memory = LoomMemory(node_id="test_node", l1_token_budget=500, l2_token_budget=1000)

        # 添加一些Task
        for i in range(5):
            task = Task(action=f"action_{i}", parameters={})
            memory.add_task(task, tier=MemoryTier.L1_RAW_IO)

        stats = memory.get_stats()
        assert stats["l1_item_count"] == 5
        assert stats["l2_item_count"] == 0
        assert stats["l3_item_count"] == 0
        assert stats["total_tasks"] == 5
        assert stats["l1_token_budget"] == 500
        assert stats["l2_token_budget"] == 1000

    def test_clear_l2(self):
        """测试清空L2"""
        memory = LoomMemory(node_id="test_node")

        task = Task(action="test_action", parameters={})
        memory.add_task(task, tier=MemoryTier.L2_WORKING)

        assert len(memory.get_l2_tasks()) == 1

        memory.clear_l2()
        assert len(memory.get_l2_tasks()) == 0

    def test_clear_all(self):
        """测试清空所有记忆"""
        memory = LoomMemory(node_id="test_node")

        # 添加Task到不同层级
        task1 = Task(action="action_1", parameters={})
        task2 = Task(action="action_2", parameters={})

        memory.add_task(task1, tier=MemoryTier.L1_RAW_IO)
        memory.add_task(task2, tier=MemoryTier.L2_WORKING)

        assert memory.get_stats()["total_tasks"] == 2

        memory.clear_all()
        assert memory.get_stats()["total_tasks"] == 0
        assert memory.get_stats()["l1_item_count"] == 0
        assert memory.get_stats()["l2_item_count"] == 0

    def test_task_summary_generation(self):
        """测试Task摘要生成（Token-First Design）"""
        # Each task ≈ 60 tokens (action + 100-char params + 100-char result)
        # 3 tasks ≈ 180 tokens; budget=200 → usage ratio 0.9 > compress threshold 0.85
        memory = LoomMemory(node_id="test_node", l2_token_budget=200)

        # 添加Task到L2直到触发压缩
        for i in range(3):
            task = Task(action=f"action_{i}", parameters={"data": "x" * 100})
            task.metadata["importance"] = 0.3  # 低重要性
            task.result = {"output": "y" * 100}
            task.status = TaskStatus.COMPLETED
            memory.add_task(task, tier=MemoryTier.L2_WORKING)

        # 触发L2到L3的压缩
        memory._promote_l2_to_l3()

        # 验证L3有摘要
        l3_summaries = memory.get_l3_summaries()
        assert len(l3_summaries) > 0

        # 验证摘要内容
        summary = l3_summaries[0]
        assert summary.action.startswith("action_")
        assert len(summary.param_summary) <= 203  # 200 + "..."
        assert len(summary.result_summary) <= 203

    def test_simple_search(self):
        """测试简单文本搜索（无向量化）"""
        memory = LoomMemory(node_id="test_node", enable_l4_vectorization=False)

        # 添加不同的Task
        task1 = Task(action="user_login", parameters={"username": "alice"})
        task2 = Task(action="user_logout", parameters={"username": "bob"})
        task3 = Task(action="data_fetch", parameters={"query": "users"})

        memory.add_task(task1, tier=MemoryTier.L1_RAW_IO)
        memory.add_task(task2, tier=MemoryTier.L1_RAW_IO)
        memory.add_task(task3, tier=MemoryTier.L1_RAW_IO)

        # 搜索包含"user"的Task
        results = memory._simple_search_tasks("user", limit=5)
        assert len(results) >= 2  # 至少找到task1和task2

        # 验证结果包含正确的Task
        actions = [t.action for t in results]
        assert "user_login" in actions or "user_logout" in actions
