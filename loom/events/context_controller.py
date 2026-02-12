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
from typing import TYPE_CHECKING, Any

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
        """
        初始化上下文控制器

        Args:
            event_bus: 事件总线
            token_counter: Token 计数器
        """
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
        聚合多个 Session 的 L2 内容到 L3

        从指定 Session 的 L2 层收集重要任务，
        可选地进行摘要压缩，然后存储到 L3。

        Args:
            session_ids: 要聚合的 Session ID 列表（None 表示所有）
            summarizer: 可选的摘要函数

        Returns:
            聚合后的摘要字典，如果无内容则返回 None
        """
        target_sessions = session_ids or list(self._sessions.keys())

        # 收集所有 L2 任务
        l2_contents: list[dict[str, Any]] = []
        for sid in target_sessions:
            session = self._sessions.get(sid)
            if session is None or not session.is_active:
                continue

            l2_tasks = session.get_l2_tasks(limit=50)
            for task in l2_tasks:
                l2_contents.append(
                    {
                        "session_id": sid,
                        "task_id": task.task_id,
                        "action": task.action,
                        "content": self._task_to_content(task),
                        "importance": getattr(task, "importance", 0.5),
                    }
                )

        if not l2_contents:
            return None

        # 生成摘要
        if summarizer:
            summary_text = await summarizer(l2_contents)
        else:
            # 默认简单拼接
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
        """
        设置 L4 持久化处理器

        Args:
            persist_handler: 持久化函数，接收摘要字典
            load_handler: 加载函数，接收 agent_id 返回摘要列表
        """
        self._l4_persist_handler = persist_handler
        self._l4_load_handler = load_handler

    async def persist_to_l4(
        self,
        summary: dict[str, Any] | None = None,
        agent_id: str = "default",
    ) -> bool:
        """
        持久化摘要到 L4（全局存储）

        Args:
            summary: 要持久化的摘要（None 表示持久化最新的 L3 摘要）
            agent_id: Agent 标识

        Returns:
            是否成功持久化
        """
        if self._l4_persist_handler is None:
            return False

        target = summary
        if target is None and self._l3_summaries:
            target = self._l3_summaries[-1]

        if target is None:
            return False

        # 添加 agent_id
        target["agent_id"] = agent_id

        try:
            await self._l4_persist_handler(target)
            return True
        except Exception:
            return False

    async def load_from_l4(self, agent_id: str = "default") -> list[dict[str, Any]]:
        """
        从 L4 加载持久化的摘要

        Args:
            agent_id: Agent 标识

        Returns:
            摘要列表
        """
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

        提升流程：L1 → L2 → L3 → L4
        - L1→L2: 由 Session.promote_tasks() 处理（基于重要性）
        - L2→L3: 聚合多 Session 的 L2 到 L3
        - L3→L4: 持久化 L3 到全局存储

        Args:
            session_id: 指定 Session（None 表示所有）
            l2_to_l3: 是否执行 L2→L3 提升
            l3_to_l4: 是否执行 L3→L4 提升
            summarizer: 可选的摘要函数

        Returns:
            提升结果统计
        """
        l1_to_l2_count = 0
        l2_to_l3_summary: dict[str, Any] | None = None
        l3_to_l4_ok = False

        # L1 → L2: 触发各 Session 的任务提升
        target_sessions = [session_id] if session_id else list(self._sessions.keys())
        for sid in target_sessions:
            session = self._sessions.get(sid)
            if session and session.is_active:
                session.promote_tasks()
                l1_to_l2_count += 1

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
            "l1_to_l2": l1_to_l2_count,
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

        Args:
            session_ids: 要聚合的 Session ID 列表
            query: 当前查询（用于相关性计算）
            token_budget: 总 token 预算
            allocation_strategy: 预算分配策略
                - "equal": 平均分配
                - "priority": 按 Session 优先级分配
                - "dynamic": 按内容相关性动态分配

        Returns:
            聚合后的 ContextBlock 列表
        """
        from loom.context.block import ContextBlock

        blocks: list[ContextBlock] = []
        sessions = [self._sessions[sid] for sid in session_ids if sid in self._sessions]

        if not sessions:
            return blocks

        # 计算每个 Session 的预算
        budgets = self._allocate_budget(sessions, token_budget, allocation_strategy)

        # 从每个 Session 收集上下文
        for session, budget in zip(sessions, budgets, strict=False):
            session_blocks = await self._collect_from_session(session, query, budget)
            blocks.extend(session_blocks)

        # 按优先级排序
        blocks.sort(key=lambda b: b.priority, reverse=True)

        return blocks

    def _allocate_budget(
        self,
        sessions: list["Session"],
        total_budget: int,
        strategy: str,
    ) -> list[int]:
        """分配 token 预算给各 Session"""
        n = len(sessions)
        if n == 0:
            return []

        if strategy == "equal":
            base = total_budget // n
            return [base] * n

        # 默认平均分配
        base = total_budget // n
        return [base] * n

    async def _collect_from_session(
        self,
        session: "Session",
        _query: str,
        budget: int,
    ) -> list["ContextBlock"]:
        """从单个 Session 收集上下文"""
        from loom.context.block import ContextBlock

        blocks: list[ContextBlock] = []
        current_tokens = 0

        # 从 L1 获取最近任务
        l1_tasks = session.get_l1_tasks(limit=20)
        for task in l1_tasks:
            content = self._task_to_content(task)
            if not content:
                continue

            tokens = self._estimate_tokens(content)
            if current_tokens + tokens > budget:
                break

            block = ContextBlock(
                content=content,
                role="assistant",
                token_count=tokens,
                priority=0.8,
                source=f"session:{session.session_id}:L1",
                metadata={"task_id": task.task_id, "session_id": session.session_id},
            )
            blocks.append(block)
            current_tokens += tokens

        return blocks

    def _task_to_content(self, task: "Task") -> str:
        """将 Task 转换为内容字符串"""
        action = task.action
        params = task.parameters

        if action == "node.thinking":
            return str(params.get("content", ""))
        elif action == "node.tool_call":
            tool_name = params.get("tool_name", "")
            tool_args = params.get("tool_args", {})
            return f"[Tool: {tool_name}] {tool_args}"
        elif action == "node.message":
            return str(params.get("content") or params.get("message", ""))
        elif action == "execute":
            return str(params.get("content", ""))

        return ""

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
        """
        分发 Task 到多个 Session

        将一个 Agent 产生的 Task 分发到多个 Session 流中。

        Args:
            task: 要分发的任务
            session_ids: 目标 Session ID 列表
            copy_task: 是否复制 Task（避免共享状态）

        Returns:
            {session_id: task} 映射
        """
        results: dict[str, Task] = {}

        for sid in session_ids:
            session = self._sessions.get(sid)
            if session is None or not session.is_active:
                continue

            # 复制或直接使用
            distributed_task = task.copy() if copy_task else task

            # 添加到 Session
            session.add_task(distributed_task)
            results[sid] = distributed_task

        return results

    async def broadcast(
        self,
        task: "Task",
        copy_task: bool = True,
    ) -> DistributionResult:
        """
        广播 Task 到所有活跃 Session

        Args:
            task: 要分发的任务
            copy_task: 是否复制 Task

        Returns:
            DistributionResult
        """
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
        """
        条件过滤分发

        Args:
            task: 要分发的任务
            filter_fn: 过滤函数，返回 True 表示接收
            copy_task: 是否复制 Task

        Returns:
            DistributionResult
        """
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
        task_limit: int = 10,
        include_l2: bool = True,
    ) -> dict[str, int]:
        """
        从一个 Session 共享上下文到其他 Session

        Args:
            from_session_id: 源 Session ID
            to_session_ids: 目标 Session ID 列表
            task_limit: 共享的任务数量限制
            include_l2: 是否包含 L2 重要任务

        Returns:
            {session_id: shared_count} 映射
        """
        source = self._sessions.get(from_session_id)
        if source is None:
            return {}

        # 收集要共享的任务
        tasks_to_share: list[Task] = []

        # L1 最近任务
        l1_tasks = source.get_l1_tasks(limit=task_limit)
        tasks_to_share.extend(l1_tasks)

        # L2 重要任务
        if include_l2:
            l2_tasks = source.get_l2_tasks(limit=task_limit)
            tasks_to_share.extend(l2_tasks)

        if not tasks_to_share:
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
            for task in tasks_to_share:
                try:
                    shared_task = task.model_copy(deep=True)
                    shared_task.metadata = shared_task.metadata or {}
                    shared_task.metadata["shared_from"] = from_session_id
                    session.add_task(shared_task)
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
        """
        获取可供 Session 使用的 L3 共享上下文

        返回与指定 Session 相关的 L3 摘要。

        Args:
            session_id: Session ID
            limit: 返回数量限制

        Returns:
            L3 摘要列表
        """
        relevant_summaries = []

        for summary in self._l3_summaries:
            session_ids = summary.get("session_ids", [])
            # 包含该 Session 或是全局摘要
            if session_id in session_ids or not session_ids:
                relevant_summaries.append(summary)

        return relevant_summaries[-limit:]
