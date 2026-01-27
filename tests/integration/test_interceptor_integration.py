"""
Interceptor Integration Tests

测试拦截器在Agent中的集成和实际使用。
"""

import pytest

from loom.orchestration.agent import Agent
from loom.protocol import Task, TaskStatus
from loom.providers.llm.mock import MockLLMProvider
from loom.runtime import (
    Interceptor,
    MetricsInterceptor,
    TimingInterceptor,
)
from loom.tools.registry import ToolRegistry


class TestInterceptorIntegration:
    """测试拦截器集成到Agent"""

    @pytest.mark.asyncio
    async def test_agent_has_interceptor_chain(self):
        """测试Agent自动拥有interceptor_chain"""
        # 1. 创建Agent
        llm = MockLLMProvider()
        tool_registry = ToolRegistry()

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            tool_registry=tool_registry,
            tools=[],
            require_done_tool=False,
        )

        # 2. 验证Agent有interceptor_chain
        assert hasattr(agent, "interceptor_chain"), "Agent should have interceptor_chain"
        assert agent.interceptor_chain is not None

        print("\n[SUCCESS] Agent has interceptor_chain")

    @pytest.mark.asyncio
    async def test_custom_interceptor_is_called(self):
        """测试自定义拦截器被调用"""
        # 1. 创建自定义拦截器
        call_log = []

        class TestInterceptor(Interceptor):
            async def before(self, task: Task) -> Task:
                call_log.append(f"before:{task.task_id}")
                return task

            async def after(self, task: Task) -> Task:
                call_log.append(f"after:{task.task_id}")
                return task

        # 2. 创建Agent并添加拦截器
        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "Task completed"},
            ]
        )
        tool_registry = ToolRegistry()

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            tool_registry=tool_registry,
            tools=[],
            require_done_tool=False,
            max_iterations=1,
        )

        agent.interceptor_chain.add(TestInterceptor())

        # 3. 执行任务
        task = Task(
            task_id="test-task-001",
            action="execute",
            parameters={"content": "Test task"},
        )

        result = await agent.execute_task(task)

        # 4. 验证拦截器被调用
        assert result.status == TaskStatus.COMPLETED
        assert len(call_log) == 2, f"Expected 2 calls, got {len(call_log)}"
        assert call_log[0] == "before:test-task-001"
        assert call_log[1] == "after:test-task-001"

        print(f"\n[SUCCESS] Custom interceptor was called: {call_log}")


class TestTimingInterceptor:
    """测试TimingInterceptor"""

    @pytest.mark.asyncio
    async def test_timing_interceptor_adds_duration(self):
        """测试TimingInterceptor添加执行时间"""
        # 1. 创建Agent并添加TimingInterceptor
        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "Task completed"},
            ]
        )
        tool_registry = ToolRegistry()

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            tool_registry=tool_registry,
            tools=[],
            require_done_tool=False,
            max_iterations=1,
        )

        agent.interceptor_chain.add(TimingInterceptor())

        # 2. 执行任务
        task = Task(
            task_id="timing-test",
            action="execute",
            parameters={"content": "Test timing"},
        )

        result = await agent.execute_task(task)

        # 3. 验证执行时间被添加到metadata
        assert result.status == TaskStatus.COMPLETED
        assert "execution_duration" in result.metadata, "Expected execution_duration in metadata"
        assert isinstance(result.metadata["execution_duration"], float)
        assert result.metadata["execution_duration"] > 0

        print(
            f"\n[SUCCESS] Timing interceptor added duration: {result.metadata['execution_duration']:.3f}s"
        )


class TestMetricsInterceptor:
    """测试MetricsInterceptor"""

    @pytest.mark.asyncio
    async def test_metrics_interceptor_collects_stats(self):
        """测试MetricsInterceptor收集统计信息"""
        # 1. 创建Agent并添加MetricsInterceptor
        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "Task 1 completed"},
                {"type": "text", "content": "Task 2 completed"},
            ]
        )
        tool_registry = ToolRegistry()

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            tool_registry=tool_registry,
            tools=[],
            require_done_tool=False,
            max_iterations=1,
        )

        metrics_interceptor = MetricsInterceptor()
        agent.interceptor_chain.add(metrics_interceptor)

        # 2. 执行多个任务
        task1 = Task(task_id="task-1", action="execute", parameters={"content": "Task 1"})
        task2 = Task(task_id="task-2", action="execute", parameters={"content": "Task 2"})

        await agent.execute_task(task1)
        await agent.execute_task(task2)

        # 3. 获取指标
        metrics = metrics_interceptor.get_metrics()

        # 4. 验证指标
        assert metrics["total_tasks"] == 2, f"Expected 2 total tasks, got {metrics['total_tasks']}"
        assert (
            metrics["completed_tasks"] == 2
        ), f"Expected 2 completed tasks, got {metrics['completed_tasks']}"
        assert (
            metrics["failed_tasks"] == 0
        ), f"Expected 0 failed tasks, got {metrics['failed_tasks']}"
        assert metrics["total_duration"] > 0, "Expected total_duration > 0"

        print(f"\n[SUCCESS] Metrics collected: {metrics}")


class TestMultipleInterceptors:
    """测试多个拦截器链式调用"""

    @pytest.mark.asyncio
    async def test_multiple_interceptors_execution_order(self):
        """测试多个拦截器的执行顺序"""
        # 1. 创建多个拦截器
        execution_order = []

        class OrderInterceptor(Interceptor):
            def __init__(self, name: str):
                self.name = name

            async def before(self, task: Task) -> Task:
                execution_order.append(f"{self.name}_before")
                return task

            async def after(self, task: Task) -> Task:
                execution_order.append(f"{self.name}_after")
                return task

        # 2. 创建Agent并添加多个拦截器
        llm = MockLLMProvider(
            responses=[
                {"type": "text", "content": "Task completed"},
            ]
        )
        tool_registry = ToolRegistry()

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            tool_registry=tool_registry,
            tools=[],
            require_done_tool=False,
            max_iterations=1,
        )

        agent.interceptor_chain.add(OrderInterceptor("A"))
        agent.interceptor_chain.add(OrderInterceptor("B"))
        agent.interceptor_chain.add(OrderInterceptor("C"))

        # 3. 执行任务
        task = Task(task_id="order-test", action="execute", parameters={"content": "Test order"})

        result = await agent.execute_task(task)

        # 4. 验证执行顺序：A_before, B_before, C_before, C_after, B_after, A_after
        expected_order = [
            "A_before",
            "B_before",
            "C_before",
            "C_after",
            "B_after",
            "A_after",
        ]

        assert result.status == TaskStatus.COMPLETED
        assert (
            execution_order == expected_order
        ), f"Expected {expected_order}, got {execution_order}"

        print(f"\n[SUCCESS] Interceptor execution order correct: {execution_order}")
