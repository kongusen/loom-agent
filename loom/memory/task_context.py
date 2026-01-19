"""
Task-based Context Management

基于 Task 的上下文管理，整合 LoomMemory 和 EventBus。

核心功能：
1. 从多个来源收集上下文（Memory + EventBus）
2. 将 Task 转换为 LLM 消息格式
3. 智能压缩和总结
4. 精确的 token 控制

设计理念：
- 防止上下文腐化
- 最大化智能
- 支持长时间任务
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from loom.memory.tokenizer import TokenCounter
from loom.protocol import Task

if TYPE_CHECKING:
    from loom.config.knowledge import KnowledgeBaseProvider
    from loom.events.queryable_event_bus import QueryableEventBus
    from loom.memory.core import LoomMemory


# ==================== 接口定义 ====================


class ContextSource(ABC):
    """
    上下文源抽象接口

    定义从不同来源获取上下文的统一接口。
    """

    @abstractmethod
    async def get_context(
        self,
        current_task: Task,
        max_items: int = 10,
    ) -> list[Task]:
        """
        获取上下文 Task 列表

        Args:
            current_task: 当前任务
            max_items: 最大返回数量

        Returns:
            相关的 Task 列表
        """
        pass


# ==================== 消息转换器 ====================


class MessageConverter:
    """
    Task → LLM Message 转换器

    将不同类型的 Task 转换为 LLM API 消息格式。
    """

    def convert_task_to_message(self, task: Task) -> dict[str, str] | None:
        """
        将单个 Task 转换为消息

        Args:
            task: Task 对象

        Returns:
            LLM 消息字典，如果不应该包含则返回 None
        """
        action = task.action
        params = task.parameters

        # 根据 action 类型转换
        if action == "node.thinking":
            # 思考过程 → assistant 消息
            content = params.get("content", "")
            if content:
                return {"role": "assistant", "content": content}

        elif action == "node.tool_call":
            # 工具调用 → assistant 消息
            tool_name = params.get("tool_name", "")
            tool_args = params.get("tool_args", {})
            return {"role": "assistant", "content": f"[Calling {tool_name}({tool_args})]"}

        elif action == "execute":
            # 任务执行 → user 消息
            content = params.get("content", "")
            if content:
                return {"role": "user", "content": content}

        # 其他类型暂不转换
        return None

    def convert_tasks_to_messages(
        self,
        tasks: list[Task],
    ) -> list[dict[str, str]]:
        """
        批量转换 Task 为消息

        Args:
            tasks: Task 列表

        Returns:
            消息列表
        """
        messages = []
        for task in tasks:
            msg = self.convert_task_to_message(task)
            if msg:
                messages.append(msg)
        return messages


# ==================== 上下文源实现 ====================


class MemoryContextSource(ContextSource):
    """
    从 LoomMemory 获取上下文

    优先级：L2 (工作记忆) > L1 (最近任务)
    """

    def __init__(self, memory: "LoomMemory"):
        self.memory = memory

    async def get_context(
        self,
        _current_task: Task,
        max_items: int = 10,
    ) -> list[Task]:
        """获取记忆中的相关任务"""
        # 1. 优先从 L2 获取（重要任务）
        l2_tasks = self.memory.get_l2_tasks(limit=max_items // 2)

        # 2. 从 L1 获取最近任务
        l1_tasks = self.memory.get_l1_tasks(limit=max_items // 2)

        # 3. 合并去重
        seen_ids = set()
        context_tasks = []

        for task in l2_tasks + l1_tasks:
            if task.task_id not in seen_ids:
                context_tasks.append(task)
                seen_ids.add(task.task_id)

        return context_tasks[:max_items]


class EventBusContextSource(ContextSource):
    """
    从 EventBus 获取上下文

    获取思考过程、工具调用等事件。
    """

    def __init__(self, event_bus: "QueryableEventBus"):
        self.event_bus = event_bus

    async def get_context(
        self,
        current_task: Task,
        max_items: int = 10,
    ) -> list[Task]:
        """获取相关事件"""
        context_tasks = []

        # 1. 获取当前任务的所有事件
        task_events = self.event_bus.query_by_task(current_task.task_id)
        context_tasks.extend(task_events)

        # 2. 获取当前节点的最近思考
        node_id = current_task.parameters.get("node_id")
        if node_id:
            thinking_events = self.event_bus.query_by_node(
                node_id,
                action_filter="node.thinking",
                limit=max_items // 2,
            )
            context_tasks.extend(thinking_events)

        # 3. 去重并限制数量
        seen_ids = set()
        unique_tasks = []
        for task in context_tasks:
            if task.task_id not in seen_ids:
                unique_tasks.append(task)
                seen_ids.add(task.task_id)

        return unique_tasks[:max_items]


# ==================== 核心管理器 ====================


class TaskContextManager:
    """
    基于 Task 的上下文管理器

    整合 LoomMemory 和 EventBus，提供智能的上下文构建。
    """

    def __init__(
        self,
        token_counter: TokenCounter,
        sources: list[ContextSource],
        converter: MessageConverter | None = None,
        max_tokens: int = 4000,
        system_prompt: str = "",
        knowledge_base: "KnowledgeBaseProvider | None" = None,
    ):
        """初始化上下文管理器"""
        self.token_counter = token_counter
        self.sources = sources
        self.converter = converter or MessageConverter()
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.knowledge_base = knowledge_base

    async def build_context(
        self,
        current_task: Task,
    ) -> list[dict[str, str]]:
        """
        构建 LLM 上下文（优化版 - L1自动包含 + LLM主动查询L2/L3/L4）

        性能优化策略：
        - L1（最近任务）自动包含在上下文中（保证速度）
        - 当前任务直接包含
        - L2/L3/L4通过工具按需查询（以压缩陈述句形式）

        Args:
            current_task: 当前正在处理的任务

        Returns:
            OpenAI 格式的消息列表
        """
        # 1. 收集L1最近任务（自动包含，保证速度）
        l1_tasks = []
        for source in self.sources:
            # 只从MemoryContextSource获取L1任务
            if hasattr(source, "memory") and hasattr(source.memory, "get_l1_tasks"):
                l1_tasks = source.memory.get_l1_tasks(limit=10)  # 最近10个任务
                break

        # 2. 转换L1任务为消息
        context_messages = []
        if l1_tasks:
            context_messages = self.converter.convert_tasks_to_messages(l1_tasks)

        # 3. 外部知识库查询（自动包含相关知识）
        if self.knowledge_base:
            # 使用当前任务的action作为查询
            query = current_task.action
            knowledge_items = await self.knowledge_base.query(query, limit=3)

            # 转换知识条目为消息格式
            for item in knowledge_items:
                context_messages.append(
                    {
                        "role": "system",
                        "content": f"📚 Knowledge: {item.content}\n(Source: {item.source})",
                    }
                )

        # 4. 添加当前任务
        current_task_messages = self.converter.convert_tasks_to_messages([current_task])
        context_messages.extend(current_task_messages)

        # 5. 添加系统提示词
        final_messages = []
        if self.system_prompt:
            final_messages.append({"role": "system", "content": self.system_prompt})

        final_messages.extend(context_messages)

        # 5. Token 限制处理（硬限制，由框架强制执行）
        return self._fit_to_token_limit(final_messages)

    def _fit_to_token_limit(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """
        确保消息列表不超过 token 限制

        策略：
        1. 始终保留 System Message
        2. 始终保留最后 N 条消息 (Recent)
        3. 如果超出，丢弃中间的消息
        """
        current_tokens = self.token_counter.count_messages(messages)
        if current_tokens <= self.max_tokens:
            return messages

        # 分离 System 消息
        system_msg = None
        other_messages = []

        if messages and messages[0]["role"] == "system":
            system_msg = messages[0]
            other_messages = messages[1:]
        else:
            other_messages = messages

        # 计算 System token
        system_tokens = self.token_counter.count_messages([system_msg]) if system_msg else 0
        available_tokens = self.max_tokens - system_tokens

        if available_tokens <= 0:
            # 极端情况：系统提示词都放不下，只返回 System Message
            return [system_msg] if system_msg else []

        # 从后往前添加，直到填满
        kept_messages = []
        current_count = 0

        for msg in reversed(other_messages):
            msg_tokens = self.token_counter.count_messages([msg])
            if current_count + msg_tokens > available_tokens:
                break
            kept_messages.insert(0, msg)
            current_count += msg_tokens

        if system_msg:
            return [system_msg] + kept_messages
        return kept_messages
