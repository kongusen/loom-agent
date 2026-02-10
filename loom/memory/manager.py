"""
Memory Manager - 内存管理器

基于 Session-EventBus 架构：
- L1/L2: Session 私有，通过 Session 访问
- L3/L4: Agent 级别，通过 ContextController 访问
- 上下文存储：简单的 key-value 存储，用于任务间共享
"""

from typing import Any, Optional

from loom.config.memory import MemoryStrategyType
from loom.memory.core import LoomMemory
from loom.runtime import Task


class ContextEntry:
    """上下文条目 - 简单的 key-value 存储"""

    def __init__(self, id: str, content: Any, created_by: str):
        self.id = id
        self.content = content
        self.created_by = created_by


class MemoryManager:
    """
    内存管理器 - 基于 Session-EventBus 架构

    职责：
    - 管理上下文存储（用于任务间共享）
    - 代理 LoomMemory 的 L1-L4 任务管理
    - 支持父子节点关系（用于分形架构）
    """

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

        # 上下文存储（简单 key-value）
        self._context: dict[str, ContextEntry] = {}

        # 子节点列表（用于分形架构）
        self._children: list[MemoryManager] = []

        # 如果有父节点，注册为子节点
        if self.parent:
            self.parent.register_child(self)

    def register_child(self, child: "MemoryManager") -> None:
        """注册子节点"""
        if child not in self._children:
            self._children.append(child)

    def unregister_child(self, child: "MemoryManager") -> None:
        """注销子节点"""
        if child in self._children:
            self._children.remove(child)

    # ==================== 上下文管理 ====================

    async def add_context(self, context_id: str, content: Any) -> ContextEntry:
        """
        添加上下文（用于任务间共享）

        Args:
            context_id: 上下文唯一标识
            content: 上下文内容

        Returns:
            创建的上下文条目
        """
        entry = ContextEntry(id=context_id, content=content, created_by=self.node_id)
        self._context[context_id] = entry
        return entry

    async def read(self, context_id: str) -> ContextEntry | None:
        """
        读取上下文

        Args:
            context_id: 上下文唯一标识

        Returns:
            上下文条目，如果不存在则从父节点查找
        """
        # 先查本地
        if context_id in self._context:
            return self._context[context_id]

        # 再查父节点（继承机制）
        if self.parent:
            return await self.parent.read(context_id)

        return None

    async def list_context(self) -> list[ContextEntry]:
        """列出所有上下文"""
        return list(self._context.values())

    # ==================== LoomMemory 代理接口 ====================

    def add_task(self, task: Task) -> None:
        """添加任务到 L1"""
        self._loom_memory.add_task(task)

    def get_l1_tasks(self, limit: int = 10, session_id: str | None = None) -> list[Task]:
        """获取 L1 任务"""
        return self._loom_memory.get_l1_tasks(limit=limit, session_id=session_id)

    def get_l2_tasks(self, limit: int = 10, session_id: str | None = None) -> list[Task]:
        """获取 L2 重要任务"""
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

    # ==================== L4 配置 ====================

    def set_vector_store(self, store: Any) -> None:
        """设置 L4 向量存储"""
        self._loom_memory.set_vector_store(store)

    def set_embedding_provider(self, provider: Any) -> None:
        """设置嵌入提供者"""
        self._loom_memory.set_embedding_provider(provider)

    # ==================== 状态检查 ====================

    @property
    def children_count(self) -> int:
        """子 MemoryManager 数量"""
        return len(self._children)

    def get_context_stats(self) -> dict[str, int]:
        """获取上下文统计"""
        return {"context_count": len(self._context)}

    def get_manager_state(self) -> dict[str, Any]:
        """获取 MemoryManager 完整状态"""
        return {
            "node_id": self.node_id,
            "children_count": self.children_count,
            "context_stats": self.get_context_stats(),
            "has_parent": self.parent is not None,
            "loom_memory_stats": self._loom_memory.get_stats(),
        }
