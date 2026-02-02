"""
Context Orchestrator - 上下文编排器

统一的上下文构建逻辑，整合：
- Token 预算管理（来自 ContextBudgeter）
- 上下文源管理（来自 ContextSource）
- 消息转换（来自 MessageConverter）
- 语义投影（简化版）

设计原则：
1. 单一职责 - 只负责上下文构建，不负责存储
2. 清晰接口 - build_context() 一个核心方法
3. 可扩展 - 支持多个上下文源
"""

from typing import Any

from loom.memory.task_context import (
    BudgetConfig,
    ContextBudgeter,
    ContextSource,
    MessageConverter,
)
from loom.memory.tokenizer import TokenCounter
from loom.protocol import Task


class ContextOrchestrator:
    """
    上下文编排器

    整合 token 预算、上下文源、消息转换。
    """

    def __init__(
        self,
        token_counter: TokenCounter,
        sources: list[ContextSource],
        max_tokens: int = 4000,
        system_prompt: str = "",
        budget_config: BudgetConfig | None = None,
    ):
        """
        初始化上下文编排器

        Args:
            token_counter: Token 计数器
            sources: 上下文源列表
            max_tokens: 最大 token 数
            system_prompt: 系统提示词
            budget_config: 预算配置
        """
        self.token_counter = token_counter
        self.sources = sources
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

        # 创建预算分配器
        self.budgeter = ContextBudgeter(
            token_counter=token_counter,
            max_tokens=max_tokens,
            config=budget_config or BudgetConfig(),
        )

        # 创建消息转换器
        self.converter = MessageConverter()

    async def build_context(self, current_task: Task) -> list[dict[str, str]]:
        """
        构建 LLM 上下文

        流程：
        1. 计算 token 预算
        2. 从各个源收集上下文
        3. 转换为消息格式
        4. 应用 token 限制
        """
        # 1. 计算预算
        system_tokens = (
            self.token_counter.count_messages([{"role": "system", "content": self.system_prompt}])
            if self.system_prompt
            else 0
        )
        _budget = self.budgeter.allocate_budget(system_prompt_tokens=system_tokens)

        # 2. 从各个源收集上下文任务
        context_tasks: list[Task] = []
        for source in self.sources:
            tasks = await source.get_context(current_task, max_items=20)
            context_tasks.extend(tasks)

        # 3. 按 session_id 过滤
        if current_task.session_id:
            context_tasks = [t for t in context_tasks if t.session_id == current_task.session_id]

        # 4. 去重
        seen_ids = set()
        unique_tasks = []
        for task in context_tasks:
            if task.task_id not in seen_ids:
                unique_tasks.append(task)
                seen_ids.add(task.task_id)

        # 5. 转换为消息
        context_messages = self.converter.convert_tasks_to_messages(unique_tasks)
        current_messages = self.converter.convert_tasks_to_messages([current_task])

        # 6. 组装最终消息
        final_messages: list[dict[str, str]] = []
        if self.system_prompt:
            final_messages.append({"role": "system", "content": self.system_prompt})

        final_messages.extend(context_messages)
        final_messages.extend(current_messages)

        # 7. 应用 token 限制
        return self._fit_to_token_limit(final_messages)

    def _fit_to_token_limit(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """确保消息不超过 token 限制"""
        current_tokens = self.token_counter.count_messages(messages)
        if current_tokens <= self.max_tokens:
            return messages

        # 保留系统消息 + 最近的消息
        system_messages = [m for m in messages if m.get("role") == "system"]
        other_messages = [m for m in messages if m.get("role") != "system"]

        system_tokens = self.token_counter.count_messages(system_messages)
        available = self.max_tokens - system_tokens

        # 从后往前保留消息
        kept: list[dict[str, Any]] = []
        current = 0
        for msg in reversed(other_messages):
            msg_tokens = self.token_counter.count_messages([msg])
            if current + msg_tokens > available:
                break
            kept.insert(0, msg)
            current += msg_tokens

        return system_messages + kept
