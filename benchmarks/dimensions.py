"""
评估维度定义 - 六大核心维度

每个维度包含：
- 指标定义 (metrics)
- 评分标准 (scoring criteria)
- 基准对比方法 (benchmark methods)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ScoreLevel(Enum):
    """评分等级"""
    EXCELLENT = "excellent"   # 90-100
    GOOD = "good"             # 70-89
    ADEQUATE = "adequate"     # 50-69
    POOR = "poor"             # 30-49
    FAILING = "failing"       # 0-29


@dataclass
class Metric:
    """单项指标"""
    name: str
    value: float
    unit: str = ""
    weight: float = 1.0
    description: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_value(self) -> float:
        return self.value * self.weight


@dataclass
class DimensionScore:
    """维度评分结果"""
    dimension_name: str
    score: float  # 0-100
    level: ScoreLevel
    metrics: list[Metric]
    analysis: str = ""
    recommendations: list[str] = field(default_factory=list)

    @classmethod
    def from_metrics(cls, name: str, metrics: list[Metric], analysis: str = "") -> DimensionScore:
        if not metrics:
            return cls(name, 0.0, ScoreLevel.FAILING, metrics, analysis)
        total_weight = sum(m.weight for m in metrics)
        if total_weight == 0:
            return cls(name, 0.0, ScoreLevel.FAILING, metrics, analysis)
        score = sum(m.weighted_value for m in metrics) / total_weight
        level = cls._score_to_level(score)
        return cls(name, round(score, 2), level, metrics, analysis)

    @staticmethod
    def _score_to_level(score: float) -> ScoreLevel:
        if score >= 90:
            return ScoreLevel.EXCELLENT
        elif score >= 70:
            return ScoreLevel.GOOD
        elif score >= 50:
            return ScoreLevel.ADEQUATE
        elif score >= 30:
            return ScoreLevel.POOR
        return ScoreLevel.FAILING


class EvaluationDimension(ABC):
    """评估维度抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """维度名称"""

    @property
    @abstractmethod
    def description(self) -> str:
        """维度描述"""

    @property
    @abstractmethod
    def weight(self) -> float:
        """维度权重 (0-1)"""

    @abstractmethod
    async def evaluate(self, context: dict[str, Any]) -> DimensionScore:
        """执行评估，返回维度评分"""


class LongHorizonStabilityDimension(EvaluationDimension):
    """
    维度1: 长程稳定性

    衡量 Agent 在长时间、多步骤任务中的表现衰减程度。
    这是 loom-agent 的核心差异化指标。

    指标：
    - step_completion_rate: 各步骤完成率（第N步 vs 第1步）
    - coherence_decay: 语义连贯性衰减曲线
    - error_cascade_resistance: 错误级联抵抗能力
    - recovery_rate: 从错误中恢复的成功率
    """

    name = "Long-Horizon Stability"
    description = "Agent 在长时间多步骤任务中的稳定性和抗衰减能力"
    weight = 0.25  # 最高权重 — 核心差异化

    async def evaluate(self, context: dict[str, Any]) -> DimensionScore:
        metrics = []
        steps = context.get("step_results", [])
        total_steps = len(steps)

        if total_steps == 0:
            return DimensionScore.from_metrics(self.name, [])

        # 1. 步骤完成率
        completed = sum(1 for s in steps if s.get("completed", False))
        completion_rate = (completed / total_steps) * 100
        metrics.append(Metric(
            name="step_completion_rate",
            value=completion_rate,
            unit="%",
            weight=1.5,
            description="各步骤完成率",
        ))

        # 2. 连贯性衰减 — 比较前半段和后半段的成功率
        mid = total_steps // 2
        if mid > 0:
            first_half = sum(1 for s in steps[:mid] if s.get("completed")) / mid
            second_half = sum(1 for s in steps[mid:] if s.get("completed")) / (total_steps - mid)
            decay = max(0, first_half - second_half)
            coherence_score = max(0, (1 - decay * 2)) * 100
        else:
            coherence_score = completion_rate
        metrics.append(Metric(
            name="coherence_decay",
            value=coherence_score,
            unit="score",
            weight=1.2,
            description="语义连贯性衰减（100=无衰减）",
        ))

        # 3. 错误级联抵抗
        error_cascades = context.get("error_cascades", 0)
        total_errors = context.get("total_errors", 1)
        cascade_resistance = max(0, (1 - error_cascades / max(total_errors, 1))) * 100
        metrics.append(Metric(
            name="error_cascade_resistance",
            value=cascade_resistance,
            unit="score",
            weight=1.0,
            description="错误级联抵抗能力",
        ))

        # 4. 恢复率
        recoveries = context.get("recoveries", 0)
        recovery_rate = (recoveries / max(total_errors, 1)) * 100 if total_errors > 0 else 100
        metrics.append(Metric(
            name="recovery_rate",
            value=min(recovery_rate, 100),
            unit="%",
            weight=1.0,
            description="从错误中恢复的成功率",
        ))

        return DimensionScore.from_metrics(self.name, metrics)


class MemoryEfficiencyDimension(EvaluationDimension):
    """
    维度2: 记忆效率

    衡量记忆系统的 token 利用率和信息保真度。

    指标：
    - token_utilization: Token 预算利用率
    - information_retention: 关键信息保留率
    - compression_ratio: 压缩比（信息密度）
    - retrieval_precision: 检索精度（L4 语义检索）
    """

    name = "Memory Efficiency"
    description = "记忆系统的 token 利用率、信息保真度和检索精度"
    weight = 0.20

    async def evaluate(self, context: dict[str, Any]) -> DimensionScore:
        metrics = []
        memory_stats = context.get("memory_stats", {})

        # 1. Token 利用率
        budget = memory_stats.get("total_budget", 1)
        used = memory_stats.get("tokens_used", 0)
        utilization = min((used / max(budget, 1)) * 100, 100)
        # 最优利用率在 70-90% 之间
        if 70 <= utilization <= 90:
            util_score = 100
        elif utilization < 70:
            util_score = utilization / 0.7
        else:
            util_score = max(0, 100 - (utilization - 90) * 5)
        metrics.append(Metric(
            name="token_utilization",
            value=util_score,
            unit="score",
            weight=1.0,
            description="Token 预算利用率（70-90% 最优）",
        ))

        # 2. 信息保留率
        key_facts_total = memory_stats.get("key_facts_total", 0)
        key_facts_retained = memory_stats.get("key_facts_retained", 0)
        retention = (key_facts_retained / max(key_facts_total, 1)) * 100
        metrics.append(Metric(
            name="information_retention",
            value=retention,
            unit="%",
            weight=1.3,
            description="关键信息保留率",
        ))

        # 3. 压缩比
        original_tokens = memory_stats.get("original_tokens", 1)
        compressed_tokens = memory_stats.get("compressed_tokens", 1)
        ratio = original_tokens / max(compressed_tokens, 1)
        # 压缩比 2-5x 为优秀
        compression_score = min(ratio / 5 * 100, 100)
        metrics.append(Metric(
            name="compression_ratio",
            value=compression_score,
            unit="score",
            weight=0.8,
            description=f"压缩比 {ratio:.1f}x",
            raw_data={"ratio": ratio},
        ))

        # 4. 检索精度
        retrieval_hits = memory_stats.get("retrieval_hits", 0)
        retrieval_total = memory_stats.get("retrieval_total", 0)
        precision = (retrieval_hits / max(retrieval_total, 1)) * 100
        metrics.append(Metric(
            name="retrieval_precision",
            value=precision,
            unit="%",
            weight=1.0,
            description="L4 语义检索精度",
        ))

        return DimensionScore.from_metrics(self.name, metrics)


class ContextQualityDimension(EvaluationDimension):
    """
    维度3: 上下文质量

    指标：
    - relevance_score: 上下文与当前任务的相关性
    - budget_efficiency: 预算分配效率
    - freshness: 上下文新鲜度
    - coverage: 任务所需信息的覆盖率
    """

    name = "Context Quality"
    description = "上下文编排的精准度、预算效率和信息覆盖率"
    weight = 0.18

    async def evaluate(self, context: dict[str, Any]) -> DimensionScore:
        metrics = []
        ctx = context.get("context_stats", {})

        relevance = ctx.get("avg_relevance", 0.5) * 100
        metrics.append(Metric("relevance_score", relevance, "score", 1.3))

        total_t = ctx.get("total_context_tokens", 1)
        useful_t = ctx.get("useful_context_tokens", 0)
        metrics.append(Metric("budget_efficiency", (useful_t / max(total_t, 1)) * 100, "%", 1.0))

        stale = ctx.get("stale_context_ratio", 0)
        metrics.append(Metric("freshness", (1 - stale) * 100, "score", 0.8))

        req = ctx.get("required_facts", 0)
        cov = ctx.get("covered_facts", 0)
        metrics.append(Metric("coverage", (cov / max(req, 1)) * 100, "%", 1.2))

        return DimensionScore.from_metrics(self.name, metrics)


class MultiAgentCoordinationDimension(EvaluationDimension):
    """维度4: 多智能体协作"""

    name = "Multi-Agent Coordination"
    description = "Fractal 架构下多 Agent 委派、通信和结果综合的效率"
    weight = 0.15

    async def evaluate(self, context: dict[str, Any]) -> DimensionScore:
        metrics = []
        cs = context.get("coordination_stats", {})
        delegated = cs.get("tasks_delegated", 0)
        succeeded = cs.get("tasks_succeeded", 0)
        metrics.append(Metric("delegation_success_rate", (succeeded / max(delegated, 1)) * 100, "%", 1.2))
        events_total = cs.get("events_total", 0)
        useful = cs.get("useful_events", 0)
        metrics.append(Metric("communication_efficiency", (useful / max(events_total, 1)) * 100, "%", 0.8))
        metrics.append(Metric("synthesis_quality", cs.get("synthesis_quality", 0.7) * 100, "score", 1.0))
        seq = cs.get("sequential_time_ms", 1)
        actual = cs.get("actual_time_ms", 1)
        metrics.append(Metric("parallel_efficiency", min((seq / max(actual, 1)) * 100, 100), "score", 1.0))
        return DimensionScore.from_metrics(self.name, metrics)


class ObservabilityDimension(EvaluationDimension):
    """维度5: 可观测性"""

    name = "Observability"
    description = "追踪、指标、日志的完整性和可调试性"
    weight = 0.12

    async def evaluate(self, context: dict[str, Any]) -> DimensionScore:
        metrics = []
        obs = context.get("observability_stats", {})
        metrics.append(Metric("trace_coverage", obs.get("trace_coverage", 0) * 100, "%", 1.2))
        metrics.append(Metric("metric_completeness", obs.get("metric_completeness", 0) * 100, "%", 1.0))
        metrics.append(Metric("error_attribution", obs.get("error_attribution_rate", 0) * 100, "%", 1.3))
        replay_ok = 100.0 if obs.get("supports_replay", False) else 0.0
        metrics.append(Metric("replay_capability", replay_ok, "bool", 0.8))
        return DimensionScore.from_metrics(self.name, metrics)


class DeveloperExperienceDimension(EvaluationDimension):
    """维度6: 开发者体验"""

    name = "Developer Experience"
    description = "API 易用性、文档质量、错误信息可读性"
    weight = 0.10

    async def evaluate(self, context: dict[str, Any]) -> DimensionScore:
        metrics = []
        dx = context.get("dx_stats", {})
        metrics.append(Metric("api_simplicity", dx.get("lines_to_hello_world", 100), "lines", 1.0,
                              description="Hello World 所需代码行数"))
        loc = dx.get("lines_to_hello_world", 10)
        api_score = max(0, 100 - (loc - 3) * 10)  # 3行=100分，每多1行扣10分
        metrics[0] = Metric("api_simplicity", min(max(api_score, 0), 100), "score", 1.0)
        metrics.append(Metric("error_clarity", dx.get("error_clarity", 0.5) * 100, "score", 1.2))
        metrics.append(Metric("type_safety", dx.get("type_coverage", 0.5) * 100, "%", 0.8))
        metrics.append(Metric("doc_coverage", dx.get("doc_coverage", 0.5) * 100, "%", 0.8))
        return DimensionScore.from_metrics(self.name, metrics)
