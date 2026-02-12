"""
Evaluation Framework - 评估框架编排器

整合六大维度，生成综合评估报告。
支持与其他框架的横向对比。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .dimensions import (
    ContextQualityDimension,
    DeveloperExperienceDimension,
    DimensionScore,
    EvaluationDimension,
    LongHorizonStabilityDimension,
    MemoryEfficiencyDimension,
    MultiAgentCoordinationDimension,
    ObservabilityDimension,
    ScoreLevel,
)


@dataclass
class FrameworkProfile:
    """框架基本信息"""

    name: str
    version: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    """综合评估报告"""

    framework: FrameworkProfile
    dimension_scores: list[DimensionScore]
    overall_score: float
    overall_level: ScoreLevel
    timestamp: float = field(default_factory=time.time)
    comparison_baseline: dict[str, float] = field(default_factory=dict)

    @property
    def radar_data(self) -> dict[str, float]:
        """雷达图数据（各维度得分）"""
        return {ds.dimension_name: ds.score for ds in self.dimension_scores}

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework": {
                "name": self.framework.name,
                "version": self.framework.version,
            },
            "overall_score": self.overall_score,
            "overall_level": self.overall_level.value,
            "dimensions": {
                ds.dimension_name: {
                    "score": ds.score,
                    "level": ds.level.value,
                    "metrics": [
                        {"name": m.name, "value": m.value, "unit": m.unit} for m in ds.metrics
                    ],
                }
                for ds in self.dimension_scores
            },
            "timestamp": self.timestamp,
        }


# ============ 竞品基线数据（用于横向对比）============

COMPETITOR_BASELINES: dict[str, dict[str, float]] = {
    "langchain": {
        "Long-Horizon Stability": 45,
        "Memory Efficiency": 55,
        "Context Quality": 60,
        "Multi-Agent Coordination": 40,
        "Observability": 65,
        "Developer Experience": 75,
    },
    "crewai": {
        "Long-Horizon Stability": 50,
        "Memory Efficiency": 45,
        "Context Quality": 50,
        "Multi-Agent Coordination": 70,
        "Observability": 40,
        "Developer Experience": 70,
    },
    "autogen": {
        "Long-Horizon Stability": 55,
        "Memory Efficiency": 50,
        "Context Quality": 55,
        "Multi-Agent Coordination": 65,
        "Observability": 45,
        "Developer Experience": 55,
    },
}


class EvaluationFramework:
    """
    评估框架 - 统一编排器

    用法：
        framework = EvaluationFramework()
        report = await framework.evaluate(context_data)
        report.to_dict()  # 导出报告
    """

    def __init__(
        self,
        dimensions: list[EvaluationDimension] | None = None,
        framework_profile: FrameworkProfile | None = None,
    ):
        self.dimensions = dimensions or self._default_dimensions()
        self.profile = framework_profile or FrameworkProfile(
            name="loom-agent",
            version="0.5.5",
            description="公理驱动的递归状态机 Agent 框架",
        )

    @staticmethod
    def _default_dimensions() -> list[EvaluationDimension]:
        return [
            LongHorizonStabilityDimension(),
            MemoryEfficiencyDimension(),
            ContextQualityDimension(),
            MultiAgentCoordinationDimension(),
            ObservabilityDimension(),
            DeveloperExperienceDimension(),
        ]

    async def evaluate(self, context: dict[str, Any]) -> EvaluationReport:
        """执行全维度评估"""
        scores: list[DimensionScore] = []
        for dim in self.dimensions:
            score = await dim.evaluate(context)
            scores.append(score)

        # 加权总分
        total_weight = sum(d.weight for d in self.dimensions)
        overall = sum(
            s.score * d.weight for s, d in zip(scores, self.dimensions, strict=False)
        ) / max(total_weight, 0.01)

        level = DimensionScore._score_to_level(overall)

        return EvaluationReport(
            framework=self.profile,
            dimension_scores=scores,
            overall_score=round(overall, 2),
            overall_level=level,
        )

    async def compare_with(
        self,
        context: dict[str, Any],
        baseline_name: str = "langchain",
    ) -> dict[str, Any]:
        """与竞品基线对比"""
        report = await self.evaluate(context)
        baseline = COMPETITOR_BASELINES.get(baseline_name, {})

        comparison = {}
        for ds in report.dimension_scores:
            base_score = baseline.get(ds.dimension_name, 50)
            delta = ds.score - base_score
            comparison[ds.dimension_name] = {
                "loom": ds.score,
                "baseline": base_score,
                "delta": round(delta, 2),
                "advantage": delta > 0,
            }

        return {
            "loom_overall": report.overall_score,
            "baseline_name": baseline_name,
            "dimensions": comparison,
        }
