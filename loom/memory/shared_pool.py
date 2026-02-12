"""
SharedMemoryPool - 跨 Agent 共享记忆池

进程内共享存储，多个 Agent 持有同一引用进行读写。
通过 SharedPoolSource（ContextSource）自动注入 LLM 上下文。

冲突策略：
- 默认 last-writer-wins
- 可选乐观锁：传 expected_version 启用版本检查
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from loom.exceptions import LoomError

logger = logging.getLogger(__name__)


class VersionConflictError(LoomError):
    """乐观锁版本冲突"""

    def __init__(self, key: str, expected: int, actual: int):
        self.key = key
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Version conflict on '{key}': expected {expected}, actual {actual}"
        )


@dataclass
class PoolEntry:
    """共享池条目"""

    key: str
    content: Any
    version: int = 1
    created_by: str = ""
    updated_by: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class SharedMemoryPool:
    """
    跨 Agent 共享记忆池

    用法：
        pool = SharedMemoryPool()
        agent_a = Agent(..., shared_pool=pool)
        agent_b = Agent(..., shared_pool=pool)

        # Agent A 写入
        await pool.write("research_result", {"findings": ...}, writer_id="agent-a")

        # Agent B 读取
        entry = await pool.read("research_result")
    """

    def __init__(
        self,
        pool_id: str = "default",
        event_bus: Any | None = None,
    ):
        self.pool_id = pool_id
        self._store: dict[str, PoolEntry] = {}
        self._lock = asyncio.Lock()
        self._event_bus = event_bus

    async def read(self, key: str) -> PoolEntry | None:
        """读取条目"""
        async with self._lock:
            return self._store.get(key)

    async def write(
        self,
        key: str,
        content: Any,
        writer_id: str = "",
        expected_version: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PoolEntry:
        """
        写入条目

        Args:
            key: 条目键
            content: 内容
            writer_id: 写入者 ID（通常是 agent node_id）
            expected_version: 乐观锁版本号（None 表示 last-writer-wins）
            metadata: 元数据

        Raises:
            VersionConflictError: 版本冲突时抛出
        """
        async with self._lock:
            existing = self._store.get(key)

            if expected_version is not None and existing is not None:
                if existing.version != expected_version:
                    raise VersionConflictError(
                        key=key,
                        expected=expected_version,
                        actual=existing.version,
                    )

            now = time.time()
            if existing is None:
                entry = PoolEntry(
                    key=key,
                    content=content,
                    version=1,
                    created_by=writer_id,
                    updated_by=writer_id,
                    created_at=now,
                    updated_at=now,
                    metadata=metadata or {},
                )
            else:
                entry = PoolEntry(
                    key=key,
                    content=content,
                    version=existing.version + 1,
                    created_by=existing.created_by,
                    updated_by=writer_id,
                    created_at=existing.created_at,
                    updated_at=now,
                    metadata={**existing.metadata, **(metadata or {})},
                )

            self._store[key] = entry

        await self._emit_event(entry, "write")
        return entry

    async def delete(self, key: str) -> bool:
        """删除条目"""
        async with self._lock:
            entry = self._store.pop(key, None)
        if entry:
            await self._emit_event(entry, "delete")
            return True
        return False

    async def list_entries(
        self,
        prefix: str | None = None,
        limit: int = 100,
    ) -> list[PoolEntry]:
        """列出条目（按 updated_at 降序）"""
        async with self._lock:
            entries = list(self._store.values())
        if prefix:
            entries = [e for e in entries if e.key.startswith(prefix)]
        entries.sort(key=lambda e: e.updated_at, reverse=True)
        return entries[:limit]

    @property
    def size(self) -> int:
        """当前条目数"""
        return len(self._store)

    async def _emit_event(self, entry: PoolEntry, action: str) -> None:
        """通过 EventBus 发布变更事件"""
        if self._event_bus is None:
            return
        try:
            from loom.runtime import Task

            task = Task(
                taskId=f"shared_pool:{self.pool_id}:{entry.key}:{entry.version}",
                action=f"shared_pool.{action}",
                parameters={
                    "pool_id": self.pool_id,
                    "key": entry.key,
                    "version": entry.version,
                    "writer": entry.updated_by,
                },
            )
            await self._event_bus.publish(task, wait_result=False)
        except Exception:
            logger.debug("Failed to emit shared pool event", exc_info=True)
