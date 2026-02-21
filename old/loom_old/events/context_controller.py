"""
ContextController - 上下文控制器

核心控制层，负责：
1. 聚合（Aggregation）：多个 Session 的上下文 → 一个 Agent
2. 分发（Distribution）：一个 Agent 的输出 → 多个 Session

Memory 只是 Context 控制的存储机制。
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from loom.context import ContextBlock
    from loom.events.event_bus import EventBus
    from loom.events.session import Session
    from loom.memory.tokenizer import TokenCounter
    from loom.runtime import Task


class DistributionStrategy(StrEnum):
    """分发策略"""

    BROADCAST = "broadcast"  # 广播到所有 Session
    TARGETED = "targeted"  # 只发送到指定 Session
    FILTERED = "filtered"  # 根据条件过滤 Session


@dataclass
class DistributionResult:
    """分发结果"""

    success: dict[str, "Task"] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)

    @property
    def success_count(self) -> int:
        return len(self.success)

    @property
    def failed_count(self) -> int:
        return len(self.failed)


class ContextController:
    """
    上下文控制器

    控制 Session 之间的上下文流动：
    - 聚合：多个 Session → 一个 Agent 上下文
    - 分发：一个 Task → 多个 Session

    架构位置：EventBus 层的控制组件
    """

    def __init__(
        self,
        event_bus: "EventBus | None" = None,
        token_counter: "TokenCounter | None" = None,
    ):
        self._event_bus = event_bus
        self._token_counter = token_counter
        self._sessions: dict[str, Session] = {}

        # L3: Agent 级聚合存储
        self._l3_summaries: list[dict[str, Any]] = []
        self._l3_token_budget: int = 32000
        self._l3_current_tokens: int = 0

        # L4: 持久化配置
        self._l4_persist_handler: Callable[[dict[str, Any]], Awaitable[None]] | None = None
        self._l4_load_handler: Callable[[str], Awaitable[list[dict[str, Any]]]] | None = None

    # ==================== Session 管理 ====================

    def register_session(self, session: "Session") -> None:
        """注册 Session"""
        self._sessions[session.session_id] = session

    def unregister_session(self, session_id: str) -> None:
        """注销 Session"""
        self._sessions.pop(session_id, None)

    def get_session(self, session_id: str) -> "Session | None":
        """获取 Session"""
        return self._sessions.get(session_id)

    @property
    def session_ids(self) -> list[str]:
        """获取所有 Session ID"""
        return list(self._sessions.keys())

    # ==================== L3: Agent 级聚合存储 ====================

    def add_to_l3(self, summary: dict[str, Any]) -> None:
        """添加摘要到 L3"""
        self._l3_summaries.append(summary)

    def get_l3_summaries(self, limit: int = 20) -> list[dict[str, Any]]:
        """获取 L3 摘要"""
        return self._l3_summaries[-limit:]

    @property
    def l3_count(self) -> int:
        """L3 摘要数量"""
        return len(self._l3_summaries)

    @property
    def l3_token_usage(self) -> int:
        """L3 当前 token 使用量"""
        return self._l3_current_tokens

    async def aggregate_to_l3(
        self,
        session_ids: list[str] | None = None,
        summarizer: Callable[[list[dict[str, Any]]], Awaitable[str]] | None = None,
    ) -> dict[str, Any] | None:
        """
        聚合多个 Session 的 L2 工作记忆到 L3

        从指定 Session 的 L2 层收集工作记忆条目，
        可选地进行摘要压缩，然后存储到 L3。
        """
        target_sessions = session_ids or list(self._sessions.keys())

        # 收集所有 L2 工作记忆条目
        l2_contents: list[dict[str, Any]] = []
        for sid in target_sessions:
            session = self._sessions.get(sid)
            if session is None or not session.is_active:
                continue

            entries = session.memory.get_working_memory(limit=50)
            for entry in entries:
                l2_contents.append(
                    {
                        "session_id": sid,
                        "entry_id": entry.entry_id,
                        "content": entry.content,
                        "importance": entry.importance,
                    }
                )

        if not l2_contents:
            return None

        # 生成摘要
        if summarizer:
            summary_text = await summarizer(l2_contents)
        else:
            summary_text = "\n".join(
                f"[{c['session_id']}] {c['content'][:200]}" for c in l2_contents[:20]
            )

        # 计算 token
        tokens = self._estimate_tokens(summary_text)

        # 检查预算，必要时清理旧摘要
        while self._l3_current_tokens + tokens > self._l3_token_budget and self._l3_summaries:
            old = self._l3_summaries.pop(0)
            self._l3_current_tokens -= old.get("tokens", 0)

        # 创建摘要记录
        from datetime import datetime

        summary = {
            "timestamp": datetime.now().isoformat(),
            "session_ids": target_sessions,
            "content": summary_text,
            "tokens": tokens,
            "source_count": len(l2_contents),
        }

        self._l3_summaries.append(summary)
        self._l3_current_tokens += tokens

        return summary

    # ==================== L4: 全局持久化接口 ====================

    def set_l4_handlers(
        self,
        persist_handler: Callable[[dict[str, Any]], Awaitable[None]],
        load_handler: Callable[[str], Awaitable[list[dict[str, Any]]]] | None = None,
    ) -> None:
        """设置 L4 持久化处理器"""
        self._l4_persist_handler = persist_handler
        self._l4_load_handler = load_handler

    async def persist_to_l4(
        self,
        summary: dict[str, Any] | None = None,
        agent_id: str = "default",
    ) -> bool:
        """持久化摘要到 L4（全局存储）"""
        if self._l4_persist_handler is None:
            return False

        target = summary
        if target is None and self._l3_summaries:
            target = self._l3_summaries[-1]

        if target is None:
            return False

        target["agent_id"] = agent_id

        try:
            await self._l4_persist_handler(target)
            return True
        except Exception:
            return False

    async def load_from_l4(self, agent_id: str = "default") -> list[dict[str, Any]]:
        """从 L4 加载持久化的摘要"""
        if self._l4_load_handler is None:
            return []

        try:
            return await self._l4_load_handler(agent_id)
        except Exception:
            return []

    # ==================== 提升触发器 ====================

    async def trigger_promotion(
        self,
        session_id: str | None = None,
        l2_to_l3: bool = True,
        l3_to_l4: bool = False,
        summarizer: Callable[[list[dict[str, Any]]], Awaitable[str]] | None = None,
    ) -> dict[str, Any]:
        """
        触发记忆提升流程

        三层架构中 L1→L2 由驱逐回调自动完成，无需手动触发。
        此方法仅处理：
        - L2→L3: 聚合多 Session 的 L2 到 L3
        - L3→L4: 持久化 L3 到全局存储
        """
        l2_to_l3_summary: dict[str, Any] | None = None
        l3_to_l4_ok = False

        target_sessions = [session_id] if session_id else list(self._sessions.keys())
        session_count = sum(
            1 for sid in target_sessions
            if (s := self._sessions.get(sid)) and s.is_active
        )

        # L2 → L3: 聚合到 L3
        if l2_to_l3:
            l2_to_l3_summary = await self.aggregate_to_l3(
                session_ids=target_sessions if session_id else None,
                summarizer=summarizer,
            )

        # L3 → L4: 持久化
        if l3_to_l4 and l2_to_l3_summary:
            l3_to_l4_ok = await self.persist_to_l4(l2_to_l3_summary)

        return {
            "sessions_processed": session_count,
            "l2_to_l3": l2_to_l3_summary,
            "l3_to_l4": l3_to_l4_ok,
        }

    async def aggregate_context(
        self,
        session_ids: list[str],
        query: str,
        token_budget: int,
        allocation_strategy: str = "equal",
    ) -> list["ContextBlock"]:
        """
        聚合多个 Session 的上下文

        从多个 Session 的 Memory 中选择最相关的内容，
        合并成一个 Agent 可用的上下文。
        """
        from loom.context.block import ContextBlock

        blocks: list[ContextBlock] = []
        sessions = [self._sessions[sid] for sid in session_ids if sid in self._sessions]

        if not sessions:
            return blocks

        budgets = self._allocate_budget(sessions, token_budget, allocation_strategy)

        for session, budget in zip(sessions, budgets, strict=False):
            session_blocks = await self._collect_from_session(session, query, budget)
            blocks.extend(session_blocks)

        blocks.sort(key=lambda b: b.priority, reverse=True)

        return blocks

    def _allocate_budget(
        self,
        sessions: list["Session"],
        total_budget: int,
        strategy: str,  # noqa: ARG002
    ) -> list[int]:
        """分配 token 预算给各 Session"""
        n = len(sessions)
        if n == 0:
            return []

        base = total_budget // n
        return [base] * n

    async def _collect_from_session(
        self,
        session: "Session",
        _query: str,
        budget: int,
    ) -> list["ContextBlock"]:
        """从单个 Session 收集上下文（基于 L1 消息）"""
        from loom.context.block import ContextBlock

        blocks: list[ContextBlock] = []
        current_tokens = 0

        # 从 L1 获取最近消息
        messages = session.memory.get_message_items()
        for msg in messages:
            content = str(msg.content) if msg.content else ""
            if not content:
                continue

            tokens = msg.token_count or self._estimate_tokens(content)
            if current_tokens + tokens > budget:
                break

            # 确保 role 类型正确
            role_str = msg.role if msg.role in ("user", "assistant", "system") else "assistant"
            role: Literal["system", "user", "assistant"] = role_str  # type: ignore[assignment]
            block = ContextBlock(
                content=content,
                role=role,
                token_count=tokens,
                priority=0.8,
                source=f"session:{session.session_id}:L1",
                metadata={"message_id": msg.message_id, "session_id": session.session_id},
            )
            blocks.append(block)
            current_tokens += tokens

        return blocks

    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数"""
        if self._token_counter:
            return self._token_counter.count(text)
        return max(1, len(text) // 4)

    # ==================== 分发：一个 Agent → 多 Session ====================

    async def distribute_task(
        self,
        task: "Task",
        session_ids: list[str],
        copy_task: bool = True,
    ) -> dict[str, "Task"]:
        """分发 Task 到多个 Session"""
        results: dict[str, Task] = {}

        for sid in session_ids:
            session = self._sessions.get(sid)
            if session is None or not session.is_active:
                continue

            distributed_task = task.copy() if copy_task else task
            session.add_task(distributed_task)
            results[sid] = distributed_task

        return results

    async def broadcast(
        self,
        task: "Task",
        copy_task: bool = True,
    ) -> DistributionResult:
        """广播 Task 到所有活跃 Session"""
        result = DistributionResult()

        for sid, session in self._sessions.items():
            if not session.is_active:
                result.failed[sid] = "Session not active"
                continue

            try:
                t = task.model_copy(deep=True) if copy_task else task
                session.add_task(t)
                result.success[sid] = t
            except Exception as e:
                result.failed[sid] = str(e)

        return result

    async def distribute_filtered(
        self,
        task: "Task",
        filter_fn: Callable[["Session"], bool],
        copy_task: bool = True,
    ) -> DistributionResult:
        """条件过滤分发"""
        result = DistributionResult()

        for sid, session in self._sessions.items():
            if not session.is_active:
                continue

            if not filter_fn(session):
                continue

            try:
                t = task.model_copy(deep=True) if copy_task else task
                session.add_task(t)
                result.success[sid] = t
            except Exception as e:
                result.failed[sid] = str(e)

        return result

    # ==================== 跨 Session 记忆共享 ====================

    async def share_context(
        self,
        from_session_id: str,
        to_session_ids: list[str],
        message_limit: int = 10,
        include_l2: bool = True,
    ) -> dict[str, int]:
        """
        从一个 Session 共享上下文到其他 Session

        通过 Memory API 获取 L1 消息和 L2 工作记忆，
        将内容作为消息添加到目标 Session 的 L1。
        """
        source = self._sessions.get(from_session_id)
        if source is None:
            return {}

        # 收集要共享的内容
        shared_contents: list[tuple[str, str]] = []  # (role, content)

        # L1 最近消息
        messages = source.memory.get_message_items()
        for msg in messages[-message_limit:]:
            content = str(msg.content) if msg.content else ""
            if content:
                shared_contents.append((msg.role, content))

        # L2 工作记忆
        if include_l2:
            entries = source.memory.get_working_memory(limit=message_limit)
            for entry in entries:
                if entry.content:
                    shared_contents.append(("system", f"[Shared Memory] {entry.content}"))

        if not shared_contents:
            return {}

        # 分发到目标 Session
        results: dict[str, int] = {}
        for sid in to_session_ids:
            if sid == from_session_id:
                continue

            session = self._sessions.get(sid)
            if session is None or not session.is_active:
                continue

            count = 0
            for role, content in shared_contents:
                try:
                    session.memory.add_message(
                        role,
                        content,
                        metadata={"shared_from": from_session_id},
                    )
                    count += 1
                except Exception:
                    pass

            results[sid] = count

        return results

    def get_shared_l3_context(
        self,
        session_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """获取可供 Session 使用的 L3 共享上下文"""
        relevant_summaries = []

        for summary in self._l3_summaries:
            session_ids = summary.get("session_ids", [])
            if session_id in session_ids or not session_ids:
                relevant_summaries.append(summary)

        return relevant_summaries[-limit:]
