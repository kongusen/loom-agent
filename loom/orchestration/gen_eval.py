"""Generator-Evaluator (GAN-style) loop for iterative output refinement.

Implements the Generator-Evaluator pattern from Anthropic's Harness Design:
- Generator produces output given goal + criteria + prior critique
- Evaluator judges output against criteria → PASS / FAIL + critique
- Sprint Contract: success criteria negotiated before each sprint
- Loop runs until PASS or max_sprints exhausted
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..runtime.quality import QualityContract, QualityGate, RuntimeQualityGate
from ..runtime.task import RuntimeTask

if TYPE_CHECKING:
    from ..types.handoff import HandoffArtifact
    from .events import CoordinationEventBus
    from .subagent import SubAgentManager


@dataclass
class SprintContract:
    """Negotiated success criteria for a single sprint.

    Created by the Evaluator before the Generator runs so both sides
    agree on what "done" looks like before work begins.
    """

    sprint: int
    goal: str
    criteria: list[str]      # verifiable pass conditions
    eval_tools: list[str] = field(default_factory=list)   # tools evaluator may use

    @classmethod
    def from_quality_contract(
        cls,
        contract: QualityContract,
        *,
        sprint: int,
    ) -> SprintContract:
        """Adapt a runtime QualityContract to the legacy sprint contract shape."""
        return cls(
            sprint=sprint,
            goal=contract.goal,
            criteria=list(contract.criteria),
            eval_tools=list(contract.eval_tools),
        )

    def to_quality_contract(self) -> QualityContract:
        """Adapt this legacy sprint contract to the runtime quality contract."""
        return QualityContract(
            goal=self.goal,
            criteria=list(self.criteria),
            eval_tools=list(self.eval_tools),
            metadata={"sprint": self.sprint},
        )


@dataclass
class SprintResult:
    """Outcome of one Generator→Evaluator round."""

    sprint: int
    passed: bool
    output: str              # Generator's output
    critique: str            # Evaluator's feedback (empty string on first PASS)
    contract: SprintContract
    handoff: HandoffArtifact | None = None


class GeneratorEvaluatorLoop:
    """Run Generator⇌Evaluator iterations until PASS or max_sprints.

    Usage::

        loop = GeneratorEvaluatorLoop(generator=gen_mgr, evaluator=eval_mgr)
        results = await loop.run("Build a REST API for user auth", max_sprints=5)
    """

    def __init__(
        self,
        generator: SubAgentManager,
        evaluator: SubAgentManager | None = None,
        event_bus: CoordinationEventBus | None = None,
        quality_gate: RuntimeQualityGate | None = None,
    ):
        self.generator = generator
        self.evaluator = evaluator
        self.event_bus = event_bus
        self.quality_gate = quality_gate or (
            QualityGate.evaluator(evaluator) if evaluator is not None else None
        )
        if self.quality_gate is None:
            raise ValueError("GeneratorEvaluatorLoop requires evaluator or quality_gate")

    # ── Public API ──────────────────────────────────────────────────────────

    async def run(
        self,
        goal: str,
        max_sprints: int = 5,
    ) -> list[SprintResult]:
        """Run the GAN loop, returning all sprint results."""
        results: list[SprintResult] = []
        critique = ""
        task = RuntimeTask(goal=goal)
        quality_gate = self.quality_gate
        if quality_gate is None:
            raise ValueError("GeneratorEvaluatorLoop requires evaluator or quality_gate")

        for sprint_num in range(1, max_sprints + 1):
            # Phase 1: negotiate criteria for this sprint
            quality_contract = await quality_gate.contract_for(task, iteration=sprint_num)
            contract = SprintContract.from_quality_contract(
                quality_contract,
                sprint=sprint_num,
            )

            # Phase 2: generator produces output
            gen_prompt = self._build_gen_prompt(goal, contract, critique)
            gen_result = await self.generator.spawn(gen_prompt, depth=0)
            output = gen_result.output if gen_result.success else f"[generator error] {gen_result.error}"

            # Phase 3: evaluator judges output
            quality_result = await quality_gate.evaluate(output, contract.to_quality_contract())
            critique = quality_result.critique

            sprint_result = SprintResult(
                sprint=sprint_num,
                passed=quality_result.passed,
                output=output,
                critique=critique,
                contract=contract,
            )
            results.append(sprint_result)

            # Phase 4: publish event if bus attached
            self._publish_sprint_event(sprint_result)

            if quality_result.passed:
                break

        return results

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _negotiate_contract(self, goal: str, sprint: int) -> SprintContract:
        """Ask the evaluator to generate verifiable success criteria."""
        if self.quality_gate is None:
            raise ValueError("GeneratorEvaluatorLoop requires evaluator or quality_gate")
        contract = await self.quality_gate.contract_for(
            RuntimeTask(goal=goal),
            iteration=sprint,
        )
        return SprintContract.from_quality_contract(contract, sprint=sprint)

    def _build_gen_prompt(
        self,
        goal: str,
        contract: SprintContract,
        critique: str,
    ) -> str:
        criteria_md = "\n".join(f"- {c}" for c in contract.criteria)
        prompt = (
            f"You are a Generator. Complete the following goal.\n\n"
            f"**Goal:** {goal}\n\n"
            f"**Success criteria (Sprint {contract.sprint}):**\n{criteria_md}\n"
        )
        if critique:
            prompt += f"\n**Prior critique to address:**\n{critique}\n"
        prompt += "\nProvide your output now."
        return prompt

    def _build_eval_prompt(self, output: str, contract: SprintContract) -> str:
        gate = QualityGate.evaluator(self.evaluator) if self.evaluator is not None else None
        if gate is None:
            raise ValueError("GeneratorEvaluatorLoop requires evaluator to build eval prompt")
        return gate.build_evaluation_prompt(output, contract.to_quality_contract())

    def _parse_eval(self, raw: str) -> tuple[bool, str]:
        """Parse evaluator response: first line = PASS/FAIL, rest = critique."""
        result = QualityGate.pass_fail().parse(raw)
        return result.passed, result.critique

    def _publish_sprint_event(self, result: SprintResult) -> None:
        """Publish a sprint.passed or sprint.failed event if bus is configured."""
        if self.event_bus is None:
            return
        from ..types.events import CoordinationEvent
        topic = "sprint.passed" if result.passed else "sprint.failed"
        event = CoordinationEvent(
            id=str(uuid.uuid4()),
            sender="gen_eval_loop",
            topic=topic,
            payload={
                "sprint": result.sprint,
                "passed": result.passed,
                "critique": result.critique,
            },
            delta_h=0.5,
            priority="medium",
        )
        self.event_bus.publish(event)
