"""
Memory Layers Unit Tests (Token-First Design)

测试记忆层功能 - 基于 Token 预算的设计
"""

import pytest

from loom.memory.layers import TokenBudgetLayer, PriorityTokenLayer
from loom.runtime import Task


class TestTokenBudgetLayer:
    """测试 TokenBudgetLayer (原 CircularBufferLayer)"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        layer = TokenBudgetLayer(token_budget=1000)

        assert layer.size() == 0
        assert layer.token_usage() == 0
        assert layer.token_budget == 1000

    @pytest.mark.asyncio
    async def test_add_and_retrieve(self):
        """测试添加和检索"""
        layer = TokenBudgetLayer(token_budget=1000)

        task1 = Task(task_id="t1", action="test")
        task2 = Task(task_id="t2", action="test")

        await layer.add(task1, token_count=100)
        await layer.add(task2, token_count=150)

        assert layer.size() == 2
        assert layer.token_usage() == 250

        retrieved = await layer.retrieve(None, limit=10)
        assert len(retrieved) == 2
        assert retrieved[0].task_id == "t1"
        assert retrieved[1].task_id == "t2"

    @pytest.mark.asyncio
    async def test_retrieve_with_limit(self):
        """测试带限制的检索"""
        layer = TokenBudgetLayer(token_budget=10000)

        for i in range(5):
            await layer.add(Task(task_id=f"t{i}", action="test"), token_count=100)

        retrieved = await layer.retrieve(None, limit=3)

        assert len(retrieved) == 3
        # 应该返回最近的3个
        assert retrieved[0].task_id == "t2"
        assert retrieved[1].task_id == "t3"
        assert retrieved[2].task_id == "t4"

    @pytest.mark.asyncio
    async def test_automatic_eviction_by_token_budget(self):
        """测试基于 token 预算的自动驱逐"""
        layer = TokenBudgetLayer(token_budget=300)

        # 添加3个任务，每个100 tokens，填满预算
        for i in range(3):
            await layer.add(Task(task_id=f"t{i}", action="test"), token_count=100)

        assert layer.size() == 3
        assert layer.token_usage() == 300

        # 添加第4个任务（100 tokens），应该驱逐最旧的
        await layer.add(Task(task_id="t3", action="test"), token_count=100)

        assert layer.size() == 3
        assert layer.token_usage() == 300
        retrieved = await layer.retrieve(None, limit=10)
        # 最旧的t0应该被驱逐
        assert retrieved[0].task_id == "t1"
        assert retrieved[1].task_id == "t2"
        assert retrieved[2].task_id == "t3"

    @pytest.mark.asyncio
    async def test_eviction_callback(self):
        """测试驱逐回调"""
        layer = TokenBudgetLayer(token_budget=200)

        evicted_tasks = []

        def callback(task: Task):
            evicted_tasks.append(task)

        layer.on_eviction(callback)

        # 添加2个任务
        task1 = Task(task_id="t1", action="test")
        task2 = Task(task_id="t2", action="test")
        await layer.add(task1, token_count=100)
        await layer.add(task2, token_count=100)

        # 添加第3个任务，应该触发回调
        task3 = Task(task_id="t3", action="test")
        await layer.add(task3, token_count=100)

        assert len(evicted_tasks) == 1
        assert evicted_tasks[0].task_id == "t1"

    @pytest.mark.asyncio
    async def test_evict_tokens(self):
        """测试按 token 数驱逐"""
        layer = TokenBudgetLayer(token_budget=10000)

        for i in range(5):
            await layer.add(Task(task_id=f"t{i}", action="test"), token_count=100)

        assert layer.token_usage() == 500

        # 驱逐 200 tokens
        evicted = await layer.evict_tokens(tokens_to_free=200)

        assert len(evicted) == 2
        assert evicted[0].task_id == "t0"
        assert evicted[1].task_id == "t1"
        assert layer.size() == 3
        assert layer.token_usage() == 300

    @pytest.mark.asyncio
    async def test_evict_more_tokens_than_available(self):
        """测试驱逐 token 数超过可用数量"""
        layer = TokenBudgetLayer(token_budget=10000)

        await layer.add(Task(task_id="t1", action="test"), token_count=100)
        await layer.add(Task(task_id="t2", action="test"), token_count=100)

        # 尝试驱逐 500 tokens，但只有 200
        evicted = await layer.evict_tokens(tokens_to_free=500)

        assert len(evicted) == 2
        assert layer.size() == 0
        assert layer.token_usage() == 0

    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空"""
        layer = TokenBudgetLayer(token_budget=10000)

        for i in range(5):
            await layer.add(Task(task_id=f"t{i}", action="test"), token_count=100)

        assert layer.size() == 5
        assert layer.token_usage() == 500

        layer.clear()

        assert layer.size() == 0
        assert layer.token_usage() == 0

    @pytest.mark.asyncio
    async def test_multiple_eviction_callbacks(self):
        """测试多个驱逐回调"""
        layer = TokenBudgetLayer(token_budget=200)

        evicted1 = []
        evicted2 = []

        layer.on_eviction(lambda t: evicted1.append(t))
        layer.on_eviction(lambda t: evicted2.append(t))

        await layer.add(Task(task_id="t1", action="test"), token_count=100)
        await layer.add(Task(task_id="t2", action="test"), token_count=100)
        await layer.add(Task(task_id="t3", action="test"), token_count=100)

        # 两个回调都应该被触发
        assert len(evicted1) == 1
        assert len(evicted2) == 1
        assert evicted1[0].task_id == "t1"
        assert evicted2[0].task_id == "t1"


class TestPriorityTokenLayer:
    """测试 PriorityTokenLayer (原 PriorityQueueLayer)"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        layer = PriorityTokenLayer(token_budget=1000)

        assert layer.size() == 0
        assert layer.token_usage() == 0
        assert layer.token_budget == 1000

    @pytest.mark.asyncio
    async def test_add_and_retrieve(self):
        """测试添加和检索"""
        layer = PriorityTokenLayer(token_budget=1000)

        task1 = Task(task_id="t1", action="test", metadata={"importance": 0.8})
        task2 = Task(task_id="t2", action="test", metadata={"importance": 0.5})

        await layer.add(task1, token_count=100)
        await layer.add(task2, token_count=100)

        assert layer.size() == 2
        assert layer.token_usage() == 200

        # 检索应该按重要性排序（高重要性在前）
        retrieved = await layer.retrieve(None, limit=10)
        assert len(retrieved) == 2
        assert retrieved[0].task_id == "t1"  # 重要性 0.8
        assert retrieved[1].task_id == "t2"  # 重要性 0.5

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """测试优先级排序"""
        layer = PriorityTokenLayer(token_budget=10000)

        # 添加不同重要性的任务
        await layer.add(
            Task(task_id="low", action="test", metadata={"importance": 0.2}),
            token_count=100
        )
        await layer.add(
            Task(task_id="high", action="test", metadata={"importance": 0.9}),
            token_count=100
        )
        await layer.add(
            Task(task_id="medium", action="test", metadata={"importance": 0.5}),
            token_count=100
        )

        retrieved = await layer.retrieve(None, limit=10)

        # 应该按重要性降序排列
        assert retrieved[0].task_id == "high"
        assert retrieved[1].task_id == "medium"
        assert retrieved[2].task_id == "low"

    @pytest.mark.asyncio
    async def test_eviction_by_token_budget(self):
        """测试基于 token 预算的驱逐（驱逐低优先级）"""
        layer = PriorityTokenLayer(token_budget=200)

        # 添加2个任务，填满预算
        await layer.add(
            Task(task_id="low", action="test", metadata={"importance": 0.3}),
            token_count=100
        )
        await layer.add(
            Task(task_id="high", action="test", metadata={"importance": 0.9}),
            token_count=100
        )

        assert layer.size() == 2
        assert layer.token_usage() == 200

        # 添加一个高优先级任务，应该驱逐低优先级的
        result = await layer.add(
            Task(task_id="new_high", action="test", metadata={"importance": 0.8}),
            token_count=100
        )

        assert result is True
        assert layer.size() == 2
        retrieved = await layer.retrieve(None, limit=10)
        task_ids = [t.task_id for t in retrieved]
        assert "low" not in task_ids  # 低优先级被驱逐
        assert "high" in task_ids
        assert "new_high" in task_ids

    @pytest.mark.asyncio
    async def test_evict_tokens(self):
        """测试按 token 数驱逐（驱逐低优先级）"""
        layer = PriorityTokenLayer(token_budget=10000)

        await layer.add(
            Task(task_id="low", action="test", metadata={"importance": 0.2}),
            token_count=100
        )
        await layer.add(
            Task(task_id="high", action="test", metadata={"importance": 0.9}),
            token_count=100
        )
        await layer.add(
            Task(task_id="medium", action="test", metadata={"importance": 0.5}),
            token_count=100
        )

        # 驱逐 100 tokens，应该驱逐最低优先级的
        evicted = await layer.evict_tokens(tokens_to_free=100)

        assert len(evicted) == 1
        assert evicted[0].task_id == "low"
        assert layer.size() == 2
        assert layer.token_usage() == 200

    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空"""
        layer = PriorityTokenLayer(token_budget=10000)

        for i in range(5):
            await layer.add(
                Task(task_id=f"t{i}", action="test", metadata={"importance": 0.5}),
                token_count=100
            )

        assert layer.size() == 5
        assert layer.token_usage() == 500

        layer.clear()

        assert layer.size() == 0
        assert layer.token_usage() == 0

    @pytest.mark.asyncio
    async def test_default_importance(self):
        """测试默认重要性"""
        layer = PriorityTokenLayer(token_budget=1000)

        # 不设置 importance，应该使用默认值 0.5
        task = Task(task_id="t1", action="test")
        await layer.add(task, token_count=100)

        assert layer.size() == 1


# 向后兼容性测试
class TestBackwardCompatibility:
    """测试向后兼容的别名"""

    def test_circular_buffer_layer_alias(self):
        """测试 CircularBufferLayer 别名"""
        from loom.memory.layers import CircularBufferLayer
        layer = CircularBufferLayer(token_budget=1000)
        assert isinstance(layer, TokenBudgetLayer)

    def test_priority_queue_layer_alias(self):
        """测试 PriorityQueueLayer 别名"""
        from loom.memory.layers import PriorityQueueLayer
        layer = PriorityQueueLayer(token_budget=1000)
        assert isinstance(layer, PriorityTokenLayer)
