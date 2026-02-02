"""
Memory Layers Unit Tests

测试记忆层功能
"""

import pytest

from loom.memory.layers.circular import CircularBufferLayer
from loom.memory.layers.priority import PriorityQueueLayer
from loom.protocol import Task


class TestCircularBufferLayer:
    """测试 CircularBufferLayer"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        layer = CircularBufferLayer(max_size=10)

        assert layer.size() == 0
        assert layer._buffer.maxlen == 10

    @pytest.mark.asyncio
    async def test_add_and_retrieve(self):
        """测试添加和检索"""
        layer = CircularBufferLayer(max_size=5)

        task1 = Task(task_id="t1", action="test")
        task2 = Task(task_id="t2", action="test")

        await layer.add(task1)
        await layer.add(task2)

        assert layer.size() == 2

        retrieved = await layer.retrieve(None, limit=10)
        assert len(retrieved) == 2
        assert retrieved[0].task_id == "t1"
        assert retrieved[1].task_id == "t2"

    @pytest.mark.asyncio
    async def test_retrieve_with_limit(self):
        """测试带限制的检索"""
        layer = CircularBufferLayer(max_size=10)

        for i in range(5):
            await layer.add(Task(task_id=f"t{i}", action="test"))

        retrieved = await layer.retrieve(None, limit=3)

        assert len(retrieved) == 3
        # 应该返回最近的3个
        assert retrieved[0].task_id == "t2"
        assert retrieved[1].task_id == "t3"
        assert retrieved[2].task_id == "t4"

    @pytest.mark.asyncio
    async def test_automatic_eviction(self):
        """测试自动驱逐"""
        layer = CircularBufferLayer(max_size=3)

        # 添加3个任务，填满缓冲区
        for i in range(3):
            await layer.add(Task(task_id=f"t{i}", action="test"))

        assert layer.size() == 3

        # 添加第4个任务，应该驱逐最旧的
        await layer.add(Task(task_id="t3", action="test"))

        assert layer.size() == 3
        retrieved = await layer.retrieve(None, limit=10)
        # 最旧的t0应该被驱逐
        assert retrieved[0].task_id == "t1"
        assert retrieved[1].task_id == "t2"
        assert retrieved[2].task_id == "t3"

    @pytest.mark.asyncio
    async def test_eviction_callback(self):
        """测试驱逐回调"""
        layer = CircularBufferLayer(max_size=2)

        evicted_tasks = []

        def callback(task: Task):
            evicted_tasks.append(task)

        layer.on_eviction(callback)

        # 添加2个任务
        task1 = Task(task_id="t1", action="test")
        task2 = Task(task_id="t2", action="test")
        await layer.add(task1)
        await layer.add(task2)

        # 添加第3个任务，应该触发回调
        task3 = Task(task_id="t3", action="test")
        await layer.add(task3)

        assert len(evicted_tasks) == 1
        assert evicted_tasks[0].task_id == "t1"

    @pytest.mark.asyncio
    async def test_manual_eviction(self):
        """测试手动驱逐"""
        layer = CircularBufferLayer(max_size=10)

        for i in range(5):
            await layer.add(Task(task_id=f"t{i}", action="test"))

        # 手动驱逐2个任务
        evicted = await layer.evict(count=2)

        assert len(evicted) == 2
        assert evicted[0].task_id == "t0"
        assert evicted[1].task_id == "t1"
        assert layer.size() == 3

    @pytest.mark.asyncio
    async def test_evict_more_than_available(self):
        """测试驱逐数量超过可用数量"""
        layer = CircularBufferLayer(max_size=10)

        await layer.add(Task(task_id="t1", action="test"))
        await layer.add(Task(task_id="t2", action="test"))

        # 尝试驱逐5个，但只有2个
        evicted = await layer.evict(count=5)

        assert len(evicted) == 2
        assert layer.size() == 0

    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空"""
        layer = CircularBufferLayer(max_size=10)

        for i in range(5):
            await layer.add(Task(task_id=f"t{i}", action="test"))

        assert layer.size() == 5

        layer.clear()

        assert layer.size() == 0

    @pytest.mark.asyncio
    async def test_multiple_eviction_callbacks(self):
        """测试多个驱逐回调"""
        layer = CircularBufferLayer(max_size=2)

        evicted1 = []
        evicted2 = []

        layer.on_eviction(lambda t: evicted1.append(t))
        layer.on_eviction(lambda t: evicted2.append(t))

        await layer.add(Task(task_id="t1", action="test"))
        await layer.add(Task(task_id="t2", action="test"))
        await layer.add(Task(task_id="t3", action="test"))

        # 两个回调都应该被触发
        assert len(evicted1) == 1
        assert len(evicted2) == 1
        assert evicted1[0].task_id == "t1"
        assert evicted2[0].task_id == "t1"


class TestPriorityQueueLayer:
    """测试 PriorityQueueLayer"""

    @pytest.mark.asyncio
    async def test_init(self):
        """测试初始化"""
        layer = PriorityQueueLayer(max_size=10)

        assert layer.size() == 0
        assert layer._max_size == 10

    @pytest.mark.asyncio
    async def test_add_and_retrieve_by_priority(self):
        """测试按优先级添加和检索"""
        layer = PriorityQueueLayer(max_size=10)

        # 添加不同优先级的任务
        task1 = Task(task_id="t1", action="test", metadata={"importance": 0.3})
        task2 = Task(task_id="t2", action="test", metadata={"importance": 0.9})
        task3 = Task(task_id="t3", action="test", metadata={"importance": 0.6})

        await layer.add(task1)
        await layer.add(task2)
        await layer.add(task3)

        assert layer.size() == 3

        # 检索应该按优先级排序（高优先级在前）
        retrieved = await layer.retrieve(None, limit=10)
        assert len(retrieved) == 3
        assert retrieved[0].task_id == "t2"  # importance 0.9
        assert retrieved[1].task_id == "t3"  # importance 0.6
        assert retrieved[2].task_id == "t1"  # importance 0.3

    @pytest.mark.asyncio
    async def test_add_with_default_importance(self):
        """测试添加没有importance的任务（使用默认值）"""
        layer = PriorityQueueLayer(max_size=10)

        task = Task(task_id="t1", action="test")
        await layer.add(task)

        assert layer.size() == 1

    @pytest.mark.asyncio
    async def test_add_when_full_with_higher_priority(self):
        """测试堆满时添加更高优先级任务"""
        layer = PriorityQueueLayer(max_size=3)

        # 填满堆
        await layer.add(Task(task_id="t1", action="test", metadata={"importance": 0.3}))
        await layer.add(Task(task_id="t2", action="test", metadata={"importance": 0.5}))
        await layer.add(Task(task_id="t3", action="test", metadata={"importance": 0.7}))

        assert layer.size() == 3

        # 添加更高优先级的任务
        await layer.add(Task(task_id="t4", action="test", metadata={"importance": 0.9}))

        assert layer.size() == 3
        retrieved = await layer.retrieve(None, limit=10)
        task_ids = [t.task_id for t in retrieved]
        assert "t4" in task_ids  # 新的高优先级任务应该被添加

    @pytest.mark.asyncio
    async def test_add_when_full_keeps_lower_priority_out(self):
        """测试堆满时不添加低优先级任务"""
        layer = PriorityQueueLayer(max_size=3)

        # 填满堆
        await layer.add(Task(task_id="t1", action="test", metadata={"importance": 0.5}))
        await layer.add(Task(task_id="t2", action="test", metadata={"importance": 0.7}))
        await layer.add(Task(task_id="t3", action="test", metadata={"importance": 0.9}))

        # 尝试添加更低优先级的任务，应该被拒绝
        await layer.add(Task(task_id="t4", action="test", metadata={"importance": 0.2}))

        assert layer.size() == 3
        retrieved = await layer.retrieve(None, limit=10)
        task_ids = [t.task_id for t in retrieved]
        assert "t4" not in task_ids  # 低优先级任务不应该被添加

    @pytest.mark.asyncio
    async def test_retrieve_with_limit(self):
        """测试带限制的检索"""
        layer = PriorityQueueLayer(max_size=10)

        for i in range(5):
            await layer.add(Task(task_id=f"t{i}", action="test", metadata={"importance": i * 0.2}))

        retrieved = await layer.retrieve(None, limit=3)

        assert len(retrieved) == 3
        # 应该返回最高优先级的3个

    @pytest.mark.asyncio
    async def test_evict(self):
        """测试手动驱逐"""
        layer = PriorityQueueLayer(max_size=10)

        await layer.add(Task(task_id="t1", action="test", metadata={"importance": 0.3}))
        await layer.add(Task(task_id="t2", action="test", metadata={"importance": 0.7}))
        await layer.add(Task(task_id="t3", action="test", metadata={"importance": 0.5}))

        # 驱逐1个任务（应该驱逐最低优先级的）
        evicted = await layer.evict(count=1)

        assert len(evicted) == 1
        assert layer.size() == 2

    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空"""
        layer = PriorityQueueLayer(max_size=10)

        for i in range(5):
            await layer.add(Task(task_id=f"t{i}", action="test", metadata={"importance": 0.5}))

        assert layer.size() == 5

        layer.clear()

        assert layer.size() == 0

