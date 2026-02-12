"""
Context Orchestrator - 上下文编排器

统一入口，整合预算管理、收集、压缩。
基于 Anthropic Context Engineering 思想。
"""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.budget import BudgetManager
from loom.context.collector import ContextCollector
from loom.context.compactor import ContextCompactor
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


class ContextOrchestrator:
    """
    上下文编排器 - 统一入口

    职责：
    1. 管理 token 预算
    2. 协调上下文收集
    3. 必要时压缩上下文
    4. 输出 LLM 消息格式
    """

    def __init__(
        self,
        token_counter: "TokenCounter",
        sources: list[ContextSource],
        model_context_window: int = 128000,
        output_reserve_ratio: float = 0.25,
        allocation_ratios: dict[str, float] | None = None,
        summarizer: Callable[[str], Awaitable[str]] | None = None,
        budget_manager: BudgetManager | None = None,
    ):
        """
        初始化编排器

        Args:
            token_counter: Token 计数器
            sources: 上下文源列表
            model_context_window: 模型上下文窗口大小
            output_reserve_ratio: 预留给输出的比例
            allocation_ratios: 各源的预算分配比例
            summarizer: 摘要生成函数（用于压缩）
            budget_manager: 预算管理器（可选，默认创建 BudgetManager）
        """
        self.token_counter = token_counter
        self.sources = sources

        # 预算管理器（支持外部注入，如 AdaptiveBudgetManager）
        if budget_manager is not None:
            self.budget_manager = budget_manager
        else:
            self.budget_manager = BudgetManager(
                token_counter=token_counter,
                model_context_window=model_context_window,
                output_reserve_ratio=output_reserve_ratio,
                allocation_ratios=allocation_ratios,
            )

        # 收集器
        self.collector = ContextCollector(
            sources=sources,
            token_counter=token_counter,
        )

        # 压缩器
        self.compactor = ContextCompactor(
            token_counter=token_counter,
            summarizer=summarizer,
        )

    @property
    def max_tokens(self) -> int:
        """获取模型上下文窗口大小（兼容属性）"""
        return self.budget_manager.model_context_window

    async def build_context(
        self,
        query: str,
        system_prompt: str = "",
        min_relevance: float = 0.5,
    ) -> list[dict[str, str]]:
        """
        构建 LLM 上下文

        Args:
            query: 当前任务/查询内容
            system_prompt: 系统提示词
            min_relevance: 最低相关性阈值

        Returns:
            LLM 消息列表
        """
        # 1. 创建预算
        budget = self.budget_manager.create_budget(system_prompt)

        # 2. 分配预算给各源
        source_names = [s.source_name for s in self.sources]
        allocation = self.budget_manager.allocate_for_sources(budget, source_names)

        # 3. 收集上下文
        blocks = await self.collector.collect(
            query=query,
            allocation=allocation,
            min_relevance=min_relevance,
        )

        # 4. 检查是否需要压缩
        total_tokens = sum(b.token_count for b in blocks)
        if total_tokens > budget.available:
            blocks = await self.compactor.compact(blocks, budget.available)

        # 5. 转换为消息格式
        return self._blocks_to_messages(blocks, system_prompt)

    def _blocks_to_messages(
        self,
        blocks: list[ContextBlock],
        system_prompt: str,
    ) -> list[dict[str, str]]:
        """将块转换为 LLM 消息格式"""
        messages: list[dict[str, str]] = []

        # 系统提示词
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 按 role 分组，合并相邻同 role 的消息
        for block in blocks:
            messages.append(block.to_message())

        return messages

    def get_budget_info(self, system_prompt: str = "") -> dict:
        """获取预算信息（用于调试）"""
        budget = self.budget_manager.create_budget(system_prompt)
        source_names = [s.source_name for s in self.sources]
        allocation = self.budget_manager.allocate_for_sources(budget, source_names)

        return {
            "total": budget.total,
            "reserved_output": budget.reserved_output,
            "system_prompt": budget.system_prompt,
            "available": budget.available,
            "allocation": allocation.allocations,
        }
