"""
LoomMemory — 三层记忆系统核心

三层模型：
- L1 (MessageWindow): 滑动窗口，存储原始 messages[]，session 级
- L2 (WorkingMemoryLayer): 工作记忆，存储 facts/decisions，session 级
- L3 (MemoryStore): 持久记忆，跨 session，用户级

数据流：
  用户/LLM 消息 → L1 (滑动窗口)
                    ↓ 驱逐
                  L2 (提取关键信息)
                    ↓ 驱逐 / session 结束
                  L3 (持久化)

设计原则：
1. Token-First — 所有层以 token 预算控制容量
2. Message-Native — L1 直接存储 LLM messages
3. 框架提供机制，应用选择策略
4. 提取/摘要逻辑可插拔（默认简单实现，可注入 LLM）
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .layers import MessageWindow, WorkingMemoryLayer
from .tokenizer import EstimateCounter, TokenCounter
from .types import (
    MemoryRecord,
    MemoryType,
    MessageItem,
    WorkingMemoryEntry,
)

if TYPE_CHECKING:
    from .store import MemoryStore
    from .vector_store import EmbeddingProvider

logger = logging.getLogger(__name__)


# =============================================================================
# 可插拔的提取/摘要函数类型
# =============================================================================

# L1→L2: 从被驱逐消息中提取工作记忆条目
# 输入: 被驱逐的消息列表, token_counter
# 输出: 提取的工作记忆条目列表
EvictionExtractor = Callable[
    [list[MessageItem], TokenCounter],
    list[WorkingMemoryEntry],
]

# L2→L3: 从被驱逐的工作记忆条目生成持久记忆记录
# 输入: 被驱逐的条目列表
# 输出: 持久记忆记录列表
PersistenceSummarizer = Callable[
    [list[WorkingMemoryEntry]],
    list[MemoryRecord],
]


def _default_extractor(
    evicted: list[MessageItem],
    token_counter: TokenCounter,
) -> list[WorkingMemoryEntry]:
    """
    默认的 L1→L2 提取器：将被驱逐消息合并为一条摘要

    从消息 metadata 中读取 importance（由 LLM <imp:X.X/> 标记注入），
    取所有消息中的最大值作为摘要的重要性。
    生产环境建议注入 LLM-based 提取器。
    """
    if not evicted:
        return []

    # 合并消息内容，收集 importance
    parts: list[str] = []
    source_ids: list[str] = []
    importances: list[float] = []
    for msg in evicted:
        source_ids.append(msg.message_id)
        msg_imp = msg.metadata.get("importance")
        if msg_imp is not None:
            importances.append(float(msg_imp))
        if msg.role == "user":
            parts.append(f"User: {msg.content}")
        elif msg.role == "assistant":
            if msg.content:
                parts.append(f"Assistant: {msg.content}")
            if msg.tool_calls:
                tool_names = [tc.get("function", {}).get("name", "?") for tc in msg.tool_calls]
                parts.append(f"Assistant called tools: {', '.join(tool_names)}")
        elif msg.role == "tool":
            content_str = str(msg.content) if msg.content else ""
            # 截断过长的工具输出
            if len(content_str) > 200:
                content_str = content_str[:200] + "..."
            parts.append(f"Tool({msg.tool_name}): {content_str}")

    if not parts:
        return []

    summary = " | ".join(parts)
    token_count = token_counter.count(summary)

    entry = WorkingMemoryEntry(
        content=summary,
        entry_type=MemoryType.SUMMARY,
        importance=max(importances) if importances else 0.5,
        token_count=token_count,
        source_message_ids=source_ids,
        session_id=evicted[0].metadata.get("session_id"),
    )
    return [entry]


def _default_summarizer(
    evicted: list[WorkingMemoryEntry],
) -> list[MemoryRecord]:
    """
    默认的 L2→L3 摘要器：直接转换为持久记录

    生产环境建议注入 LLM-based 摘要器。
    """
    records: list[MemoryRecord] = []
    for entry in evicted:
        record = MemoryRecord(
            content=entry.content,
            session_id=entry.session_id,
            importance=entry.importance,
            tags=entry.tags,
            source_entry_ids=[entry.entry_id],
        )
        records.append(record)
    return records


# =============================================================================
# LoomMemory — 三层记忆系统
# =============================================================================


class LoomMemory:
    """
    三层记忆系统

    L1 (MessageWindow): 滑动窗口 — 当前对话上下文
    L2 (WorkingMemoryLayer): 工作记忆 — session 内关键信息
    L3 (MemoryStore): 持久记忆 — 跨 session 用户级存储

    Usage:
        memory = LoomMemory(node_id="agent-1")
        memory.add_message("user", "Hello", token_count=5)
        messages = memory.get_context_messages()
    """

    def __init__(
        self,
        node_id: str,
        *,
        l1_token_budget: int = 8000,
        l2_token_budget: int = 16000,
        l2_importance_threshold: float = 0.6,
        l2_ttl_seconds: int | None = 86400,  # 默认 24h
        memory_store: MemoryStore | None = None,
        token_counter: TokenCounter | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        # 可插拔的提取/摘要逻辑
        eviction_extractor: EvictionExtractor | None = None,
        persistence_summarizer: PersistenceSummarizer | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.node_id = node_id
        self.user_id = user_id
        self.session_id = session_id
        self._token_counter = token_counter or EstimateCounter()
        self._l2_importance_threshold = l2_importance_threshold

        # L1: 滑动窗口
        self._l1 = MessageWindow(token_budget=l1_token_budget)

        # L2: 工作记忆（带 TTL）
        self._l2 = WorkingMemoryLayer(
            token_budget=l2_token_budget,
            ttl_seconds=l2_ttl_seconds,
        )

        # L3: 持久存储（可选）
        self._l3: MemoryStore | None = memory_store

        # Embedding 提供者（用于 L3 向量检索）
        self._embedding_provider: EmbeddingProvider | None = embedding_provider

        # 可插拔逻辑
        self._eviction_extractor = eviction_extractor or _default_extractor
        self._persistence_summarizer = persistence_summarizer or _default_summarizer

        # 待持久化队列（L2 驱逐产生的记录，等待异步写入 L3）
        self._pending_l3_records: list[MemoryRecord] = []

        # 连接驱逐回调
        self._l1.on_eviction(self._on_l1_eviction)
        self._l2.on_eviction(self._on_l2_eviction)

    # ================================================================
    # L1: Message-level API（核心 API）
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

        这是最常用的 API。ExecutionEngine 每次收到用户输入、
        LLM 输出、工具结果时都调用此方法。

        Args:
            role: 消息角色 ("user", "assistant", "system", "tool")
            content: 消息内容
            token_count: token 数（None 则自动计算）
            **kwargs: 传递给 MessageItem 的其他参数
                - tool_call_id: 工具调用 ID
                - tool_name: 工具名称
                - tool_calls: 工具调用列表
                - metadata: 扩展元数据

        Returns:
            被驱逐的消息列表
        """
        if token_count is None:
            text = str(content) if content else ""
            token_count = self._token_counter.count(text)

        # 注入 session_id 到 metadata
        metadata = kwargs.pop("metadata", {})
        if self.session_id:
            metadata.setdefault("session_id", self.session_id)

        item = MessageItem(
            role=role,
            content=content,
            token_count=token_count,
            metadata=metadata,
            **kwargs,
        )
        return self._l1.append(item)

    def add_message_item(self, item: MessageItem) -> list[MessageItem]:
        """
        添加 MessageItem 对象到 L1

        Args:
            item: MessageItem 实例

        Returns:
            被驱逐的消息列表
        """
        return self._l1.append(item)

    def get_context_messages(self) -> list[dict[str, Any]]:
        """
        获取当前上下文消息（LLM API 格式）

        直接返回 L1 中的所有消息，可传给 LLM API。
        这替代了旧的 ContextOrchestrator.build_context() 中
        对 L1 的处理。

        Returns:
            消息字典列表
        """
        return self._l1.get_messages()

    def get_message_items(self) -> list[MessageItem]:
        """获取 L1 中的所有 MessageItem 对象"""
        return self._l1.get_items()

    # ================================================================
    # L2: Working Memory API
    # ================================================================

    def add_working_memory(self, entry: WorkingMemoryEntry) -> list[WorkingMemoryEntry]:
        """
        添加条目到 L2 工作记忆

        Args:
            entry: 工作记忆条目

        Returns:
            被驱逐的条目列表
        """
        return self._l2.add(entry)

    def get_working_memory(
        self,
        limit: int | None = None,
        entry_type: str | None = None,
    ) -> list[WorkingMemoryEntry]:
        """
        获取 L2 工作记忆条目

        Args:
            limit: 最大返回数
            entry_type: 按类型过滤

        Returns:
            WorkingMemoryEntry 列表（按 importance 降序）
        """
        if entry_type:
            return self._l2.get_by_type(entry_type)
        return self._l2.get_entries(limit=limit)

    # ================================================================
    # L3: Persistent Memory API
    # ================================================================

    async def save_persistent(self, record: MemoryRecord) -> str | None:
        """
        保存记录到 L3 持久存储

        Args:
            record: 持久记忆记录

        Returns:
            记录 ID，如果没有 L3 存储则返回 None
        """
        if not self._l3:
            return None

        # 注入 user_id
        if self.user_id and not record.user_id:
            record.user_id = self.user_id

        # 生成 embedding（如果有 provider 且 record 没有 embedding）
        await self._ensure_embedding(record)

        return await self._l3.save(record)

    async def search_persistent(
        self,
        query: str,
        limit: int = 5,
    ) -> list[MemoryRecord]:
        """
        搜索 L3 持久记忆

        优先使用向量搜索（如果有 embedding_provider），
        失败或无结果时 fallback 到文本搜索。

        Args:
            query: 查询文本
            limit: 最大返回数

        Returns:
            匹配的记录列表
        """
        if not self._l3:
            return []

        # 优先向量搜索
        if self._embedding_provider:
            try:
                query_embedding = await self._embedding_provider.embed(query)
                results = await self._l3.query_by_vector(
                    embedding=query_embedding,
                    limit=limit,
                    user_id=self.user_id,
                )
                if results:
                    return results
            except Exception:
                logger.debug("Vector search failed, falling back to text search")

        # Fallback: 文本搜索
        return await self._l3.query_by_text(
            query=query,
            limit=limit,
            user_id=self.user_id,
        )

    async def search_persistent_by_vector(
        self,
        embedding: list[float],
        limit: int = 5,
    ) -> list[MemoryRecord]:
        """
        向量搜索 L3 持久记忆

        Args:
            embedding: 查询向量
            limit: 最大返回数

        Returns:
            匹配的记录列表
        """
        if not self._l3:
            return []

        return await self._l3.query_by_vector(
            embedding=embedding,
            limit=limit,
            user_id=self.user_id,
        )

    # ================================================================
    # Embedding 辅助
    # ================================================================

    async def _ensure_embedding(self, record: MemoryRecord) -> None:
        """为 MemoryRecord 生成 embedding（如果有 provider 且尚无 embedding）"""
        if self._embedding_provider and record.embedding is None and record.content:
            try:
                record.embedding = await self._embedding_provider.embed(record.content)
            except Exception:
                logger.debug("Failed to generate embedding for record %s", record.record_id)

    # ================================================================
    # 跨层搜索
    # ================================================================

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        跨层搜索（L1 文本匹配 + L2 文本匹配 + L3 持久搜索）

        Args:
            query: 查询文本
            limit: 每层最大返回数

        Returns:
            搜索结果列表，每个结果包含 tier, content, importance
        """
        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        # L1: 简单文本匹配
        for item in self._l1.get_items():
            content_str = str(item.content) if item.content else ""
            if query_lower in content_str.lower():
                results.append({
                    "tier": "L1",
                    "content": content_str,
                    "role": item.role,
                    "importance": 0.5,
                })

        # L2: 文本匹配
        for entry in self._l2.get_entries():
            if query_lower in entry.content.lower() or any(
                query_lower in tag.lower() for tag in entry.tags
            ):
                results.append({
                    "tier": "L2",
                    "content": entry.content,
                    "importance": entry.importance,
                })

        # L3: 持久搜索
        if self._l3:
            records = await self._l3.query_by_text(
                query=query, limit=limit, user_id=self.user_id,
            )
            for record in records:
                results.append({
                    "tier": "L3",
                    "content": record.content,
                    "importance": record.importance,
                })

        return results[:limit * 3]

    # ================================================================
    # 驱逐回调（L1→L2→L3 管线）
    # ================================================================

    def _on_l1_eviction(self, evicted: list[MessageItem]) -> None:
        """
        L1 驱逐回调：从被驱逐消息中提取关键信息 → L2

        重要性门控：只有 importance >= threshold 的条目才进入 L2。
        """
        if not evicted:
            return

        entries = self._eviction_extractor(evicted, self._token_counter)
        admitted = 0
        for entry in entries:
            if self.session_id and not entry.session_id:
                entry.session_id = self.session_id
            if entry.importance < self._l2_importance_threshold:
                logger.debug(
                    "L1→L2 gate: dropped entry (importance=%.2f < threshold=%.2f)",
                    entry.importance, self._l2_importance_threshold,
                )
                continue
            self._l2.add(entry)
            admitted += 1

        logger.debug(
            "L1→L2: evicted %d messages, extracted %d entries, admitted %d",
            len(evicted), len(entries), admitted,
        )

    def _on_l2_eviction(self, evicted: list[WorkingMemoryEntry]) -> None:
        """
        L2 驱逐回调：将被驱逐条目转换为持久记录 → L3 待写入队列

        使用可插拔的 persistence_summarizer。
        实际写入 L3 需要异步操作，先放入待写入队列，
        由 flush_pending() 或 end_session() 触发。
        """
        if not evicted:
            return

        records = self._persistence_summarizer(evicted)
        for record in records:
            if self.user_id and not record.user_id:
                record.user_id = self.user_id
            if self.session_id and not record.session_id:
                record.session_id = self.session_id
            self._pending_l3_records.append(record)

        logger.debug(
            "L2→L3(pending): evicted %d entries, queued %d records",
            len(evicted),
            len(records),
        )

    async def flush_pending(self) -> int:
        """
        将待写入队列中的记录写入 L3

        Returns:
            成功写入的记录数
        """
        if not self._l3 or not self._pending_l3_records:
            return 0

        count = 0
        while self._pending_l3_records:
            record = self._pending_l3_records.pop(0)
            await self._ensure_embedding(record)
            try:
                await self._l3.save(record)
                count += 1
            except Exception:
                logger.warning("Failed to save record to L3: %s", record.record_id)

        return count

    # ================================================================
    # Session 生命周期
    # ================================================================

    async def end_session(self) -> int:
        """
        结束 session：将 L2 高重要性内容持久化到 L3

        低于 importance threshold 的内容直接丢弃。

        Returns:
            持久化的记录数
        """
        threshold = self._l2_importance_threshold

        # 1. 将 L2 中高重要性条目转换为 L3 记录
        all_entries = self._l2.get_entries()
        qualified_entries = [e for e in all_entries if e.importance >= threshold]
        if qualified_entries:
            records = self._persistence_summarizer(qualified_entries)
            for record in records:
                if self.user_id and not record.user_id:
                    record.user_id = self.user_id
                if self.session_id and not record.session_id:
                    record.session_id = self.session_id
                self._pending_l3_records.append(record)

        # 2. 如果 L2 无合格条目但 L1 中有消息，从 L1 提取并过滤
        if not qualified_entries:
            l1_messages = self._l1.get_items()
            if l1_messages:
                extracted_entries = self._eviction_extractor(l1_messages, self._token_counter)
                qualified_extracted = [e for e in extracted_entries if e.importance >= threshold]
                if qualified_extracted:
                    records = self._persistence_summarizer(qualified_extracted)
                    for record in records:
                        if self.user_id and not record.user_id:
                            record.user_id = self.user_id
                        if self.session_id and not record.session_id:
                            record.session_id = self.session_id
                        self._pending_l3_records.append(record)

        # 3. 写入 L3
        count = await self.flush_pending()

        # 4. 清空 L1 和 L2
        self._l1.clear()
        self._l2.clear()

        logger.info("Session ended: persisted %d records to L3", count)
        return count

    # ================================================================
    # 配置与状态
    # ================================================================

    def set_memory_store(self, store: MemoryStore) -> None:
        """设置 L3 持久存储后端"""
        self._l3 = store

    def set_eviction_extractor(self, extractor: EvictionExtractor) -> None:
        """设置 L1→L2 提取器"""
        self._eviction_extractor = extractor

    def set_embedding_provider(self, provider: EmbeddingProvider) -> None:
        """设置 embedding 提供者（用于 L3 向量检索）"""
        self._embedding_provider = provider

    def set_persistence_summarizer(self, summarizer: PersistenceSummarizer) -> None:
        """设置 L2→L3 摘要器"""
        self._persistence_summarizer = summarizer

    @property
    def l1(self) -> MessageWindow:
        """直接访问 L1 层（高级用法）"""
        return self._l1

    @property
    def l2(self) -> WorkingMemoryLayer:
        """直接访问 L2 层（高级用法）"""
        return self._l2

    @property
    def l3(self) -> MemoryStore | None:
        """直接访问 L3 层（高级用法）"""
        return self._l3

    @property
    def token_counter(self) -> TokenCounter:
        return self._token_counter

    def get_stats(self) -> dict[str, Any]:
        """
        获取记忆系统统计信息

        Returns:
            统计信息字典
        """
        return {
            "node_id": self.node_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            # L1
            "l1_token_usage": self._l1.token_usage(),
            "l1_token_budget": self._l1.token_budget,
            "l1_message_count": self._l1.size(),
            # L2
            "l2_token_usage": self._l2.token_usage(),
            "l2_token_budget": self._l2.token_budget,
            "l2_entry_count": self._l2.size(),
            # L3
            "l3_enabled": self._l3 is not None,
            "l3_pending_count": len(self._pending_l3_records),
        }

    def clear_all(self) -> None:
        """清空所有层级（慎用）"""
        self._l1.clear()
        self._l2.clear()
        self._pending_l3_records.clear()

    def close(self) -> None:
        """关闭 LoomMemory，清理资源"""
        self.clear_all()
