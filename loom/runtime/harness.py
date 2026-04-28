"""Runtime harness contracts."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from .task import RuntimeTask


@dataclass(slots=True)
class HarnessCandidate:
    """One possible output considered by a harness strategy."""

    content: str
    id: str = ""
    score: float | None = None
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


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
    candidates: list[HarnessCandidate] = field(default_factory=list)
    selected_candidate_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class HarnessRequest:
    """Semantic request passed to user-defined runtime harnesses."""

    task: RuntimeTask
    context: HarnessContext

    @property
    def runner(self) -> Any:
        return self.context.runner

    @property
    def session_id(self) -> str | None:
        return self.context.session_id

    @property
    def metadata(self) -> dict[str, Any]:
        return self.context.metadata

    async def run_once(self, task: RuntimeTask | None = None) -> Any:
        """Run the underlying runtime once, bypassing the harness strategy."""
        run = getattr(self.runner, "run", None)
        if not callable(run):
            raise TypeError("HarnessRequest.runner must provide an async run(task) method")
        return await run(task or self.task)


class RuntimeHarness(Protocol):
    """Protocol implemented by all long-task runtime harnesses."""

    async def run(
        self,
        request: HarnessRequest,
    ) -> HarnessOutcome: ...


class Harness:
    """Factory for built-in runtime harness implementations."""

    @staticmethod
    def single_run() -> SingleRunHarness:
        return SingleRunHarness()

    @staticmethod
    def custom(
        handler: Callable[[HarnessRequest], HarnessOutcome | str | Awaitable[HarnessOutcome | str]],
        *,
        name: str = "custom",
    ) -> CustomHarness:
        return CustomHarness(handler=handler, name=name)

    @staticmethod
    def generator_evaluator(
        *,
        generator: Any | None = None,
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
        request: HarnessRequest | RuntimeTask,
        context: HarnessContext | None = None,
    ) -> HarnessOutcome:
        request = _coerce_request(request, context)
        task = request.task
        runner = request.runner
        run = getattr(runner, "run", None)
        if not callable(run):
            raise TypeError("HarnessContext.runner must provide an async run(task) method")
        result = await run(task)
        output = _result_field(result, "output", result)
        state = str(_result_field(result, "state", _result_field(result, "status", ""))).lower()
        iterations = _result_field(result, "iterations", 1)
        passed = "failed" not in state and "cancelled" not in state
        return HarnessOutcome(
            output=str(output),
            passed=passed,
            iterations=int(iterations or 1),
            metadata={"harness": "single_run"},
        )


class CustomHarness:
    """Adapter for user-defined runtime harness strategies."""

    def __init__(
        self,
        handler: Callable[[HarnessRequest], HarnessOutcome | str | Awaitable[HarnessOutcome | str]],
        *,
        name: str = "custom",
    ) -> None:
        self.handler = handler
        self.name = name

    async def run(
        self,
        request: HarnessRequest | RuntimeTask,
        context: HarnessContext | None = None,
    ) -> HarnessOutcome:
        resolved = _coerce_request(request, context)
        result = self.handler(resolved)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, HarnessOutcome):
            result.metadata.setdefault("harness", self.name)
            return result
        return HarnessOutcome(output=str(result), metadata={"harness": self.name})


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
        request: HarnessRequest | RuntimeTask,
        context: HarnessContext | None = None,
    ) -> HarnessOutcome:
        from ..orchestration.harness import AgentHarness

        request = _coerce_request(request, context)
        task = request.task
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
            candidates=[
                HarnessCandidate(
                    id=f"sprint-{sprint.sprint}",
                    content=sprint.output,
                    score=1.0 if sprint.passed else 0.0,
                    rationale=sprint.critique,
                    metadata={"passed": sprint.passed},
                )
                for sprint in result.sprint_results
            ],
            metadata={
                "harness": "generator_evaluator",
                "critique": result.critique,
                "spec": result.spec,
                "sprint_results": result.sprint_results,
            },
        )


def _coerce_request(
    request: HarnessRequest | RuntimeTask,
    context: HarnessContext | None,
) -> HarnessRequest:
    if isinstance(request, HarnessRequest):
        return request
    if isinstance(request, RuntimeTask):
        if context is None:
            raise TypeError("HarnessContext is required when running a harness with RuntimeTask")
        return HarnessRequest(task=request, context=context)
    raise TypeError(f"harness request must be HarnessRequest or RuntimeTask, got {type(request).__name__}")


def _result_field(result: Any, key: str, default: Any) -> Any:
    if isinstance(result, dict):
        return result.get(key, default)
    return getattr(result, key, default)
