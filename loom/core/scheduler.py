from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Iterable, Set, Tuple
from pathlib import Path

from loom.interfaces.tool import BaseTool


@dataclass
class SchedulerConfig:
    max_concurrency: int = 10
    timeout_seconds: int = 120
    enable_priority: bool = True
    detect_file_conflicts: bool = True  # US4: File write conflict detection


class Scheduler:
    """智能调度器（并发/超时控制 + US4文件冲突检测）。"""

    def __init__(self, config: SchedulerConfig | None = None) -> None:
        self.config = config or SchedulerConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)
        self._file_locks: Dict[str, asyncio.Lock] = {}  # US4: Per-file locks

    async def schedule_batch(
        self, tool_calls: Iterable[Tuple[BaseTool, Dict]]
    ) -> AsyncGenerator[Any, None]:
        """US4: Enhanced scheduling with file conflict detection.

        Groups tools into:
        1. Concurrent-safe (parallel_safe=True) - executed in parallel
        2. File-writing with conflicts - serialized by file path
        3. Sequential-only (parallel_safe=False) - executed serially
        """
        concurrent_safe: list[Tuple[BaseTool, Dict]] = []
        file_writers: list[Tuple[BaseTool, Dict, str]] = []  # (tool, args, file_path)
        sequential_only: list[Tuple[BaseTool, Dict]] = []

        for tool, args in tool_calls:
            if tool.is_concurrency_safe:
                # Check if it's a file-writing tool (US4)
                file_path = self._detect_file_write(tool, args)
                if file_path and self.config.detect_file_conflicts:
                    file_writers.append((tool, args, file_path))
                else:
                    concurrent_safe.append((tool, args))
            else:
                sequential_only.append((tool, args))

        # Execute concurrent-safe tools in parallel
        if concurrent_safe:
            async for result in self._execute_concurrent(concurrent_safe):
                yield result

        # Execute file writers with conflict detection
        if file_writers:
            async for result in self._execute_file_writers(file_writers):
                yield result

        # Execute sequential tools serially
        for tool, args in sequential_only:
            yield await self._execute_single(tool, args)

    def _detect_file_write(self, tool: BaseTool, args: Dict) -> str | None:
        """US4: Detect if tool is writing to a file.

        Heuristics:
        - Tool name contains 'write', 'edit', 'save'
        - Args contain 'file_path', 'path', 'filename'

        Returns normalized file path if detected, None otherwise.
        """
        tool_name_lower = tool.name.lower()
        is_file_op = any(kw in tool_name_lower for kw in ['write', 'edit', 'save', 'create'])

        if not is_file_op:
            return None

        # Extract file path from args
        for key in ['file_path', 'path', 'filename', 'target']:
            if key in args:
                file_path = str(args[key])
                # Normalize path
                try:
                    return str(Path(file_path).resolve())
                except Exception:
                    return file_path

        return None

    async def _execute_file_writers(
        self, file_writers: list[Tuple[BaseTool, Dict, str]]
    ) -> AsyncGenerator[Any, None]:
        """US4: Execute file-writing tools with per-file serialization."""
        async def run_with_lock(tool: BaseTool, args: Dict, file_path: str) -> Any:
            # Get or create lock for this file
            if file_path not in self._file_locks:
                self._file_locks[file_path] = asyncio.Lock()

            lock = self._file_locks[file_path]

            async with lock:  # Serialize writes to same file
                async with self._semaphore:  # Respect global concurrency limit
                    return await self._execute_single(tool, args)

        tasks = [asyncio.create_task(run_with_lock(t, a, fp)) for t, a, fp in file_writers]
        for coro in asyncio.as_completed(tasks):
            yield await coro

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

