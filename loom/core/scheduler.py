from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Iterable, Tuple

from loom.interfaces.tool import BaseTool


@dataclass
class SchedulerConfig:
    max_concurrency: int = 10
    timeout_seconds: int = 120
    enable_priority: bool = True


class Scheduler:
    """智能调度器（并发/超时控制）。"""

    def __init__(self, config: SchedulerConfig | None = None) -> None:
        self.config = config or SchedulerConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)

    async def schedule_batch(
        self, tool_calls: Iterable[Tuple[BaseTool, Dict]]
    ) -> AsyncGenerator[Any, None]:
        concurrent_safe: list[Tuple[BaseTool, Dict]] = []
        sequential_only: list[Tuple[BaseTool, Dict]] = []
        for tool, args in tool_calls:
            (concurrent_safe if tool.is_concurrency_safe else sequential_only).append((tool, args))

        if concurrent_safe:
            async for result in self._execute_concurrent(concurrent_safe):
                yield result

        for tool, args in sequential_only:
            yield await self._execute_single(tool, args)

    async def _execute_concurrent(
        self, tool_calls: Iterable[Tuple[BaseTool, Dict]]
    ) -> AsyncGenerator[Any, None]:
        async def run(tool: BaseTool, args: Dict) -> Any:
            async with self._semaphore:
                return await self._execute_single(tool, args)

        tasks = [asyncio.create_task(run(t, a)) for t, a in tool_calls]
        for coro in asyncio.as_completed(tasks):
            yield await coro

    async def _execute_single(self, tool: BaseTool, args: Dict) -> Any:
        return await asyncio.wait_for(tool.run(**args), timeout=self.config.timeout_seconds)

