"""
Benchmark Runner - 基准测试运行器

提供标准化的场景定义和自动化测试执行。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .framework import EvaluationFramework, EvaluationReport


class ScenarioComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    MARATHON = "marathon"


@dataclass
class BenchmarkScenario:
    """基准测试场景"""

    name: str
    description: str
    complexity: ScenarioComplexity
    steps: list[dict[str, Any]]
    expected_outcomes: list[str] = field(default_factory=list)
    timeout_seconds: float = 300.0
    tags: list[str] = field(default_factory=list)


BUILTIN_SCENARIOS: list[BenchmarkScenario] = [
    BenchmarkScenario(
        name="linear_10_step",
        description="10步线性任务",
        complexity=ScenarioComplexity.SIMPLE,
        steps=[{"id": i, "type": "sequential"} for i in range(10)],
        tags=["baseline", "linear"],
    ),
    BenchmarkScenario(
        name="branching_20_step",
        description="20步分支任务",
        complexity=ScenarioComplexity.MODERATE,
        steps=[{"id": i, "type": "branching"} for i in range(20)],
        tags=["branching"],
    ),
    BenchmarkScenario(
        name="marathon_50_step",
        description="50步马拉松任务",
        complexity=ScenarioComplexity.MARATHON,
        steps=[{"id": i, "type": "marathon"} for i in range(50)],
        tags=["marathon", "stress"],
        timeout_seconds=600.0,
    ),
    BenchmarkScenario(
        name="multi_agent_delegation",
        description="多Agent委派任务",
        complexity=ScenarioComplexity.MODERATE,
        steps=[{"id": i, "type": "delegation", "agents": 3} for i in range(15)],
        tags=["multi-agent"],
    ),
    BenchmarkScenario(
        name="memory_pressure",
        description="记忆压力测试",
        complexity=ScenarioComplexity.COMPLEX,
        steps=[{"id": i, "type": "memory_intensive"} for i in range(30)],
        tags=["memory", "stress"],
    ),
]


@dataclass
class ScenarioResult:
    """单场景执行结果"""

    scenario: BenchmarkScenario
    step_results: list[dict[str, Any]]
    total_time_ms: float
    total_tokens: int = 0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    """
    基准测试运行器

    用法：
        runner = BenchmarkRunner(agent_factory=my_factory)
        results = await runner.run_all()
        report = await runner.generate_report(results)
    """

    def __init__(
        self,
        agent_factory: Callable[..., Awaitable[Any]],
        scenarios: list[BenchmarkScenario] | None = None,
        evaluation_framework: EvaluationFramework | None = None,
    ):
        self.agent_factory = agent_factory
        self.scenarios = scenarios or BUILTIN_SCENARIOS
        self.eval_framework = evaluation_framework or EvaluationFramework()

    async def run_scenario(self, scenario: BenchmarkScenario) -> ScenarioResult:
        """执行单个场景"""
        step_results: list[dict[str, Any]] = []
        errors: list[str] = []
        total_tokens = 0
        start = time.monotonic()

        agent = await self.agent_factory()

        for step in scenario.steps:
            step_start = time.monotonic()
            try:
                result = await asyncio.wait_for(
                    self._execute_step(agent, step),
                    timeout=scenario.timeout_seconds / max(len(scenario.steps), 1),
                )
                step_results.append(
                    {
                        "step_id": step["id"],
                        "completed": True,
                        "time_ms": (time.monotonic() - step_start) * 1000,
                        "tokens": result.get("tokens", 0),
                        "output": result.get("output", ""),
                    }
                )
                total_tokens += result.get("tokens", 0)
            except TimeoutError:
                step_results.append(
                    {
                        "step_id": step["id"],
                        "completed": False,
                        "time_ms": (time.monotonic() - step_start) * 1000,
                        "error": "timeout",
                    }
                )
                errors.append(f"Step {step['id']} timed out")
            except Exception as e:
                step_results.append(
                    {
                        "step_id": step["id"],
                        "completed": False,
                        "time_ms": (time.monotonic() - step_start) * 1000,
                        "error": str(e),
                    }
                )
                errors.append(f"Step {step['id']}: {e}")

        elapsed = (time.monotonic() - start) * 1000
        return ScenarioResult(
            scenario=scenario,
            step_results=step_results,
            total_time_ms=elapsed,
            total_tokens=total_tokens,
            errors=errors,
        )

    async def run_all(
        self,
        tags: list[str] | None = None,
    ) -> list[ScenarioResult]:
        """执行所有（或按 tag 过滤的）场景"""
        scenarios = self.scenarios
        if tags:
            scenarios = [s for s in scenarios if any(t in s.tags for t in tags)]

        results = []
        for scenario in scenarios:
            result = await self.run_scenario(scenario)
            results.append(result)
        return results

    async def generate_report(
        self,
        results: list[ScenarioResult],
    ) -> EvaluationReport:
        """从场景结果生成评估报告"""
        context = self._results_to_context(results)
        return await self.eval_framework.evaluate(context)

    @staticmethod
    async def _execute_step(agent: Any, step: dict[str, Any]) -> dict[str, Any]:
        """执行单步（由具体 agent 实现决定）"""
        if hasattr(agent, "run"):
            prompt = f"Execute step {step['id']} (type: {step.get('type', 'unknown')})"
            result = await agent.run(prompt)
            return {"output": str(result), "tokens": 0}
        return {"output": "", "tokens": 0}

    @staticmethod
    def _results_to_context(results: list[ScenarioResult]) -> dict[str, Any]:
        """将场景结果转换为评估上下文"""
        all_steps = []
        total_errors = 0
        total_tokens = 0

        for r in results:
            all_steps.extend(r.step_results)
            total_errors += len(r.errors)
            total_tokens += r.total_tokens

        return {
            "step_results": all_steps,
            "total_errors": total_errors,
            "error_cascades": 0,
            "recoveries": 0,
            "memory_stats": {
                "total_budget": 128000,
                "tokens_used": total_tokens,
            },
            "context_stats": {},
            "coordination_stats": {},
            "observability_stats": {},
            "dx_stats": {},
        }
