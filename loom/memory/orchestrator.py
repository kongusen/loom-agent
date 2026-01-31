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
    ContextBudgeter,
    ContextSource,
    MessageConverter,
    BudgetConfig,
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

        Args:
            current_task: 当前任务

        Returns:
            OpenAI 格式的消息列表
        """
        # TODO: Implement in Task 7
        raise NotImplementedError
