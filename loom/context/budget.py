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


# 默认预算分配比例（两级分配模型）
# 注意：output_reserve_ratio 单独配置，这里的比例是剩余可用空间的分配
#
# 两级分配：
#   固定区 (~40%): system_prompt + user_input + tools + skills
#   对话区 (~35%): L1_recent + L2_important + agent_output
#   检索区 (~25%): retrieval（L4 和 RAG 在共享池中按相关性竞争）
DEFAULT_ALLOCATION_RATIOS: dict[str, float] = {
    # 固定区（高优先级，不可压缩）
    "system_prompt": 0.12,  # 系统提示词
    "user_input": 0.12,  # 用户输入
    "tools": 0.11,  # 工具定义
    "skills": 0.05,  # 技能定义
    # 对话区（可压缩）
    "L1_recent": 0.18,  # 最近任务
    "L2_important": 0.10,  # 重要任务
    "agent_output": 0.05,  # Agent输出
    # 共享区（跨 Agent 共享记忆）
    "shared_pool": 0.05,  # SharedMemoryPool 共享记忆
    # 检索区（L4 + RAG 共享池）
    "retrieval": 0.22,  # 统一检索（L4 语义 + RAG 知识库竞争）
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
            source: int(available * ratio) for source, ratio in self.allocation_ratios.items()
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
        filtered_ratios = {name: self.allocation_ratios.get(name, 0.1) for name in source_names}

        # 重新归一化
        normalized = self._normalize_ratios(filtered_ratios)

        allocations = {source: int(available * ratio) for source, ratio in normalized.items()}
        return BudgetAllocation(allocations=allocations)


# ============ 自适应预算策略 ============


class TaskPhase:
    """任务阶段（基于迭代进度推断）"""

    EARLY = "early"  # 前 30% 迭代
    MIDDLE = "middle"  # 30-70%
    LATE = "late"  # 后 30%

    @staticmethod
    def from_progress(current_iteration: int, max_iterations: int) -> str:
        if max_iterations <= 0:
            return TaskPhase.MIDDLE
        ratio = current_iteration / max_iterations
        if ratio < 0.3:
            return TaskPhase.EARLY
        elif ratio < 0.7:
            return TaskPhase.MIDDLE
        return TaskPhase.LATE


# 各阶段的预算分配模板（两级分配模型）
PHASE_ALLOCATION_TEMPLATES: dict[str, dict[str, float]] = {
    TaskPhase.EARLY: {
        # 固定区偏重（理解任务阶段）
        "system_prompt": 0.18,
        "tools": 0.15,
        "skills": 0.12,
        # 对话区
        "L1_recent": 0.17,
        "L2_important": 0.10,
        # 共享区
        "shared_pool": 0.03,
        # 检索区
        "retrieval": 0.20,
        "INHERITED": 0.05,
    },
    TaskPhase.MIDDLE: {
        # 对话区偏重（执行任务阶段）
        "system_prompt": 0.10,
        "tools": 0.10,
        "skills": 0.06,
        "L1_recent": 0.26,
        "L2_important": 0.16,
        # 共享区（协作高峰期）
        "shared_pool": 0.06,
        "retrieval": 0.20,
        "INHERITED": 0.06,
    },
    TaskPhase.LATE: {
        # 继承+检索偏重（保持一致性阶段）
        "system_prompt": 0.08,
        "tools": 0.08,
        "skills": 0.04,
        "L1_recent": 0.17,
        "L2_important": 0.11,
        # 共享区
        "shared_pool": 0.04,
        "retrieval": 0.18,
        "INHERITED": 0.30,
    },
}


class AdaptiveBudgetManager(BudgetManager):
    """
    自适应预算管理器

    根据任务阶段动态调整各上下文源的预算分配比例。
    - 初期：侧重 system prompt + skill context（理解任务）
    - 中期：侧重 L1/L2 工作记忆（执行任务）
    - 后期：侧重 L3/inherited 历史摘要（保持一致性）

    用法：
        manager = AdaptiveBudgetManager(
            token_counter=counter,
            model_context_window=128000,
        )
        # 每次迭代时更新阶段
        manager.update_phase(current_iteration=15, max_iterations=30)
        budget = manager.create_budget(system_prompt)
        allocation = manager.allocate_for_sources(budget, source_names)
    """

    def __init__(
        self,
        token_counter: "TokenCounter",
        model_context_window: int,
        output_reserve_ratio: float = 0.25,
        allocation_ratios: dict[str, float] | None = None,
        phase_templates: dict[str, dict[str, float]] | None = None,
    ):
        super().__init__(
            token_counter=token_counter,
            model_context_window=model_context_window,
            output_reserve_ratio=output_reserve_ratio,
            allocation_ratios=allocation_ratios,
        )
        self._phase = TaskPhase.EARLY
        self._phase_templates = phase_templates or PHASE_ALLOCATION_TEMPLATES

    @property
    def current_phase(self) -> str:
        return self._phase

    def update_phase(self, current_iteration: int, max_iterations: int) -> str:
        """根据迭代进度更新阶段，并切换预算分配"""
        self._phase = TaskPhase.from_progress(current_iteration, max_iterations)
        template = self._phase_templates.get(self._phase)
        if template:
            self.allocation_ratios = self._normalize_ratios(template)
        return self._phase
