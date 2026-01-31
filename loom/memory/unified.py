"""
Unified Memory Manager - 统一内存管理器

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


class UnifiedMemoryManager:
    """统一内存管理器 - 整合 LoomMemory（L1-L4）和 FractalMemory（作用域）"""

    def __init__(
        self,
        node_id: str,
        parent: Optional["UnifiedMemoryManager"] = None,
        max_l1_size: int = 50,
        max_l2_size: int = 100,
        max_l3_size: int = 500,
    ):
        self.node_id = node_id
        self.parent = parent

        # 底层存储：LoomMemory 管理 L1-L4
        self._loom_memory = LoomMemory(
            node_id=node_id,
            max_l1_size=max_l1_size,
            max_l2_size=max_l2_size,
            max_l3_size=max_l3_size,
        )

        # 作用域索引
        self._memory_by_scope: dict[MemoryScope, dict[str, MemoryEntry]] = {
            scope: {} for scope in MemoryScope
        }

    async def write(
        self, entry_id: str, content: Any, scope: MemoryScope = MemoryScope.LOCAL
    ) -> MemoryEntry:
        """写入记忆（TODO: Task 2）"""
        raise NotImplementedError

    async def read(
        self, entry_id: str, search_scopes: list[MemoryScope] | None = None
    ) -> MemoryEntry | None:
        """读取记忆（TODO: Task 3）"""
        raise NotImplementedError

    # LoomMemory 兼容接口
    def add_task(self, task: Task) -> None:
        self._loom_memory.add_task(task)

    def get_l1_tasks(self, limit: int = 10, session_id: str | None = None) -> list[Task]:
        return self._loom_memory.get_l1_tasks(limit=limit, session_id=session_id)
