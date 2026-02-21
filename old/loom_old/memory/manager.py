"""
Memory Manager — 统一的记忆管理代理

基于三层记忆架构：
- 代理 LoomMemory 的 L1/L2/L3 API
- 支持父子节点关系（分形架构）
- 上下文存储（任务间共享的 key-value）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loom.memory.core import LoomMemory
from loom.memory.types import (
    MemoryRecord,
    MessageItem,
    WorkingMemoryEntry,
)

if TYPE_CHECKING:
    from loom.memory.store import MemoryStore
    from loom.memory.tokenizer import TokenCounter


class ContextEntry:
    """上下文条目 — 简单的 key-value 存储"""

    def __init__(self, id: str, content: Any, created_by: str):
        self.id = id
        self.content = content
        self.created_by = created_by


class MemoryManager:
    """
    统一的记忆管理代理

    职责：
    - 代理 LoomMemory 的三层 API（L1 消息 / L2 工作记忆 / L3 持久）
    - 管理上下文存储（任务间共享的 key-value）
    - 支持父子节点关系（分形架构中子节点继承父节点上下文）
    - 支持 LoomMemory 注入（解耦 Agent 和 Memory）

    Usage:
        # 方式 1: 自动创建 LoomMemory
        manager = MemoryManager(node_id="agent-1")

        # 方式 2: 注入已有的 LoomMemory
        memory = LoomMemory(node_id="agent-1", l1_token_budget=16000)
        manager = MemoryManager(node_id="agent-1", memory=memory)

        # 消息级 API
        manager.add_message("user", "Hello", token_count=5)
        messages = manager.get_context_messages()
    """

    def __init__(
        self,
        node_id: str,
        *,
        parent: MemoryManager | None = None,
        memory: LoomMemory | None = None,
        # 以下参数仅在 memory=None 时生效（自动创建 LoomMemory）
        l1_token_budget: int = 8000,
        l2_token_budget: int = 16000,
        l2_importance_threshold: float = 0.6,
        l2_ttl_seconds: int | None = 86400,
        memory_store: MemoryStore | None = None,
        token_counter: TokenCounter | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        embedding_provider: Any | None = None,
        event_bus: Any = None,
        **kwargs: Any,  # noqa: ARG002
    ):
        self.node_id = node_id
        self.parent = parent
        self._event_bus = event_bus

        # LoomMemory: 注入或自动创建
        if memory is not None:
            self.memory = memory
        else:
            self.memory = LoomMemory(
                node_id=node_id,
                l1_token_budget=l1_token_budget,
                l2_token_budget=l2_token_budget,
                l2_importance_threshold=l2_importance_threshold,
                l2_ttl_seconds=l2_ttl_seconds,
                memory_store=memory_store,
                token_counter=token_counter,
                user_id=user_id,
                session_id=session_id,
                embedding_provider=embedding_provider,
            )

        # 上下文存储（简单 key-value，用于任务间共享）
        self._context: dict[str, ContextEntry] = {}

        # 子节点列表（分形架构）
        self._children: list[MemoryManager] = []

        # 注册为父节点的子节点
        if self.parent:
            self.parent.register_child(self)

    def register_child(self, child: MemoryManager) -> None:
        """注册子节点"""
        if child not in self._children:
            self._children.append(child)

    def unregister_child(self, child: MemoryManager) -> None:
        """注销子节点"""
        if child in self._children:
            self._children.remove(child)

    # ================================================================
    # L1: Message-level API（代理 LoomMemory）
    # ================================================================

    def add_message(
        self,
        role: str,
        content: str | dict[str, Any] | None = None,
        token_count: int | None = None,
        **kwargs: Any,
    ) -> list[MessageItem]:
        """
        添加消息到 L1 滑动窗口

        Args:
            role: 消息角色
            content: 消息内容
            token_count: token 数（None 则自动计算）
            **kwargs: 传递给 MessageItem 的其他参数

        Returns:
            被驱逐的消息列表
        """
        return self.memory.add_message(role, content, token_count, **kwargs)

    def add_message_item(self, item: MessageItem) -> list[MessageItem]:
        """添加 MessageItem 到 L1"""
        return self.memory.add_message_item(item)

    def get_context_messages(self) -> list[dict[str, Any]]:
        """获取 L1 所有消息（LLM API 格式）"""
        return self.memory.get_context_messages()

    def get_message_items(self) -> list[MessageItem]:
        """获取 L1 所有 MessageItem"""
        return self.memory.get_message_items()

    # ================================================================
    # L2: Working Memory API
    # ================================================================

    def add_working_memory(self, entry: WorkingMemoryEntry) -> list[WorkingMemoryEntry]:
        """添加条目到 L2 工作记忆"""
        return self.memory.add_working_memory(entry)

    def get_working_memory(
        self,
        limit: int | None = None,
        entry_type: str | None = None,
    ) -> list[WorkingMemoryEntry]:
        """获取 L2 工作记忆条目"""
        return self.memory.get_working_memory(limit=limit, entry_type=entry_type)

    # ================================================================
    # L3: Persistent Memory API
    # ================================================================

    async def save_persistent(self, record: MemoryRecord) -> str | None:
        """保存到 L3 持久存储"""
        return await self.memory.save_persistent(record)

    async def search_persistent(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        """搜索 L3 持久记忆"""
        return await self.memory.search_persistent(query, limit)

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """跨层搜索"""
        return await self.memory.search(query, limit)

    # ================================================================
    # Session 生命周期
    # ================================================================

    async def end_session(self) -> int:
        """结束 session，持久化 L2 到 L3"""
        return await self.memory.end_session()

    async def flush_pending(self) -> int:
        """写入待持久化记录到 L3"""
        return await self.memory.flush_pending()

    # ================================================================
    # 上下文管理（任务间共享的 key-value）
    # ================================================================

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
        读取上下文（支持父节点继承）

        Args:
            context_id: 上下文唯一标识

        Returns:
            上下文条目，不存在则从父节点查找
        """
        if context_id in self._context:
            return self._context[context_id]

        if self.parent:
            return await self.parent.read(context_id)

        return None

    async def list_context(self) -> list[ContextEntry]:
        """列出所有上下文"""
        return list(self._context.values())

    # ================================================================
    # 配置
    # ================================================================

    def set_memory_store(self, store: MemoryStore) -> None:
        """设置 L3 持久存储后端"""
        self.memory.set_memory_store(store)

    # ================================================================
    # 状态与统计
    # ================================================================

    @property
    def children_count(self) -> int:
        return len(self._children)

    def get_stats(self) -> dict[str, Any]:
        """获取完整状态"""
        return {
            "node_id": self.node_id,
            "children_count": self.children_count,
            "context_count": len(self._context),
            "has_parent": self.parent is not None,
            **self.memory.get_stats(),
        }

    # ================================================================
    # Checkpoint 快照
    # ================================================================

    def export_snapshot(self) -> dict[str, Any]:
        """
        导出记忆快照（用于 Checkpoint 持久化）

        Returns:
            可序列化的快照字典
        """
        # L1: 导出消息
        l1_items = []
        for item in self.memory.get_message_items():
            l1_items.append({
                "role": item.role,
                "content": item.content,
                "token_count": item.token_count,
                "message_id": item.message_id,
                "tool_call_id": item.tool_call_id,
                "tool_name": item.tool_name,
                "tool_calls": item.tool_calls,
                "metadata": item.metadata,
            })

        # L2: 导出工作记忆
        l2_items = []
        for entry in self.memory.get_working_memory():
            l2_items.append({
                "entry_id": entry.entry_id,
                "content": entry.content,
                "entry_type": entry.entry_type.value,
                "importance": entry.importance,
                "token_count": entry.token_count,
                "tags": entry.tags,
                "source_message_ids": entry.source_message_ids,
                "session_id": entry.session_id,
                "access_count": entry.access_count,
                "metadata": entry.metadata,
            })

        # 上下文存储
        context_data = {
            k: {"id": v.id, "content": v.content, "created_by": v.created_by}
            for k, v in self._context.items()
        }

        return {
            "node_id": self.node_id,
            "l1_items": l1_items,
            "l2_items": l2_items,
            "context": context_data,
        }

    def restore_snapshot(self, snapshot: dict[str, Any]) -> None:
        """
        从快照恢复记忆

        Args:
            snapshot: export_snapshot() 返回的快照字典
        """
        if not snapshot:
            return

        from loom.memory.types import MemoryType

        # 清空当前状态
        self.memory.clear_all()
        self._context.clear()

        # 恢复 L1
        for item_data in snapshot.get("l1_items", []):
            item = MessageItem(
                role=item_data.get("role", "user"),
                content=item_data.get("content"),
                token_count=item_data.get("token_count", 0),
                message_id=item_data.get("message_id", ""),
                tool_call_id=item_data.get("tool_call_id"),
                tool_name=item_data.get("tool_name"),
                tool_calls=item_data.get("tool_calls"),
                metadata=item_data.get("metadata", {}),
            )
            self.memory.add_message_item(item)

        # 恢复 L2
        for entry_data in snapshot.get("l2_items", []):
            entry_type_str = entry_data.get("entry_type", "fact")
            try:
                entry_type = MemoryType(entry_type_str)
            except ValueError:
                entry_type = MemoryType.FACT

            entry = WorkingMemoryEntry(
                entry_id=entry_data.get("entry_id", ""),
                content=entry_data.get("content", ""),
                entry_type=entry_type,
                importance=entry_data.get("importance", 0.5),
                token_count=entry_data.get("token_count", 0),
                tags=entry_data.get("tags", []),
                source_message_ids=entry_data.get("source_message_ids", []),
                session_id=entry_data.get("session_id"),
                access_count=entry_data.get("access_count", 0),
                metadata=entry_data.get("metadata", {}),
            )
            self.memory.add_working_memory(entry)

        # 恢复上下文
        for k, v in snapshot.get("context", {}).items():
            self._context[k] = ContextEntry(
                id=v.get("id", k),
                content=v.get("content"),
                created_by=v.get("created_by", ""),
            )
