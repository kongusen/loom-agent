"""
Loom Agent 评价体系 (Evaluation Framework)

提供标准化的 Agent 框架评估维度和基准测试，
帮助量化 loom-agent 在长时间任务场景下的核心优势。

六大评估维度：
1. Long-Horizon Stability (长程稳定性)
2. Memory Efficiency (记忆效率)
3. Context Quality (上下文质量)
4. Multi-Agent Coordination (多智能体协作)
5. Observability & Debuggability (可观测性)
6. Developer Experience (开发者体验)
"""

from benchmarks.dimensions import (
    ContextQualityDimension,
    DeveloperExperienceDimension,
    EvaluationDimension,
    LongHorizonStabilityDimension,
    MemoryEfficiencyDimension,
    MultiAgentCoordinationDimension,
    ObservabilityDimension,
)
from benchmarks.framework import EvaluationFramework, EvaluationReport
from benchmarks.runner import BenchmarkRunner, BenchmarkScenario

__all__ = [
    "EvaluationFramework",
    "EvaluationReport",
    "EvaluationDimension",
    "LongHorizonStabilityDimension",
    "MemoryEfficiencyDimension",
    "ContextQualityDimension",
    "MultiAgentCoordinationDimension",
    "ObservabilityDimension",
    "DeveloperExperienceDimension",
    "BenchmarkRunner",
    "BenchmarkScenario",
]
