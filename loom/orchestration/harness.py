"""AgentHarness - Planner → Generator ⇌ Evaluator one-shot entry point.

Implements the Harness pattern from Anthropic's "Harness Design for Long-Running Apps":
  1. (Optional) Planner expands the brief into a detailed spec
  2. GeneratorEvaluatorLoop refines the output until PASS or max_sprints
  3. Returns a HarnessResult with the final output and sprint history
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runtime.quality import RuntimeQualityGate
    from .events import CoordinationEventBus
    from .subagent import SubAgentManager

from .gen_eval import GeneratorEvaluatorLoop, SprintResult


@dataclass
class HarnessResult:
    """Complete result from an AgentHarness.run() call."""

    spec: str                              # planner-expanded brief (or original brief)
    output: str                            # final generator output
    passed: bool                           # True if evaluator passed the last sprint
    sprints: int                           # total sprints executed
    critique: str                          # last evaluator critique (empty on first-try PASS)
    sprint_results: list[SprintResult] = field(default_factory=list)


class AgentHarness:
    """Planner → Generator ⇌ Evaluator pipeline.

    The evaluator is optional: when omitted the harness runs a single
    generator sprint with no criteria negotiation.

    Usage::

        harness = AgentHarness(generator=gen_mgr, evaluator=eval_mgr, planner=plan_mgr)
        result = await harness.run("Build a CLI tool that converts CSV to JSON")
    """

    def __init__(
        self,
        generator: SubAgentManager,
        evaluator: SubAgentManager | None = None,
        planner: SubAgentManager | None = None,
        max_sprints: int = 5,
        event_bus: CoordinationEventBus | None = None,
        quality_gate: RuntimeQualityGate | None = None,
    ):
        self.generator = generator
        self.evaluator = evaluator
        self.planner = planner
        self.max_sprints = max_sprints
        self.event_bus = event_bus
        self.quality_gate = quality_gate

    async def run(self, brief: str) -> HarnessResult:
        """Execute the full Planner→Generator⇌Evaluator pipeline."""

        # Phase 1: planner expands brief → spec (optional)
        spec = await self._plan(brief)

        # Phase 2a: no evaluator — single generator run
        if self.evaluator is None and self.quality_gate is None:
            gen_result = await self.generator.spawn(spec, depth=0)
            output = gen_result.output if gen_result.success else f"[error] {gen_result.error}"
            return HarnessResult(
                spec=spec,
                output=output,
                passed=gen_result.success,
                sprints=1,
                critique="",
                sprint_results=[],
            )

        # Phase 2b: generator⇌evaluator loop
        loop = GeneratorEvaluatorLoop(
            generator=self.generator,
            evaluator=self.evaluator,
            event_bus=self.event_bus,
            quality_gate=self.quality_gate,
        )
        sprint_results = await loop.run(spec, max_sprints=self.max_sprints)

        last = sprint_results[-1] if sprint_results else None
        return HarnessResult(
            spec=spec,
            output=last.output if last else "",
            passed=last.passed if last else False,
            sprints=len(sprint_results),
            critique=last.critique if last else "",
            sprint_results=sprint_results,
        )

    async def _plan(self, brief: str) -> str:
        """Expand brief into a detailed spec via planner (or return brief as-is)."""
        if self.planner is None:
            return brief
        plan_prompt = (
            f"You are a Planner. Expand the following brief into a detailed, "
            f"actionable specification that a Generator can implement.\n\n"
            f"Brief: {brief}\n\n"
            "Provide the expanded specification now."
        )
        result = await self.planner.spawn(plan_prompt, depth=0)
        if result.success and result.output:
            return str(result.output)
        return brief  # fall back to original brief on planner failure
