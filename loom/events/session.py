"""
Session - 会话实体 (EventBus 层)

Session 是 EventBus 和 Agent Context 之间的智能桥梁：
- EventBus 容量无限（可以有成千上万的 Task）
- Agent Context 有限（如 128K tokens）
- Session 负责从大量 Task 中选择最相关的内容

核心职责：
1. Task 流管理 - 订阅、过滤、路由
2. Memory 存储 - L1(消息窗口) / L2(工作记忆) / L3(持久记忆)
3. Context 构建 - 按需从 Memory 选择内容
4. 生命周期管理 - ACTIVE/PAUSED/ENDED

基于 Token-First Design 原则。
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.context import ContextOrchestrator
    from loom.events.event_bus import EventBus
    from loom.memory.core import LoomMemory
    from loom.memory.tokenizer import TokenCounter
    from loom.runtime import Task


class SessionStatus(StrEnum):
    """会话状态"""

    ACTIVE = "active"  # 活跃中
    PAUSED = "paused"  # 已暂停
    ENDED = "ended"  # 已结束


class Session:
    """
    会话实体 - EventBus 和 Agent Context 之间的智能桥梁

    架构位置：EventBus 层
    - 拥有 Memory 实例（存储组件）
    - 拥有 ContextOrchestrator（构建组件）
    - 与 EventBus 集成（Task 流管理）

    Token 预算层级（三层记忆架构）：
    - L1: 消息窗口 (默认 8K tokens)
    - L2: 工作记忆 (默认 16K tokens)
    - L3: 持久记忆 (可选，通过 MemoryStore)
    - Context: Agent 上下文 (默认 128K tokens)
    """

    def __init__(
        self,
        session_id: str,
        event_bus: "EventBus | None" = None,
        # Token-First 预算配置
        l1_token_budget: int = 8000,
        l2_token_budget: int = 16000,
        context_token_budget: int = 128000,
        # 可选的 token 计数器
        token_counter: "TokenCounter | None" = None,
    ):
        """
        初始化会话

        Args:
            session_id: 会话唯一标识
            event_bus: 事件总线（Task 路由）
            l1_token_budget: L1 消息窗口 token 预算
            l2_token_budget: L2 工作记忆 token 预算
            context_token_budget: 上下文构建 token 预算
            token_counter: Token 计数器（用于 Context 构建）
        """
        self.session_id = session_id
        self.context_token_budget = context_token_budget
        self.created_at = datetime.now()
        self.status = SessionStatus.ACTIVE

        # 生命周期时间戳
        self._paused_at: datetime | None = None
        self._ended_at: datetime | None = None

        # EventBus 引用
        self._event_bus = event_bus

        # Token 预算配置（保存用于懒加载）
        self._l1_token_budget = l1_token_budget
        self._l2_token_budget = l2_token_budget
        self._token_counter = token_counter

        # 懒加载的组件
        self._memory: LoomMemory | None = None
        self._context_orchestrator: ContextOrchestrator | None = None

        # EventBus 订阅 ID（用于取消订阅）
        self._subscription_handler: Any = None

    # ==================== 懒加载组件 ====================

    @property
    def memory(self) -> "LoomMemory":
        """获取会话的 Memory 实例（懒加载）"""
        if self._memory is None:
            from loom.memory.core import LoomMemory

            self._memory = LoomMemory(
                node_id=self.session_id,
                l1_token_budget=self._l1_token_budget,
                l2_token_budget=self._l2_token_budget,
                session_id=self.session_id,
            )
        return self._memory

    @property
    def event_bus(self) -> "EventBus | None":
        """获取会话的 EventBus 实例"""
        return self._event_bus

    @property
    def is_active(self) -> bool:
        """会话是否活跃"""
        return self.status == SessionStatus.ACTIVE

    @property
    def duration(self) -> float:
        """会话持续时间（秒）"""
        end_time = self._ended_at or datetime.now()
        return (end_time - self.created_at).total_seconds()

    # ==================== 生命周期管理 ====================

    def pause(self) -> None:
        """暂停会话"""
        if self.status != SessionStatus.ACTIVE:
            raise RuntimeError(f"Cannot pause session in {self.status} status")
        self.status = SessionStatus.PAUSED
        self._paused_at = datetime.now()

    def resume(self) -> None:
        """恢复会话"""
        if self.status != SessionStatus.PAUSED:
            raise RuntimeError(f"Cannot resume session in {self.status} status")
        self.status = SessionStatus.ACTIVE
        self._paused_at = None

    def end(self) -> None:
        """结束会话"""
        if self.status == SessionStatus.ENDED:
            return  # 幂等操作
        self.status = SessionStatus.ENDED
        self._ended_at = datetime.now()
        # 清理 Memory 资源
        if self._memory is not None:
            self._memory.l2.clear()

    # ==================== Task 流管理 ====================

    def add_task(self, task: "Task") -> None:
        """
        添加任务到会话记忆

        将 Task 转换为消息存入 L1 滑动窗口。

        Args:
            task: 要添加的任务

        Raises:
            RuntimeError: 如果会话不活跃
        """
        if not self.is_active:
            raise RuntimeError(f"Cannot add task to {self.status} session")
        # 确保任务关联到此会话
        task.session_id = self.session_id
        # 将 Task 转换为消息存入 L1
        content = str(task.parameters.get("content", "") or "")
        if not content:
            content = f"[{task.action}] {task.parameters}"
        self.memory.add_message(
            "assistant",
            content,
            metadata={"task_id": getattr(task, "task_id", getattr(task, "taskId", ""))},
        )

    async def publish_task(self, task: "Task", wait_result: bool = True) -> "Task":
        """
        通过 EventBus 发布任务

        自动注入 session_id，确保任务关联到此会话。

        Args:
            task: 要发布的任务
            wait_result: 是否等待任务完成

        Returns:
            处理后的任务

        Raises:
            RuntimeError: 如果会话不活跃或没有 EventBus
        """
        if not self.is_active:
            raise RuntimeError(f"Cannot publish task in {self.status} session")
        if not self._event_bus:
            raise RuntimeError("No EventBus configured for this session")

        # 自动注入 session_id
        task.session_id = self.session_id

        # 通过 EventBus 发布
        return await self._event_bus.publish(task, wait_result=wait_result)

    # ==================== Context 构建 ====================

    async def build_context(
        self,
        query: str,
        system_prompt: str = "",
        user_input: str = "",
        tool_manager: Any = None,
        skill_registry: Any = None,
        active_skill_ids: list[str] | None = None,
        min_relevance: float = 0.5,
    ) -> list[dict[str, str]]:
        """
        构建 Agent 上下文（整合 7 大来源）

        Args:
            query: 当前任务/查询内容
            system_prompt: 系统提示词
            user_input: 用户输入
            tool_manager: 工具管理器
            skill_registry: 技能注册表
            active_skill_ids: 激活的技能ID列表
            min_relevance: 最低相关性阈值

        Returns:
            LLM 消息列表
        """
        from loom.context.orchestrator import ContextOrchestrator
        from loom.context.source import ContextSource
        from loom.context.sources import (
            L1RecentSource,
            L2ImportantSource,
            PromptSource,
            SkillSource,
            ToolSource,
            UserInputSource,
        )
        from loom.memory import EstimateCounter

        # 获取或创建 token counter
        token_counter = self._token_counter or EstimateCounter()

        # 构建 7 大上下文源
        sources: list[ContextSource] = []

        # 1. User Input Source
        user_source = UserInputSource(user_input)
        sources.append(user_source)

        # 2. Prompt Source
        prompt_source = PromptSource(system_prompt)
        sources.append(prompt_source)

        # 3. Memory Sources (L1, L2)
        l1_source = L1RecentSource(self.memory, self.session_id)
        l2_source = L2ImportantSource(self.memory, self.session_id)
        sources.extend([l1_source, l2_source])

        # 4. Tool Source
        if tool_manager:
            tool_source = ToolSource(tool_manager=tool_manager)
            sources.append(tool_source)

        # 5. Skill Source
        if skill_registry:
            skill_source = SkillSource(
                skill_registry=skill_registry,
                active_skill_ids=active_skill_ids or [],
            )
            sources.append(skill_source)

        # 创建编排器
        orchestrator = ContextOrchestrator(
            token_counter=token_counter,
            sources=sources,
            model_context_window=self.context_token_budget,
        )

        return await orchestrator.build_context(
            query=query,
            system_prompt=system_prompt,
            min_relevance=min_relevance,
        )

    # ==================== 统计信息 ====================

    def get_stats(self) -> dict[str, Any]:
        """获取会话统计信息"""
        stats: dict[str, Any] = {
            "session_id": self.session_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "duration_seconds": self.duration,
            "context_token_budget": self.context_token_budget,
        }
        # 如果 Memory 已初始化，添加 Memory 统计
        if self._memory is not None:
            stats.update(self._memory.get_stats())
        return stats

    def __repr__(self) -> str:
        return f"Session(id={self.session_id}, status={self.status})"
