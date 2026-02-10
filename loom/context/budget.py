"""
Token Budget - Token 预算管理

基于 Anthropic Context Engineering 思想：
- Token-First Design: 所有操作以 token 为单位
- 预留输出空间: 不要塞满上下文窗口
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


@dataclass
class TokenBudget:
    """
    Token 预算

    Attributes:
        total: 模型上下文窗口大小
        reserved_output: 预留给输出的 token
        system_prompt: 系统提示词占用的 token
    """

    total: int
    reserved_output: int = 0
    system_prompt: int = 0

    @property
    def available(self) -> int:
        """可用于上下文的 token 数"""
        return max(0, self.total - self.reserved_output - self.system_prompt)

    @property
    def used(self) -> int:
        """已使用的 token 数"""
        return self.system_prompt

    @property
    def remaining(self) -> int:
        """剩余可用 token 数"""
        return self.available


@dataclass
class BudgetAllocation:
    """
    预算分配结果

    将可用预算分配给各个上下文源
    """

    allocations: dict[str, int] = field(default_factory=dict)

    def get(self, source_name: str) -> int:
        """获取某个源的预算"""
        return self.allocations.get(source_name, 0)

    @property
    def total_allocated(self) -> int:
        """总分配量"""
        return sum(self.allocations.values())


# 默认预算分配比例（7大上下文来源）
# 注意：output_reserve_ratio 单独配置，这里的比例是剩余可用空间的分配
DEFAULT_ALLOCATION_RATIOS: dict[str, float] = {
    # 固定开销（高优先级，不可压缩）
    "system_prompt": 0.12,  # 系统提示词
    "user_input": 0.12,     # 用户输入
    "tools": 0.15,          # 工具定义
    "skills": 0.10,         # 技能定义
    # 动态内容（可压缩）
    "L1_recent": 0.18,      # 最近任务
    "L2_important": 0.12,   # 重要任务
    "L4_semantic": 0.06,    # 语义检索
    "RAG_knowledge": 0.10,  # 知识库
    "agent_output": 0.05,   # Agent输出
}

# 旧版兼容比例（仅 Memory 源）
LEGACY_ALLOCATION_RATIOS: dict[str, float] = {
    "L1_recent": 0.25,
    "L2_important": 0.20,
    "L3_summary": 0.15,
    "L4_semantic": 0.15,
    "RAG_knowledge": 0.15,
    "INHERITED": 0.10,
}


class BudgetManager:
    """
    预算管理器

    负责：
    1. 计算可用预算
    2. 按比例分配给各源
    3. 动态调整分配
    """

    def __init__(
        self,
        token_counter: "TokenCounter",
        model_context_window: int,
        output_reserve_ratio: float = 0.25,
        allocation_ratios: dict[str, float] | None = None,
    ):
        """
        初始化预算管理器

        Args:
            token_counter: Token 计数器
            model_context_window: 模型上下文窗口大小
            output_reserve_ratio: 预留给输出的比例 (默认 25%)
            allocation_ratios: 各源的分配比例
        """
        self.token_counter = token_counter
        self.model_context_window = model_context_window
        self.output_reserve_ratio = output_reserve_ratio
        self.allocation_ratios = self._normalize_ratios(
            allocation_ratios or DEFAULT_ALLOCATION_RATIOS
        )

    def _normalize_ratios(self, ratios: dict[str, float]) -> dict[str, float]:
        """归一化比例，确保总和为 1.0"""
        total = sum(ratios.values())
        if total <= 0:
            return DEFAULT_ALLOCATION_RATIOS.copy()
        return {k: v / total for k, v in ratios.items()}

    def create_budget(self, system_prompt: str = "") -> TokenBudget:
        """
        创建 Token 预算

        Args:
            system_prompt: 系统提示词

        Returns:
            TokenBudget 对象
        """
        reserved_output = int(self.model_context_window * self.output_reserve_ratio)

        system_tokens = 0
        if system_prompt:
            system_tokens = self.token_counter.count_messages(
                [{"role": "system", "content": system_prompt}]
            )

        return TokenBudget(
            total=self.model_context_window,
            reserved_output=reserved_output,
            system_prompt=system_tokens,
        )

    def allocate(self, budget: TokenBudget) -> BudgetAllocation:
        """
        分配预算给各源

        Args:
            budget: Token 预算

        Returns:
            BudgetAllocation 对象
        """
        available = budget.available
        allocations = {
            source: int(available * ratio)
            for source, ratio in self.allocation_ratios.items()
        }
        return BudgetAllocation(allocations=allocations)

    def allocate_for_sources(
        self,
        budget: TokenBudget,
        source_names: list[str],
    ) -> BudgetAllocation:
        """
        只为指定的源分配预算

        Args:
            budget: Token 预算
            source_names: 需要分配的源名称列表

        Returns:
            BudgetAllocation 对象
        """
        available = budget.available

        # 筛选出需要的源及其比例
        filtered_ratios = {
            name: self.allocation_ratios.get(name, 0.1)
            for name in source_names
        }

        # 重新归一化
        normalized = self._normalize_ratios(filtered_ratios)

        allocations = {
            source: int(available * ratio)
            for source, ratio in normalized.items()
        }
        return BudgetAllocation(allocations=allocations)
