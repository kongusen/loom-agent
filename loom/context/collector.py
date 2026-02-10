"""
Context Collector - 上下文收集器

协调多个上下文源，按预算收集上下文块。
"""

import asyncio
from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.budget import BudgetAllocation
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


class ContextCollector:
    """
    上下文收集器

    职责：
    1. 协调多个上下文源
    2. 按预算分配收集上下文
    3. 合并和排序结果
    """

    def __init__(
        self,
        sources: list[ContextSource],
        token_counter: "TokenCounter",
    ):
        """
        初始化收集器

        Args:
            sources: 上下文源列表
            token_counter: Token 计数器
        """
        self.sources = sources
        self.token_counter = token_counter
        self._source_map = {s.source_name: s for s in sources}

    async def collect(
        self,
        query: str,
        allocation: BudgetAllocation,
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """
        从所有源收集上下文

        Args:
            query: 当前任务内容
            allocation: 预算分配
            min_relevance: 最低相关性阈值

        Returns:
            按 priority 降序排列的 ContextBlock 列表
        """
        # 并行从各源收集
        tasks = []
        for source in self.sources:
            budget = allocation.get(source.source_name)
            if budget > 0:
                tasks.append(
                    self._collect_from_source(
                        source, query, budget, min_relevance
                    )
                )

        # 等待所有源完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_blocks: list[ContextBlock] = []
        for result in results:
            if isinstance(result, list):
                all_blocks.extend(result)
            # 忽略异常，继续处理其他源的结果

        # 按 priority 降序排序
        all_blocks.sort(key=lambda b: b.priority, reverse=True)

        return all_blocks

    async def _collect_from_source(
        self,
        source: ContextSource,
        query: str,
        budget: int,
        min_relevance: float,
    ) -> list[ContextBlock]:
        """从单个源收集"""
        return await source.collect(
            query=query,
            token_budget=budget,
            token_counter=self.token_counter,
            min_relevance=min_relevance,
        )

    async def collect_from_specific(
        self,
        query: str,
        source_budgets: dict[str, int],
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """
        从指定源收集

        Args:
            query: 当前任务内容
            source_budgets: 源名称 -> 预算
            min_relevance: 最低相关性阈值

        Returns:
            按 priority 降序排列的 ContextBlock 列表
        """
        tasks = []
        for source_name, budget in source_budgets.items():
            source = self._source_map.get(source_name)
            if source and budget > 0:
                tasks.append(
                    self._collect_from_source(
                        source, query, budget, min_relevance
                    )
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_blocks: list[ContextBlock] = []
        for result in results:
            if isinstance(result, list):
                all_blocks.extend(result)

        all_blocks.sort(key=lambda b: b.priority, reverse=True)
        return all_blocks
