"""
Memory Manager - 内存管理器

整合 FractalMemory 和 LoomMemory 的职责：
- L1-L4 分层存储（来自 LoomMemory）
- LOCAL/SHARED/INHERITED/GLOBAL 作用域（来自 FractalMemory）
- 统一的读写接口
- 父子节点关系管理
"""

from typing import Any, Optional

from loom.config.memory import MemoryStrategyType
from loom.fractal.memory import MemoryEntry, MemoryScope
from loom.memory.core import LoomMemory
from loom.runtime import Task


class MemoryManager:
    """内存管理器 - 整合 LoomMemory（L1-L4）和 FractalMemory（作用域）"""

    def __init__(
        self,
        node_id: str,
        parent: Optional["MemoryManager"] = None,
        # Token-First: 使用 token 预算而非条目数
        l1_token_budget: int = 8000,
        l2_token_budget: int = 16000,
        l3_token_budget: int = 32000,
        l4_token_budget: int = 100000,
        event_bus: Any = None,
        # MemoryConfig support
        strategy: Any = None,
        enable_auto_migration: bool = True,
        enable_compression: bool = True,
        l1_retention_hours: int | None = None,
        l2_retention_hours: int | None = None,
        l3_retention_hours: int | None = None,
        l4_retention_hours: int | None = None,
        l1_promote_threshold: int = 3,
        l3_promote_threshold: int = 3,
        l2_auto_compress: bool = True,
        l3_auto_compress: bool = True,
        importance_threshold: float = 0.6,
    ):
        self.node_id = node_id
        self.parent = parent

        # 底层存储：LoomMemory 管理 L1-L4（Token-First Design）
        self._loom_memory = LoomMemory(
            node_id=node_id,
            l1_token_budget=l1_token_budget,
            l2_token_budget=l2_token_budget,
            l3_token_budget=l3_token_budget,
            l4_token_budget=l4_token_budget,
            event_bus=event_bus,
            strategy=(
                strategy
                if strategy is not None
                else MemoryStrategyType.IMPORTANCE_BASED
            ),
            enable_auto_migration=enable_auto_migration,
            enable_compression=enable_compression,
            l1_retention_hours=l1_retention_hours,
            l2_retention_hours=l2_retention_hours,
            l3_retention_hours=l3_retention_hours,
            l4_retention_hours=l4_retention_hours,
            l1_promote_threshold=l1_promote_threshold,
            l3_promote_threshold=l3_promote_threshold,
            l2_auto_compress=l2_auto_compress,
            l3_auto_compress=l3_auto_compress,
            importance_threshold=importance_threshold,
        )

        # 作用域索引
        self._memory_by_scope: dict[MemoryScope, dict[str, MemoryEntry]] = {
            scope: {} for scope in MemoryScope
        }

        # 子节点列表（用于 propagate_down）
        self._children: list[MemoryManager] = []

        # 如果有父节点，注册为子节点
        if self.parent:
            self.parent.register_child(self)

    def register_child(self, child: "MemoryManager") -> None:
        """注册子节点（用于 propagate_down）"""
        if child not in self._children:
            self._children.append(child)

    def unregister_child(self, child: "MemoryManager") -> None:
        """注销子节点"""
        if child in self._children:
            self._children.remove(child)

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
            entry = existing
        else:
            # 创建新记忆条目
            entry = MemoryEntry(
                id=entry_id,
                content=content,
                scope=scope,
                created_by=self.node_id,
                updated_by=self.node_id,
            )
            self._memory_by_scope[scope][entry_id] = entry

        # 实现向上传播（propagate_up）
        if policy.propagate_up and self.parent:
            await self.parent.write(entry_id, content, scope)

        # 实现向下传播（propagate_down）
        # 注意：向下传播时使用 INHERITED 作用域，子节点只读
        if policy.propagate_down and self._children:
            for child in self._children:
                # 使子节点的 INHERITED 缓存失效（通过删除旧缓存）
                if entry_id in child._memory_by_scope[MemoryScope.INHERITED]:
                    del child._memory_by_scope[MemoryScope.INHERITED][entry_id]

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
            if scope == MemoryScope.INHERITED:
                # INHERITED 需要特殊处理：检查缓存是否过期
                continue
            if entry_id in self._memory_by_scope[scope]:
                return self._memory_by_scope[scope][entry_id]

        # 处理 INHERITED 作用域（带缓存失效检查）
        if MemoryScope.INHERITED in search_scopes and self.parent:
            cached = self._memory_by_scope[MemoryScope.INHERITED].get(entry_id)

            # 从父节点获取最新版本
            parent_entry = await self.parent.read(
                entry_id,
                search_scopes=[MemoryScope.SHARED, MemoryScope.GLOBAL, MemoryScope.INHERITED],
            )

            if parent_entry:
                # 检查缓存是否过期
                if cached and cached.parent_version == parent_entry.version:
                    return cached  # 缓存有效，直接返回

                # 缓存过期或不存在，创建新的缓存
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
        """
        列出指定作用域的所有记忆

        对于 INHERITED 作用域，会从父节点的 SHARED/GLOBAL 作用域获取并缓存
        """
        # 对于 INHERITED 作用域，需要从父节点获取
        if scope == MemoryScope.INHERITED and self.parent:
            # 获取父节点的 SHARED 和 GLOBAL 记忆
            parent_shared = await self.parent.list_by_scope(MemoryScope.SHARED)
            parent_global = await self.parent.list_by_scope(MemoryScope.GLOBAL)

            # 合并父节点的记忆
            parent_entries = parent_shared + parent_global

            # 缓存到本地 INHERITED 作用域（避免重复查询）
            for parent_entry in parent_entries:
                if parent_entry.id not in self._memory_by_scope[MemoryScope.INHERITED]:
                    inherited_entry = MemoryEntry(
                        id=parent_entry.id,
                        content=parent_entry.content,
                        scope=MemoryScope.INHERITED,
                        version=parent_entry.version,
                        created_by=parent_entry.created_by,
                        updated_by=parent_entry.updated_by,
                        parent_version=parent_entry.version,
                    )
                    self._memory_by_scope[MemoryScope.INHERITED][parent_entry.id] = inherited_entry

        return list(self._memory_by_scope[scope].values())

    # LoomMemory 兼容接口
    def add_task(self, task: Task) -> None:
        self._loom_memory.add_task(task)

    def get_l1_tasks(self, limit: int = 10, session_id: str | None = None) -> list[Task]:
        return self._loom_memory.get_l1_tasks(limit=limit, session_id=session_id)

    def get_l2_tasks(self, limit: int = 10, session_id: str | None = None) -> list[Task]:
        """获取 L2 重要任务（兼容 LoomMemory 接口）"""
        return self._loom_memory.get_l2_tasks(limit=limit, session_id=session_id)

    def get_task(self, task_id: str) -> Task | None:
        """根据 ID 获取任务"""
        return self._loom_memory.get_task(task_id)

    def promote_tasks(self) -> None:
        """触发任务提升（L1→L2→L3→L4）"""
        self._loom_memory.promote_tasks()

    async def promote_tasks_async(self) -> None:
        """异步触发任务提升"""
        await self._loom_memory.promote_tasks_async()

    # L4 配置透传
    def set_vector_store(self, store: Any) -> None:
        """设置 L4 向量存储"""
        self._loom_memory.set_vector_store(store)

    def set_embedding_provider(self, provider: Any) -> None:
        """设置嵌入提供者"""
        self._loom_memory.set_embedding_provider(provider)

    # ==================== 状态检查方法 ====================

    @property
    def children_count(self) -> int:
        """子 MemoryManager 数量"""
        return len(self._children)

    def get_scope_stats(self) -> dict[str, int]:
        """获取各作用域的记忆条目统计"""
        return {scope.value: len(entries) for scope, entries in self._memory_by_scope.items()}

    def get_manager_state(self) -> dict[str, Any]:
        """获取 MemoryManager 完整状态"""
        return {
            "node_id": self.node_id,
            "children_count": self.children_count,
            "scope_stats": self.get_scope_stats(),
            "has_parent": self.parent is not None,
            "loom_memory_stats": self._loom_memory.get_stats(),
        }
