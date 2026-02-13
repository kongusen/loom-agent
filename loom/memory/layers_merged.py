"""
Memory Layer Implementations — 三层架构

L1: MessageWindow — 滑动窗口，存储原始 messages[]
L2: WorkingMemoryLayer — 工作记忆，存储 facts/decisions

设计原则：
1. Token-First — 所有容量以 token 预算控制
2. Message-Native — L1 直接存储 LLM messages
3. Paired Eviction — tool_call 和 tool_result 配对驱逐
"""

from __future__ import annotations

import heapq
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from .types import MessageItem, WorkingMemoryEntry

# =============================================================================
# L1: MessageWindow — 滑动窗口
# =============================================================================


class MessageWindow:
    """
    L1 滑动窗口 — 存储原始 LLM messages

    直接替代 ExecutionEngine 中的 accumulated_messages。
    L1 = 当前对话上下文 = LLM 看到的 messages[]。

    特性：
    - Token 预算控制容量
    - FIFO 驱逐（从最旧的消息开始）
    - Paired Eviction: 驱逐 assistant(tool_calls) 时，
      同时驱逐对应的 tool result 消息
    - 驱逐回调：通知 L2 从被驱逐消息中提取关键信息
    - system 消息保护：system prompt 不参与驱逐
    """

    def __init__(self, token_budget: int = 8000):
        self._messages: deque[MessageItem] = deque()
        self._token_budget = token_budget
        self._current_tokens = 0
        self._eviction_callbacks: list[Callable[[list[MessageItem]], None]] = []

    # ---- 写入 ----

    def append(self, message: MessageItem) -> list[MessageItem]:
        """
        追加消息到窗口末尾

        如果超出 token 预算，从头部驱逐最旧的消息。
        驱逐时执行 paired eviction（tool_call + tool_result 配对）。

        Args:
            message: 要追加的消息

        Returns:
            被驱逐的消息列表（可能为空）
        """
        self._messages.append(message)
        self._current_tokens += message.token_count

        evicted = self._evict_if_over_budget()

        if evicted:
            for callback in self._eviction_callbacks:
                callback(evicted)

        return evicted

    def append_message(
        self,
        role: str,
        content: str | dict[str, Any] | None = None,
        token_count: int = 0,
        **kwargs: Any,
    ) -> list[MessageItem]:
        """
        便捷方法：直接追加原始消息参数

        Args:
            role: 消息角色
            content: 消息内容
            token_count: token 数
            **kwargs: 传递给 MessageItem 的其他参数

        Returns:
            被驱逐的消息列表
        """
        item = MessageItem(
            role=role,
            content=content,
            token_count=token_count,
            **kwargs,
        )
        return self.append(item)

    # ---- 读取 ----

    def get_messages(self) -> list[dict[str, Any]]:
        """
        获取所有消息（LLM API 格式）

        Returns:
            消息字典列表，可直接传给 LLM API
        """
        return [msg.to_message() for msg in self._messages]

    def get_items(self) -> list[MessageItem]:
        """
        获取所有 MessageItem 对象

        Returns:
            MessageItem 列表（按时间顺序）
        """
        return list(self._messages)

    def get_recent(self, n: int) -> list[MessageItem]:
        """获取最近 n 条消息"""
        items = list(self._messages)
        return items[-n:] if n < len(items) else items

    # ---- 驱逐逻辑 ----

    def _evict_if_over_budget(self) -> list[MessageItem]:
        """
        超预算时从头部驱逐消息

        实现 paired eviction：
        1. 从头部取出最旧的非 system 消息
        2. 如果是 assistant 消息且包含 tool_calls，
           收集所有对应的 tool result 消息一起驱逐
        3. 如果是 tool 消息，找到对应的 assistant(tool_calls) 消息一起驱逐

        Returns:
            被驱逐的消息列表
        """
        evicted: list[MessageItem] = []

        while self._current_tokens > self._token_budget and self._messages:
            # 找到第一个可驱逐的消息（跳过 system）
            candidate = self._find_eviction_candidate()
            if candidate is None:
                break

            # 执行 paired eviction
            paired = self._collect_paired_messages(candidate)
            for msg in paired:
                self._remove_message(msg)
                evicted.append(msg)

        return evicted

    def _find_eviction_candidate(self) -> MessageItem | None:
        """找到第一个可驱逐的消息（跳过 system prompt）"""
        for msg in self._messages:
            if msg.role != "system":
                return msg
        return None

    def _collect_paired_messages(self, candidate: MessageItem) -> list[MessageItem]:
        """
        收集需要配对驱逐的消息

        规则：
        - assistant(tool_calls) → 同时驱逐对应的 tool result 消息
        - tool result → 同时驱逐对应的 assistant(tool_calls) 消息
        - user/assistant(text) → 单独驱逐
        """
        to_evict = [candidate]

        if candidate.role == "assistant" and candidate.tool_calls:
            # 收集所有对应的 tool result
            call_ids = {
                tc.get("id") for tc in candidate.tool_calls if tc.get("id")
            }
            if call_ids:
                for msg in self._messages:
                    if msg is candidate:
                        continue
                    if msg.role == "tool" and msg.tool_call_id in call_ids:
                        to_evict.append(msg)

        elif candidate.role == "tool" and candidate.tool_call_id:
            # 找到对应的 assistant(tool_calls) 消息
            for msg in self._messages:
                if msg is candidate:
                    continue
                if msg.role == "assistant" and msg.tool_calls:
                    call_ids = {
                        tc.get("id") for tc in msg.tool_calls if tc.get("id")
                    }
                    if candidate.tool_call_id in call_ids:
                        # 驱逐整个 assistant + 所有对应 tool results
                        to_evict = [msg]
                        for other in self._messages:
                            if other is msg:
                                continue
                            if other.role == "tool" and other.tool_call_id in call_ids:
                                to_evict.append(other)
                        break

        return to_evict

    def _remove_message(self, msg: MessageItem) -> None:
        """从 deque 中移除指定消息"""
        try:
            self._messages.remove(msg)
            self._current_tokens -= msg.token_count
        except ValueError:
            pass

    # ---- 回调 ----

    def on_eviction(self, callback: Callable[[list[MessageItem]], None]) -> None:
        """
        注册驱逐回调

        回调接收被驱逐的消息列表（可能包含配对消息）。
        典型用途：L2 从被驱逐消息中提取 facts。

        Args:
            callback: 回调函数，接收 list[MessageItem]
        """
        self._eviction_callbacks.append(callback)

    # ---- 状态查询 ----

    @property
    def token_budget(self) -> int:
        return self._token_budget

    @token_budget.setter
    def token_budget(self, value: int) -> None:
        self._token_budget = value

    def token_usage(self) -> int:
        return self._current_tokens

    def size(self) -> int:
        return len(self._messages)

    def clear(self) -> None:
        self._messages.clear()
        self._current_tokens = 0


# =============================================================================
# L2: WorkingMemoryLayer — 工作记忆
# =============================================================================


@dataclass(order=True)
class _PriorityEntry:
    """内部排序用的优先级包装"""

    priority: float  # -importance（min-heap → max-importance 优先）
    token_count: int = field(compare=False)
    entry: WorkingMemoryEntry = field(compare=False)


class WorkingMemoryLayer:
    """
    L2 工作记忆 — 存储 session 内的关键信息

    从 L1 驱逐消息中提取的 facts/decisions/summaries。
    按 importance 排序，token 预算控制容量。

    特性：
    - Heap-based 优先级队列
    - Token 预算控制
    - 驱逐最低 importance 的条目
    - 驱逐回调：通知 L3 持久化
    """

    def __init__(self, token_budget: int = 16000, ttl_seconds: int | None = None):
        self._heap: list[_PriorityEntry] = []
        self._token_budget = token_budget
        self._current_tokens = 0
        self._ttl_seconds = ttl_seconds
        self._eviction_callbacks: list[Callable[[list[WorkingMemoryEntry]], None]] = []

    # ---- TTL 清理 ----

    def _purge_expired(self) -> list[WorkingMemoryEntry]:
        """惰性清理过期条目"""
        if self._ttl_seconds is None:
            return []
        now = datetime.now()
        expired: list[WorkingMemoryEntry] = []
        remaining: list[_PriorityEntry] = []
        for pe in self._heap:
            if pe.entry.expires_at is not None and pe.entry.expires_at <= now:
                self._current_tokens -= pe.token_count
                expired.append(pe.entry)
            else:
                remaining.append(pe)
        if expired:
            self._heap = remaining
            heapq.heapify(self._heap)
        return expired

    # ---- 写入 ----

    def add(self, entry: WorkingMemoryEntry) -> list[WorkingMemoryEntry]:
        """
        添加工作记忆条目

        如果超出 token 预算，驱逐最低 importance 的条目。

        Args:
            entry: 工作记忆条目

        Returns:
            被驱逐的条目列表
        """
        # 设置 TTL 过期时间
        if self._ttl_seconds is not None and entry.expires_at is None:
            entry.expires_at = datetime.now() + timedelta(seconds=self._ttl_seconds)
        self._purge_expired()

        priority_entry = _PriorityEntry(
            priority=-entry.importance,
            token_count=entry.token_count,
            entry=entry,
        )

        evicted: list[WorkingMemoryEntry] = []

        # 需要腾出空间
        while (
            self._current_tokens + entry.token_count > self._token_budget
            and self._heap
        ):
            # 驱逐最低 importance（priority 最大的，即 heap 中 max）
            lowest = max(self._heap)
            # 如果新条目 importance 更低，不添加
            if priority_entry >= lowest:
                return evicted
            self._heap.remove(lowest)
            heapq.heapify(self._heap)
            self._current_tokens -= lowest.token_count
            evicted.append(lowest.entry)

        heapq.heappush(self._heap, priority_entry)
        self._current_tokens += entry.token_count

        if evicted:
            for callback in self._eviction_callbacks:
                callback(evicted)

        return evicted

    # ---- 读取 ----

    def get_entries(self, limit: int | None = None) -> list[WorkingMemoryEntry]:
        """
        获取所有条目（按 importance 降序）

        Args:
            limit: 最大返回数，None 表示全部

        Returns:
            WorkingMemoryEntry 列表
        """
        self._purge_expired()
        sorted_items = sorted(self._heap)
        entries = [item.entry for item in sorted_items]
        if limit is not None:
            entries = entries[:limit]
        return entries

    def get_by_type(self, entry_type: str) -> list[WorkingMemoryEntry]:
        """按类型过滤条目"""
        self._purge_expired()
        return [
            item.entry for item in self._heap
            if item.entry.entry_type.value == entry_type
        ]

    def find(self, entry_id: str) -> WorkingMemoryEntry | None:
        """按 ID 查找条目"""
        for item in self._heap:
            if item.entry.entry_id == entry_id:
                return item.entry
        return None

    # ---- 删除 ----

    def remove(self, entry_id: str) -> bool:
        """移除指定条目"""
        for item in self._heap:
            if item.entry.entry_id == entry_id:
                self._heap.remove(item)
                heapq.heapify(self._heap)
                self._current_tokens -= item.token_count
                return True
        return False

    # ---- 回调 ----

    def on_eviction(self, callback: Callable[[list[WorkingMemoryEntry]], None]) -> None:
        """
        注册驱逐回调

        典型用途：L3 持久化被驱逐的工作记忆条目。

        Args:
            callback: 回调函数，接收 list[WorkingMemoryEntry]
        """
        self._eviction_callbacks.append(callback)

    # ---- 状态查询 ----

    @property
    def token_budget(self) -> int:
        return self._token_budget

    @token_budget.setter
    def token_budget(self, value: int) -> None:
        self._token_budget = value

    def token_usage(self) -> int:
        return self._current_tokens

    def size(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
        self._current_tokens = 0
