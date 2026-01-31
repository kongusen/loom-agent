"""
Memory Manager - 内存管理器

整合 FractalMemory 和 LoomMemory 的职责：
- L1-L4 分层存储（来自 LoomMemory）
- LOCAL/SHARED/INHERITED/GLOBAL 作用域（来自 FractalMemory）
- 统一的读写接口
- 父子节点关系管理
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from loom.fractal.memory import MemoryScope, MemoryEntry
from loom.memory.core import LoomMemory
from loom.protocol import Task


class MemoryManager:
    """内存管理器 - 整合 LoomMemory（L1-L4）和 FractalMemory（作用域）"""

    def __init__(
        self,
        node_id: str,
        parent: Optional["MemoryManager"] = None,
        max_l1_size: int = 50,
        max_l2_size: int = 100,
        max_l3_size: int = 500,
        event_bus: Any = None,
    ):
        self.node_id = node_id
        self.parent = parent

        # 底层存储：LoomMemory 管理 L1-L4
        self._loom_memory = LoomMemory(
            node_id=node_id,
            max_l1_size=max_l1_size,
            max_l2_size=max_l2_size,
            max_l3_size=max_l3_size,
            event_bus=event_bus,
        )

        # 作用域索引
        self._memory_by_scope: dict[MemoryScope, dict[str, MemoryEntry]] = {
            scope: {} for scope in MemoryScope
        }

    async def write(
        self, entry_id: str, content: Any, scope: MemoryScope = MemoryScope.LOCAL
    ) -> MemoryEntry:
        """
        写入记忆到指定作用域

        Args:
            entry_id: 记忆唯一标识
            content: 记忆内容
            scope: 作用域（LOCAL/SHARED/INHERITED/GLOBAL）

        Returns:
            创建的记忆条目
        """
        from loom.fractal.memory import ACCESS_POLICIES

        # 检查写权限
        policy = ACCESS_POLICIES[scope]
        if not policy.writable:
            raise PermissionError(f"Scope {scope.value} is read-only")

        # 如果已存在，更新版本
        existing = self._memory_by_scope[scope].get(entry_id)
        if existing:
            existing.version += 1
            existing.content = content
            existing.updated_by = self.node_id
            return existing

        # 创建新记忆条目
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            scope=scope,
            created_by=self.node_id,
            updated_by=self.node_id,
        )

        self._memory_by_scope[scope][entry_id] = entry
        return entry

    async def read(
        self, entry_id: str, search_scopes: list[MemoryScope] | None = None
    ) -> MemoryEntry | None:
        """
        读取记忆（支持作用域搜索和父节点继承）

        Args:
            entry_id: 记忆唯一标识
            search_scopes: 搜索的作用域列表（None = 搜索所有）

        Returns:
            记忆条目，如果不存在返回 None
        """
        if search_scopes is None:
            search_scopes = list(MemoryScope)

        # 按优先级搜索本地作用域：LOCAL > SHARED > INHERITED > GLOBAL
        for scope in search_scopes:
            if entry_id in self._memory_by_scope[scope]:
                return self._memory_by_scope[scope][entry_id]

        # 如果是 INHERITED 作用域，尝试从父节点读取
        if MemoryScope.INHERITED in search_scopes and self.parent:
            parent_entry = await self.parent.read(
                entry_id,
                search_scopes=[MemoryScope.SHARED, MemoryScope.GLOBAL, MemoryScope.INHERITED],
            )
            if parent_entry:
                # 创建只读副本并缓存
                inherited_entry = MemoryEntry(
                    id=parent_entry.id,
                    content=parent_entry.content,
                    scope=MemoryScope.INHERITED,
                    version=parent_entry.version,
                    created_by=parent_entry.created_by,
                    updated_by=parent_entry.updated_by,
                    parent_version=parent_entry.version,
                )
                self._memory_by_scope[MemoryScope.INHERITED][entry_id] = inherited_entry
                return inherited_entry

        return None

    async def list_by_scope(self, scope: MemoryScope) -> list[MemoryEntry]:
        """列出指定作用域的所有记忆"""
        return list(self._memory_by_scope[scope].values())

    # LoomMemory 兼容接口
    def add_task(self, task: Task) -> None:
        self._loom_memory.add_task(task)

    def get_l1_tasks(self, limit: int = 10, session_id: str | None = None) -> list[Task]:
        return self._loom_memory.get_l1_tasks(limit=limit, session_id=session_id)

    def get_l2_tasks(self, limit: int = 10, session_id: str | None = None) -> list[Task]:
        """获取 L2 重要任务（兼容 LoomMemory 接口）"""
        return self._loom_memory.get_l2_tasks(limit=limit, session_id=session_id)

    def promote_tasks(self) -> None:
        """触发任务提升（L1→L2→L3→L4）"""
        self._loom_memory.promote_tasks()

    async def promote_tasks_async(self) -> None:
        """异步触发任务提升"""
        await self._loom_memory.promote_tasks_async()
