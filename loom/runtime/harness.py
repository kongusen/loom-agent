"""Runtime harness contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .task import RuntimeTask


@dataclass(slots=True)
class HarnessContext:
    """Execution context supplied to a runtime harness."""

    runner: Any
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class HarnessOutcome:
    """Outcome returned by a runtime harness."""

    output: str
    passed: bool = True
    iterations: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeHarness(Protocol):
    """Protocol implemented by all long-task runtime harnesses."""

    async def run(
        self,
        task: RuntimeTask,
        context: HarnessContext,
    ) -> HarnessOutcome:
        ...


class Harness:
    """Factory for built-in runtime harness implementations."""

    @staticmethod
    def single_run() -> SingleRunHarness:
        return SingleRunHarness()

    @staticmethod
    def generator_evaluator(
        *,
        generator: Any,
        evaluator: Any | None = None,
        planner: Any | None = None,
        quality_gate: Any | None = None,
        max_sprints: int = 5,
        event_bus: Any | None = None,
    ) -> GeneratorEvaluatorHarness:
        return GeneratorEvaluatorHarness(
            generator=generator,
            evaluator=evaluator,
            planner=planner,
            quality_gate=quality_gate,
            max_sprints=max_sprints,
            event_bus=event_bus,
        )


class SingleRunHarness:
    """Harness that delegates one RuntimeTask to the supplied runner."""

    async def run(
        self,
        task: RuntimeTask,
        context: HarnessContext,
    ) -> HarnessOutcome:
        runner = context.runner
        run = getattr(runner, "run", None)
        if not callable(run):
            raise TypeError("HarnessContext.runner must provide an async run(task) method")
        result = await run(task)
        output = getattr(result, "output", result)
        state = str(getattr(result, "state", "")).lower()
        passed = "failed" not in state and "cancelled" not in state
        return HarnessOutcome(
            output=str(output),
            passed=passed,
            iterations=1,
            metadata={"harness": "single_run"},
        )


class GeneratorEvaluatorHarness:
    """Runtime harness adapter for the existing AgentHarness implementation."""

    def __init__(
        self,
        *,
        generator: Any,
        evaluator: Any | None = None,
        planner: Any | None = None,
        quality_gate: Any | None = None,
        max_sprints: int = 5,
        event_bus: Any | None = None,
    ) -> None:
        self.generator = generator
        self.evaluator = evaluator
        self.planner = planner
        self.quality_gate = quality_gate
        self.max_sprints = max_sprints
        self.event_bus = event_bus

    async def run(
        self,
        task: RuntimeTask,
        context: HarnessContext,
    ) -> HarnessOutcome:
        from ..orchestration.harness import AgentHarness

        _ = context
        result = await AgentHarness(
            generator=self.generator,
            evaluator=self.evaluator,
            planner=self.planner,
            quality_gate=self.quality_gate,
            max_sprints=self.max_sprints,
            event_bus=self.event_bus,
        ).run(task.goal)
        return HarnessOutcome(
            output=result.output,
            passed=result.passed,
            iterations=result.sprints,
            metadata={
                "harness": "generator_evaluator",
                "critique": result.critique,
                "spec": result.spec,
                "sprint_results": result.sprint_results,
            },
        )
