"""
上下文管理 - Context Management

基于第一性原理的上下文管理实现。

核心功能：
1. 精确的Token计数（集成TokenCounter）
2. 智能的消息选择策略
3. 可配置的上下文限制

设计原则：
- 策略模式：支持多种上下文选择策略
- 精确计数：使用TokenCounter而非估算
- 优先级保留：重要消息优先保留
"""

from abc import ABC, abstractmethod

from loom.memory.tokenizer import TokenCounter
from loom.memory.types import MemoryUnit


class ContextStrategy(ABC):
    """
    上下文选择策略抽象基类

    定义上下文选择的统一接口。
    """

    @abstractmethod
    def select_context(
        self,
        units: list[MemoryUnit],
        max_tokens: int,
        token_counter: TokenCounter,
    ) -> list[MemoryUnit]:
        """
        从记忆单元列表中选择上下文

        Args:
            units: 候选记忆单元列表
            max_tokens: 最大token数限制
            token_counter: Token计数器

        Returns:
            选中的记忆单元列表
        """
        pass


class PriorityContextStrategy(ContextStrategy):
    """
    基于优先级的上下文选择策略

    选择规则：
    1. 按importance排序
    2. 优先保留高importance的记忆单元
    3. 在token限制内尽可能多地保留
    """

    def select_context(
        self,
        units: list[MemoryUnit],
        max_tokens: int,
        token_counter: TokenCounter,
    ) -> list[MemoryUnit]:
        """选择高优先级的记忆单元"""
        if not units:
            return []

        # 按importance降序排序
        sorted_units = sorted(units, key=lambda u: u.importance, reverse=True)

        selected = []
        current_tokens = 0

        for unit in sorted_units:
            # 计算当前单元的token数
            unit_tokens = token_counter.count(str(unit.content))

            # 检查是否超过限制
            if current_tokens + unit_tokens <= max_tokens:
                selected.append(unit)
                current_tokens += unit_tokens
            else:
                # 已达到token限制
                break

        return selected


class SlidingWindowStrategy(ContextStrategy):
    """
    滑动窗口策略

    选择规则：
    1. 保留最近的N个记忆单元
    2. 按时间顺序（created_at）排序
    3. 在token限制内从最新开始选择
    """

    def select_context(
        self,
        units: list[MemoryUnit],
        max_tokens: int,
        token_counter: TokenCounter,
    ) -> list[MemoryUnit]:
        """选择最近的记忆单元"""
        if not units:
            return []

        # 按时间降序排序（最新的在前）
        sorted_units = sorted(units, key=lambda u: u.created_at, reverse=True)

        selected = []
        current_tokens = 0

        for unit in sorted_units:
            # 计算当前单元的token数
            unit_tokens = token_counter.count(str(unit.content))

            # 检查是否超过限制
            if current_tokens + unit_tokens <= max_tokens:
                selected.append(unit)
                current_tokens += unit_tokens
            else:
                break

        # 恢复时间顺序（旧的在前）
        selected.reverse()
        return selected


class ContextManager:
    """
    上下文管理器

    负责管理上下文的构建和选择。

    使用方式：
        manager = ContextManager(
            token_counter=TiktokenCounter("gpt-4"),
            strategy=PriorityContextStrategy(),
            max_tokens=4000
        )
        context = manager.build_context(memory_units)
    """

    def __init__(
        self,
        token_counter: TokenCounter,
        strategy: ContextStrategy | None = None,
        max_tokens: int = 4000,
    ):
        """
        初始化上下文管理器

        Args:
            token_counter: Token计数器
            strategy: 上下文选择策略（默认使用滑动窗口）
            max_tokens: 最大token数限制
        """
        self.token_counter = token_counter
        self.strategy = strategy or SlidingWindowStrategy()
        self.max_tokens = max_tokens

    def build_context(
        self,
        units: list[MemoryUnit],
        max_tokens: int | None = None,
    ) -> list[MemoryUnit]:
        """
        构建上下文

        Args:
            units: 候选记忆单元列表
            max_tokens: 最大token数（覆盖默认值）

        Returns:
            选中的记忆单元列表
        """
        tokens = max_tokens or self.max_tokens
        return self.strategy.select_context(units, tokens, self.token_counter)
