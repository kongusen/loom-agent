"""
Parallel Executor - 并行执行器

基于公理A3（分形自相似）：
提供框架级别的多Agent并行执行能力，自动处理SSE事件汇聚。

设计原则：
1. 透明性 - 自动为每个任务创建子级EventBus
2. 可配置 - 支持并发控制和输出策略
3. 流式 - 实时返回SSE事件流
"""

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

from loom.events.event_bus import EventBus
from loom.events.output_collector import OutputCollector, OutputStrategy, SSEEvent

if TYPE_CHECKING:
    pass

T = TypeVar("T")


@dataclass
class ParallelTask:
    """
    并行任务定义

    用于描述并行执行中的单个任务。
    """

    task_id: str  # 任务唯一标识
    content: str  # 任务内容（传递给Agent的输入）
    metadata: dict[str, Any] = field(default_factory=dict)  # 额外元数据


@dataclass
class ParallelResult:
    """
    并行执行结果

    包含单个任务的执行结果和状态信息。
    """

    task_id: str
    result: Any
    success: bool
    error: str | None = None
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# Agent工厂函数类型：接收任务和子级EventBus，返回执行结果
AgentFactory = Callable[[ParallelTask, EventBus], Any]


class ParallelExecutor:
    """
    分形并行执行器

    提供框架级别的并行Agent执行支持，自动处理：
    1. 子级EventBus创建和事件汇聚
    2. 并发控制
    3. SSE流式输出
    4. 结果收集和合成

    使用示例:
    ```python
    executor = ParallelExecutor(
        event_bus=shared_bus,
        max_concurrency=5,
        output_strategy=OutputStrategy.REALTIME,
    )

    async def agent_factory(task: ParallelTask, child_bus: EventBus) -> str:
        agent = Agent.create(llm, event_bus=child_bus, node_id=f"{task.task_id}:Worker")
        return await agent.run(task.content)

    async for event in executor.execute_parallel(tasks, agent_factory):
        yield event.to_sse()
    ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        max_concurrency: int = 5,
        output_strategy: OutputStrategy = OutputStrategy.REALTIME,
    ):
        """
        初始化并行执行器

        Args:
            event_bus: 父级事件总线（子任务事件会汇聚到此）
            max_concurrency: 最大并发数
            output_strategy: 输出策略
        """
        self.event_bus = event_bus
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.output_strategy = output_strategy
        self._collector: OutputCollector | None = None
        self._results: list[ParallelResult] = []

    async def execute_parallel(
        self,
        tasks: list[ParallelTask],
        agent_factory: AgentFactory,
    ) -> AsyncIterator[SSEEvent]:
        """
        并行执行任务，流式返回SSE事件

        Args:
            tasks: 并行任务列表
            agent_factory: Agent工厂函数，接收(task, child_bus)返回执行结果

        Yields:
            SSEEvent事件
        """
        # 创建输出收集器
        self._collector = OutputCollector(
            self.event_bus,
            strategy=self.output_strategy,
        )
        self._collector.start()
        self._results = []

        # 创建执行任务
        execution_tasks = [
            asyncio.create_task(self._execute_single(task, agent_factory)) for task in tasks
        ]

        # 并行执行和流式输出
        # 创建一个任务来等待所有执行完成
        # 创建一个任务来等待所有执行完成
        async def wait_for_completion() -> None:
            try:
                await asyncio.gather(*execution_tasks, return_exceptions=True)
            finally:
                # 所有任务完成后关闭收集器
                if self._collector:
                    await self._collector.close()

        completion_task = asyncio.create_task(wait_for_completion())

        # 流式输出事件
        try:
            async for sse_str in self._collector.stream(timeout=30.0):
                # 解析SSE字符串回SSEEvent（简化处理）
                yield self._parse_sse_string(sse_str)
        except Exception:
            pass  # 流结束

        # 确保所有任务完成
        await completion_task

    async def _execute_single(
        self,
        task: ParallelTask,
        agent_factory: AgentFactory,
    ) -> ParallelResult:
        """
        执行单个任务

        Args:
            task: 并行任务
            agent_factory: Agent工厂函数

        Returns:
            执行结果
        """
        async with self.semaphore:
            start_time = time.time()
            child_bus = self.event_bus.create_child_bus(task.task_id)

            try:
                result = await agent_factory(task, child_bus)
                parallel_result = ParallelResult(
                    task_id=task.task_id,
                    result=result,
                    success=True,
                    duration=time.time() - start_time,
                    metadata=task.metadata,
                )
            except Exception as e:
                parallel_result = ParallelResult(
                    task_id=task.task_id,
                    result=None,
                    success=False,
                    error=str(e),
                    duration=time.time() - start_time,
                    metadata=task.metadata,
                )

            self._results.append(parallel_result)
            return parallel_result

    def _parse_sse_string(self, sse_str: str) -> SSEEvent:
        """
        解析SSE字符串为SSEEvent

        Args:
            sse_str: SSE格式字符串

        Returns:
            SSEEvent实例
        """
        import json

        # 处理心跳
        if sse_str.startswith(":"):
            return SSEEvent(
                type="heartbeat",
                task_id="system",
                agent_id="executor",
                data="",
            )

        # 解析 data: {...}
        if sse_str.startswith("data:"):
            json_str = sse_str[5:].strip()
            try:
                data = json.loads(json_str)
                return SSEEvent(
                    type=data.get("type", "unknown"),
                    task_id=data.get("task_id", "unknown"),
                    agent_id=data.get("agent_id", "unknown"),
                    data=data.get("data", ""),
                    tool_calls=data.get("tool_calls", []),
                    timestamp=data.get("timestamp", time.time()),
                    metadata=data.get("metadata", {}),
                )
            except json.JSONDecodeError:
                pass

        return SSEEvent(
            type="raw",
            task_id="unknown",
            agent_id="unknown",
            data=sse_str,
        )

    def get_results(self) -> list[ParallelResult]:
        """
        获取所有执行结果

        Returns:
            并行执行结果列表
        """
        return self._results

    async def execute_and_synthesize(
        self,
        tasks: list[ParallelTask],
        agent_factory: AgentFactory,
        synthesizer: Callable[[list[ParallelResult]], Any] | None = None,
    ) -> tuple[list[ParallelResult], Any]:
        """
        执行并合成结果（非流式）

        适用于不需要实时SSE输出，但需要最终合成的场景。

        Args:
            tasks: 并行任务列表
            agent_factory: Agent工厂函数
            synthesizer: 可选的结果合成函数

        Returns:
            (执行结果列表, 合成结果)
        """
        # 先收集所有事件（忽略）
        async for _ in self.execute_parallel(tasks, agent_factory):
            pass

        results = self.get_results()

        # 合成结果
        synthesis = None
        if synthesizer:
            synthesis = (
                await synthesizer(results)
                if asyncio.iscoroutinefunction(synthesizer)
                else synthesizer(results)
            )

        return results, synthesis
