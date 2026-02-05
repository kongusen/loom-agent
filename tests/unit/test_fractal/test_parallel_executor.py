"""
ParallelExecutor Unit Tests

测试并行执行器功能
"""

import asyncio

import pytest

from loom.events import EventBus, OutputStrategy
from loom.fractal import ParallelExecutor, ParallelResult, ParallelTask


class TestParallelTask:
    """测试ParallelTask数据类"""

    def test_parallel_task_creation(self):
        """测试创建ParallelTask"""
        task = ParallelTask(
            task_id="chunk_1",
            content="测试内容",
            metadata={"source": "test"},
        )

        assert task.task_id == "chunk_1"
        assert task.content == "测试内容"
        assert task.metadata["source"] == "test"

    def test_parallel_task_default_metadata(self):
        """测试默认metadata"""
        task = ParallelTask(task_id="t1", content="content")
        assert task.metadata == {}


class TestParallelResult:
    """测试ParallelResult数据类"""

    def test_parallel_result_success(self):
        """测试成功结果"""
        result = ParallelResult(
            task_id="task1",
            result="执行成功",
            success=True,
            duration=1.5,
        )

        assert result.task_id == "task1"
        assert result.result == "执行成功"
        assert result.success is True
        assert result.error is None

    def test_parallel_result_failure(self):
        """测试失败结果"""
        result = ParallelResult(
            task_id="task1",
            result=None,
            success=False,
            error="执行失败",
        )

        assert result.success is False
        assert result.error == "执行失败"


class TestParallelExecutor:
    """测试ParallelExecutor"""

    def test_executor_creation(self):
        """测试创建执行器"""
        bus = EventBus()
        executor = ParallelExecutor(
            event_bus=bus,
            max_concurrency=3,
            output_strategy=OutputStrategy.REALTIME,
        )

        assert executor.event_bus is bus
        assert executor.output_strategy == OutputStrategy.REALTIME

    @pytest.mark.asyncio
    async def test_execute_single_task(self):
        """测试执行单个任务"""
        bus = EventBus()
        executor = ParallelExecutor(bus, max_concurrency=1)

        tasks = [ParallelTask(task_id="single", content="测试")]

        async def simple_factory(task: ParallelTask, child_bus: EventBus) -> str:
            return f"处理: {task.content}"

        events = []
        async for event in executor.execute_parallel(tasks, simple_factory):
            events.append(event)

        results = executor.get_results()
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].result == "处理: 测试"

    @pytest.mark.asyncio
    async def test_execute_multiple_tasks_parallel(self):
        """测试并行执行多个任务"""
        bus = EventBus()
        executor = ParallelExecutor(bus, max_concurrency=3)

        tasks = [ParallelTask(task_id=f"task_{i}", content=f"内容_{i}") for i in range(3)]

        execution_order = []

        async def factory(task: ParallelTask, child_bus: EventBus) -> str:
            execution_order.append(task.task_id)
            await asyncio.sleep(0.01)
            return task.content

        async for _ in executor.execute_parallel(tasks, factory):
            pass

        results = executor.get_results()
        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_execute_with_failure(self):
        """测试任务执行失败"""
        bus = EventBus()
        executor = ParallelExecutor(bus, max_concurrency=2)

        tasks = [
            ParallelTask(task_id="success", content="ok"),
            ParallelTask(task_id="fail", content="error"),
        ]

        async def factory(task: ParallelTask, child_bus: EventBus) -> str:
            if task.content == "error":
                raise ValueError("模拟错误")
            return "成功"

        async for _ in executor.execute_parallel(tasks, factory):
            pass

        results = executor.get_results()
        assert len(results) == 2

        success_result = next(r for r in results if r.task_id == "success")
        fail_result = next(r for r in results if r.task_id == "fail")

        assert success_result.success is True
        assert fail_result.success is False
        assert "模拟错误" in fail_result.error

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """测试并发限制"""
        bus = EventBus()
        executor = ParallelExecutor(bus, max_concurrency=2)

        concurrent_count = 0
        max_concurrent = 0

        tasks = [ParallelTask(task_id=f"t{i}", content="") for i in range(5)]

        async def factory(task: ParallelTask, child_bus: EventBus) -> str:
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return "done"

        async for _ in executor.execute_parallel(tasks, factory):
            pass

        # 最大并发应该不超过限制
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_child_bus_creation(self):
        """测试子级EventBus创建"""
        parent_bus = EventBus()
        executor = ParallelExecutor(parent_bus, max_concurrency=1)

        child_bus_ids = []

        tasks = [ParallelTask(task_id="task1", content="")]

        async def factory(task: ParallelTask, child_bus: EventBus) -> str:
            child_bus_ids.append(child_bus.node_id)
            assert child_bus.parent_bus is parent_bus
            return "done"

        async for _ in executor.execute_parallel(tasks, factory):
            pass

        assert child_bus_ids == ["task1"]

    @pytest.mark.asyncio
    async def test_execute_and_synthesize(self):
        """测试执行并合成"""
        bus = EventBus()
        executor = ParallelExecutor(bus, max_concurrency=2)

        tasks = [
            ParallelTask(task_id="t1", content="a"),
            ParallelTask(task_id="t2", content="b"),
        ]

        async def factory(task: ParallelTask, child_bus: EventBus) -> str:
            return task.content.upper()

        def synthesizer(results: list[ParallelResult]) -> str:
            return ",".join(r.result for r in results if r.success)

        results, synthesis = await executor.execute_and_synthesize(tasks, factory, synthesizer)

        assert len(results) == 2
        assert "A" in synthesis
        assert "B" in synthesis

    def test_parse_sse_string_heartbeat(self):
        """测试解析心跳SSE"""
        bus = EventBus()
        executor = ParallelExecutor(bus)

        event = executor._parse_sse_string(": heartbeat")
        assert event.type == "heartbeat"

    def test_parse_sse_string_data(self):
        """测试解析数据SSE"""
        bus = EventBus()
        executor = ParallelExecutor(bus)

        sse_str = 'data: {"type": "thinking", "task_id": "t1", "agent_id": "a1", "data": "test"}'
        event = executor._parse_sse_string(sse_str)

        assert event.type == "thinking"
        assert event.task_id == "t1"
        assert event.data == "test"
