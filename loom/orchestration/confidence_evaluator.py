"""
Confidence Evaluator - 置信度评估器

基于公理A5（认知调度公理）：
评估任务执行结果的质量和置信度，支持重试决策。

功能：
- 多维度评估（完整性、正确性、一致性）
- 可插拔评估策略
- 重试和升级决策
- 评分聚合

设计原则：
1. 多维评估 - 从多个角度评估质量
2. 策略模式 - 支持自定义评估策略
3. 决策支持 - 提供重试和升级建议
"""

from abc import ABC, abstractmethod
from typing import Any

from loom.protocol import Task, TaskStatus


class ConfidenceScore:
    """
    置信度评分

    包含总体置信度和各维度的详细评分。
    """

    def __init__(
        self,
        overall: float,
        dimensions: dict[str, float] | None = None,
        reasons: list[str] | None = None,
    ):
        """
        初始化置信度评分

        Args:
            overall: 总体置信度 (0.0-1.0)
            dimensions: 各维度评分
            reasons: 评分理由
        """
        self.overall = max(0.0, min(1.0, overall))  # 限制在 [0, 1]
        self.dimensions = dimensions or {}
        self.reasons = reasons or []

    def add_dimension(self, name: str, score: float) -> None:
        """
        添加维度评分

        Args:
            name: 维度名称
            score: 评分 (0.0-1.0)
        """
        self.dimensions[name] = max(0.0, min(1.0, score))

    def add_reason(self, reason: str) -> None:
        """
        添加评分理由

        Args:
            reason: 理由说明
        """
        self.reasons.append(reason)

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式

        Returns:
            字典表示
        """
        return {
            "overall": self.overall,
            "dimensions": self.dimensions,
            "reasons": self.reasons,
        }


class EvaluationStrategy(ABC):
    """
    评估策略抽象基类

    定义单个评估维度的接口。
    """

    def __init__(self, name: str, weight: float = 1.0):
        """
        初始化评估策略

        Args:
            name: 策略名称
            weight: 权重 (用于加权平均)
        """
        self.name = name
        self.weight = weight

    @abstractmethod
    async def evaluate(self, task: Task) -> float:
        """
        评估任务

        Args:
            task: 要评估的任务

        Returns:
            评分 (0.0-1.0)
        """
        pass


class ConfidenceEvaluator:
    """
    置信度评估器

    使用多个评估策略对任务结果进行综合评估。
    """

    def __init__(
        self,
        strategies: list[EvaluationStrategy] | None = None,
        retry_threshold: float = 0.6,
        escalate_threshold: float = 0.4,
    ):
        """
        初始化评估器

        Args:
            strategies: 评估策略列表
            retry_threshold: 重试阈值（低于此值建议重试）
            escalate_threshold: 升级阈值（低于此值建议升级）
        """
        self.strategies = strategies or []
        self.retry_threshold = retry_threshold
        self.escalate_threshold = escalate_threshold

        # 如果没有提供策略，使用默认策略
        if not self.strategies:
            self._add_default_strategies()

    def _add_default_strategies(self) -> None:
        """添加默认评估策略"""
        self.add_strategy(StatusBasedStrategy())
        self.add_strategy(ErrorPresenceStrategy())
        self.add_strategy(ResultLengthStrategy())

    def add_strategy(self, strategy: EvaluationStrategy) -> None:
        """
        添加评估策略

        Args:
            strategy: 评估策略
        """
        self.strategies.append(strategy)

    async def evaluate(self, task: Task) -> ConfidenceScore:
        """
        评估任务

        Args:
            task: 要评估的任务

        Returns:
            置信度评分
        """
        if not self.strategies:
            # 没有策略，返回默认评分
            return ConfidenceScore(
                overall=0.5,
                reasons=["No evaluation strategies configured"],
            )

        # 执行所有策略
        dimension_scores = {}
        total_weight = 0.0
        weighted_sum = 0.0

        for strategy in self.strategies:
            try:
                score = await strategy.evaluate(task)
                dimension_scores[strategy.name] = score
                weighted_sum += score * strategy.weight
                total_weight += strategy.weight
            except Exception:
                # 策略执行失败，记录但继续
                dimension_scores[strategy.name] = 0.0

        # 计算加权平均
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        # 生成评分理由
        reasons = self._generate_reasons(overall_score, dimension_scores)

        return ConfidenceScore(
            overall=overall_score,
            dimensions=dimension_scores,
            reasons=reasons,
        )

    def _generate_reasons(self, overall: float, dimensions: dict[str, float]) -> list[str]:
        """
        生成评分理由

        Args:
            overall: 总体评分
            dimensions: 各维度评分

        Returns:
            理由列表
        """
        reasons = []

        # 总体评价
        if overall >= 0.8:
            reasons.append("High confidence: Task executed successfully")
        elif overall >= 0.6:
            reasons.append("Medium confidence: Task completed with minor issues")
        elif overall >= 0.4:
            reasons.append("Low confidence: Task completed with significant issues")
        else:
            reasons.append("Very low confidence: Task likely failed or incomplete")

        # 维度分析
        low_dimensions = [name for name, score in dimensions.items() if score < 0.5]
        if low_dimensions:
            reasons.append(f"Low scores in: {', '.join(low_dimensions)}")

        return reasons

    def should_retry(self, score: ConfidenceScore) -> bool:
        """
        判断是否应该重试

        Args:
            score: 置信度评分

        Returns:
            是否应该重试
        """
        return self.escalate_threshold < score.overall < self.retry_threshold

    def should_escalate(self, score: ConfidenceScore) -> bool:
        """
        判断是否应该升级

        Args:
            score: 置信度评分

        Returns:
            是否应该升级到更强节点
        """
        return score.overall <= self.escalate_threshold


# ==================== 内置评估策略 ====================


class StatusBasedStrategy(EvaluationStrategy):
    """
    基于任务状态的评估策略

    根据任务的执行状态给出评分。
    """

    def __init__(self, weight: float = 1.0):
        super().__init__(name="status", weight=weight)

    async def evaluate(self, task: Task) -> float:
        """
        根据任务状态评估

        Args:
            task: 任务对象

        Returns:
            评分 (0.0-1.0)
        """
        if task.status == TaskStatus.COMPLETED:
            return 1.0
        elif task.status == TaskStatus.RUNNING:
            return 0.5
        elif task.status == TaskStatus.PENDING:
            return 0.3
        else:  # FAILED
            return 0.0


class ErrorPresenceStrategy(EvaluationStrategy):
    """
    基于错误信息的评估策略

    检查任务是否有错误信息。
    """

    def __init__(self, weight: float = 1.0):
        super().__init__(name="error_presence", weight=weight)

    async def evaluate(self, task: Task) -> float:
        """
        检查错误信息

        Args:
            task: 任务对象

        Returns:
            评分 (0.0-1.0)
        """
        # 如果有错误信息，评分为 0
        if task.error:
            return 0.0

        # 没有错误，评分为 1
        return 1.0


class ResultLengthStrategy(EvaluationStrategy):
    """
    基于结果长度的评估策略

    评估结果的完整性（基于长度）。
    """

    def __init__(self, min_length: int = 10, weight: float = 0.5):
        """
        初始化策略

        Args:
            min_length: 最小期望长度
            weight: 权重
        """
        super().__init__(name="result_length", weight=weight)
        self.min_length = min_length

    async def evaluate(self, task: Task) -> float:
        """
        评估结果长度

        Args:
            task: 任务对象

        Returns:
            评分 (0.0-1.0)
        """
        if not task.result:
            return 0.0

        # 将结果转换为字符串并计算长度
        result_str = str(task.result)
        length = len(result_str)

        # 如果长度小于最小值，按比例评分
        if length < self.min_length:
            return length / self.min_length

        # 长度足够，返回满分
        return 1.0
