"""
Recursive Budget Control - 递归预算控制

基于A3公理（分形自相似公理）：
实现递归任务的预算控制和质量反馈。

核心功能：
1. 递归预算配置（深度、子节点数、token、时间）
2. 预算跟踪与强制执行
3. 质量指标评估（LLM-as-a-judge）

设计理念：
- Agent 仍自主决策是否分解任务
- 框架提供预算约束和质量反馈
- 超出预算时返回拒绝原因和建议
- 质量评估由LLM自我判断，而非启发式规则
"""

import contextlib
import json
import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.providers.llm.interface import LLMProvider

logger = logging.getLogger(__name__)


class BudgetViolationType(Enum):
    """预算违规类型"""

    MAX_DEPTH = "max_depth"
    MAX_CHILDREN = "max_children"
    TOKEN_BUDGET = "token_budget"
    TIME_BUDGET = "time_budget"
    TOOL_BUDGET = "tool_budget"


@dataclass
class RecursiveBudget:
    """
    递归预算配置

    Attributes:
        max_depth: 最大递归深度（默认5）
        max_children: 单节点最大子节点数（默认10）
        token_budget: Token预算（默认100000）
        time_budget_seconds: 时间预算秒数（默认300）
        tool_budget: 工具调用预算（默认50）
    """

    max_depth: int = 5
    max_children: int = 10
    token_budget: int = 100000
    time_budget_seconds: float = 300.0
    tool_budget: int = 50


@dataclass
class BudgetViolation:
    """
    预算违规信息

    Attributes:
        violation_type: 违规类型
        current_value: 当前值
        limit_value: 限制值
        message: 违规消息
        suggestion: 建议替代方案
    """

    violation_type: BudgetViolationType
    current_value: float
    limit_value: float
    message: str
    suggestion: str = ""


@dataclass
class BudgetUsage:
    """
    预算使用情况

    Attributes:
        current_depth: 当前递归深度
        total_children: 总子节点数
        tokens_used: 已使用token数
        time_elapsed: 已用时间（秒）
        tools_called: 已调用工具数
    """

    current_depth: int = 0
    total_children: int = 0
    tokens_used: int = 0
    time_elapsed: float = 0.0
    tools_called: int = 0


@dataclass
class QualityMetrics:
    """
    质量指标

    用于评估子任务执行质量，形成反馈闭环。

    Attributes:
        confidence: 置信度（0-1），表示结果的可靠程度
        coverage: 覆盖度（0-1），表示任务完成的完整程度
        novelty: 新颖度（0-1），表示结果包含的新信息量
        success: 是否成功完成
        error_count: 错误数量
        retry_count: 重试次数
    """

    confidence: float = 0.0
    coverage: float = 0.0
    novelty: float = 0.0
    success: bool = True
    error_count: int = 0
    retry_count: int = 0

    @property
    def overall_score(self) -> float:
        """综合质量分数"""
        if not self.success:
            return 0.0
        # 加权平均：置信度40%，覆盖度40%，新颖度20%
        base_score = self.confidence * 0.4 + self.coverage * 0.4 + self.novelty * 0.2
        # 错误和重试惩罚
        penalty = min(0.3, (self.error_count * 0.1 + self.retry_count * 0.05))
        return max(0.0, base_score - penalty)


class BudgetTracker:
    """
    预算跟踪器

    跟踪递归任务的预算使用情况，并在超出预算时提供反馈。
    """

    def __init__(self, budget: RecursiveBudget | None = None):
        """
        初始化预算跟踪器

        Args:
            budget: 递归预算配置
        """
        self.budget = budget or RecursiveBudget()
        self._start_time = time.time()
        self._usage = BudgetUsage()
        self._children_by_node: dict[str, int] = {}

    @property
    def usage(self) -> BudgetUsage:
        """获取当前预算使用情况"""
        self._usage.time_elapsed = time.time() - self._start_time
        return self._usage

    def check_can_create_child(
        self,
        parent_node_id: str,
        current_depth: int,
    ) -> BudgetViolation | None:
        """
        检查是否可以创建子节点

        Args:
            parent_node_id: 父节点ID
            current_depth: 当前递归深度

        Returns:
            如果违规返回BudgetViolation，否则返回None
        """
        # 检查深度限制
        if current_depth >= self.budget.max_depth:
            return BudgetViolation(
                violation_type=BudgetViolationType.MAX_DEPTH,
                current_value=current_depth,
                limit_value=self.budget.max_depth,
                message=f"已达到最大递归深度 {self.budget.max_depth}",
                suggestion="考虑简化任务或增加max_depth配置",
            )

        # 检查子节点数限制
        children_count = self._children_by_node.get(parent_node_id, 0)
        if children_count >= self.budget.max_children:
            return BudgetViolation(
                violation_type=BudgetViolationType.MAX_CHILDREN,
                current_value=children_count,
                limit_value=self.budget.max_children,
                message=f"节点 {parent_node_id} 已达到最大子节点数 {self.budget.max_children}",
                suggestion="考虑合并子任务或增加max_children配置",
            )

        # 检查时间预算
        elapsed = time.time() - self._start_time
        if elapsed >= self.budget.time_budget_seconds:
            return BudgetViolation(
                violation_type=BudgetViolationType.TIME_BUDGET,
                current_value=elapsed,
                limit_value=self.budget.time_budget_seconds,
                message=f"已超出时间预算 {self.budget.time_budget_seconds}秒",
                suggestion="考虑简化任务或增加time_budget_seconds配置",
            )

        # 检查token预算
        if self._usage.tokens_used >= self.budget.token_budget:
            return BudgetViolation(
                violation_type=BudgetViolationType.TOKEN_BUDGET,
                current_value=self._usage.tokens_used,
                limit_value=self.budget.token_budget,
                message=f"已超出token预算 {self.budget.token_budget}",
                suggestion="考虑简化任务或增加token_budget配置",
            )

        return None

    def record_child_created(self, parent_node_id: str) -> None:
        """
        记录子节点创建

        Args:
            parent_node_id: 父节点ID
        """
        self._children_by_node[parent_node_id] = self._children_by_node.get(parent_node_id, 0) + 1
        self._usage.total_children += 1

    def record_depth(self, depth: int) -> None:
        """
        记录当前深度

        Args:
            depth: 当前递归深度
        """
        self._usage.current_depth = max(self._usage.current_depth, depth)

    def record_tokens(self, tokens: int) -> None:
        """
        记录token使用

        Args:
            tokens: 使用的token数
        """
        self._usage.tokens_used += tokens

    def record_tool_call(self) -> None:
        """记录工具调用"""
        self._usage.tools_called += 1

    def get_remaining_budget(self) -> dict[str, float]:
        """
        获取剩余预算

        Returns:
            各项剩余预算的字典
        """
        elapsed = time.time() - self._start_time
        return {
            "depth_remaining": self.budget.max_depth - self._usage.current_depth,
            "tokens_remaining": self.budget.token_budget - self._usage.tokens_used,
            "time_remaining": self.budget.time_budget_seconds - elapsed,
            "tools_remaining": self.budget.tool_budget - self._usage.tools_called,
        }

    def reset(self) -> None:
        """重置预算跟踪器"""
        self._start_time = time.time()
        self._usage = BudgetUsage()
        self._children_by_node.clear()


class QualityEvaluator:
    """
    质量评估器（LLM-as-a-judge）

    使用LLM自我评估子任务执行结果的质量，形成反馈闭环。

    评估维度：
    - confidence: 结果的可靠程度
    - coverage: 任务完成的完整程度
    - novelty: 结果包含的新信息量
    """

    def __init__(self, provider: "LLMProvider | None" = None):
        """
        初始化质量评估器

        Args:
            provider: LLM provider（可选，有则使用LLM评估，无则使用默认值）
        """
        self._provider = provider

    async def evaluate(
        self,
        task_description: str,
        result: dict[str, Any],
        parent_context: str = "",
    ) -> QualityMetrics:
        """
        评估任务执行质量

        自动选择评估方式：有provider用LLM，无则用默认值。

        Args:
            task_description: 任务描述
            result: 执行结果
            parent_context: 父节点上下文

        Returns:
            质量指标
        """
        metrics = QualityMetrics()
        metrics.success = result.get("success", True)
        metrics.error_count = 1 if result.get("error") else 0

        if not metrics.success:
            return metrics

        # 有provider则使用LLM评估
        if self._provider:
            return await self._evaluate_with_llm(task_description, result, parent_context, metrics)

        # 无provider则使用默认值
        metrics.confidence = 0.6
        metrics.coverage = 0.6
        metrics.novelty = 0.5
        return metrics

    async def _evaluate_with_llm(
        self,
        task_description: str,
        result: dict[str, Any],
        parent_context: str,
        metrics: QualityMetrics,
    ) -> QualityMetrics:
        """使用LLM进行评估"""
        provider = self._provider
        if provider is None:
            metrics.confidence = 0.5
            metrics.coverage = 0.5
            metrics.novelty = 0.5
            return metrics
        prompt = self._build_evaluation_prompt(task_description, result, parent_context)

        try:
            response = await provider.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
            )
            parsed = self._parse_llm_response(response.content)
            metrics.confidence = parsed.get("confidence", 0.5)
            metrics.coverage = parsed.get("coverage", 0.5)
            metrics.novelty = parsed.get("novelty", 0.5)
        except Exception as e:
            logger.warning(f"LLM评估失败，使用默认值: {e}")
            metrics.confidence = 0.5
            metrics.coverage = 0.5
            metrics.novelty = 0.5

        return metrics

    def _build_evaluation_prompt(
        self,
        task_description: str,
        result: dict[str, Any],
        parent_context: str,
    ) -> str:
        """构建评估提示词"""
        result_content = str(result.get("result", result.get("content", "")))

        prompt = f"""请评估以下任务执行结果的质量。

任务描述：
{task_description}

执行结果：
{result_content}
"""
        if parent_context:
            prompt += f"""
父任务上下文：
{parent_context[:500]}...
"""

        prompt += """
请从三个维度评估（0-1分）：
1. confidence（置信度）: 结果是否准确完整
2. coverage（覆盖度）: 是否完整回答任务要求
3. novelty（新颖度）: 提供了多少新信息

返回JSON：{"confidence": 0.X, "coverage": 0.X, "novelty": 0.X}
"""
        return prompt

    def _parse_llm_response(self, response: str) -> dict[str, float]:
        """解析LLM响应"""
        json_match = re.search(r"\{[^}]+\}", response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return {
                    "confidence": float(data.get("confidence", 0.5)),
                    "coverage": float(data.get("coverage", 0.5)),
                    "novelty": float(data.get("novelty", 0.5)),
                }
            except (json.JSONDecodeError, ValueError):
                pass

        defaults = {"confidence": 0.5, "coverage": 0.5, "novelty": 0.5}
        for key in defaults:
            pattern = rf"{key}[:\s]+([0-9.]+)"
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                with contextlib.suppress(ValueError):
                    defaults[key] = min(1.0, max(0.0, float(match.group(1))))
        return defaults
