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
        evaluator: SubAgentManager,
        event_bus: CoordinationEventBus | None = None,
    ):
        self.generator = generator
        self.evaluator = evaluator
        self.event_bus = event_bus

    # ── Public API ──────────────────────────────────────────────────────────

    async def run(
        self,
        goal: str,
        max_sprints: int = 5,
    ) -> list[SprintResult]:
        """Run the GAN loop, returning all sprint results."""
        results: list[SprintResult] = []
        critique = ""

        for sprint_num in range(1, max_sprints + 1):
            # Phase 1: negotiate criteria for this sprint
            contract = await self._negotiate_contract(goal, sprint_num)

            # Phase 2: generator produces output
            gen_prompt = self._build_gen_prompt(goal, contract, critique)
            gen_result = await self.generator.spawn(gen_prompt, depth=0)
            output = gen_result.output if gen_result.success else f"[generator error] {gen_result.error}"

            # Phase 3: evaluator judges output
            eval_prompt = self._build_eval_prompt(output, contract)
            eval_result = await self.evaluator.spawn(eval_prompt, depth=0)
            passed, critique = self._parse_eval(
                eval_result.output if eval_result.success else "FAIL\nEvaluator error"
            )

            sprint_result = SprintResult(
                sprint=sprint_num,
                passed=passed,
                output=output,
                critique=critique,
                contract=contract,
            )
            results.append(sprint_result)

            # Phase 4: publish event if bus attached
            self._publish_sprint_event(sprint_result)

            if passed:
                break

        return results

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _negotiate_contract(self, goal: str, sprint: int) -> SprintContract:
        """Ask the evaluator to generate verifiable success criteria."""
        negotiate_prompt = (
            f"You are an Evaluator setting success criteria for sprint {sprint}.\n"
            f"Goal: {goal}\n\n"
            "List 3-5 concrete, verifiable criteria that the Generator's output "
            "must satisfy. Respond with one criterion per line, no numbering."
        )
        result = await self.evaluator.spawn(negotiate_prompt, depth=0)
        raw = result.output if result.success else ""
        criteria = [line.strip() for line in raw.splitlines() if line.strip()]
        if not criteria:
            criteria = [f"Output addresses the goal: {goal}"]
        return SprintContract(sprint=sprint, goal=goal, criteria=criteria)

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
        criteria_md = "\n".join(f"- {c}" for c in contract.criteria)
        return (
            f"You are an Evaluator. Judge the following output.\n\n"
            f"**Goal:** {contract.goal}\n\n"
            f"**Success criteria:**\n{criteria_md}\n\n"
            f"**Output to evaluate:**\n{output}\n\n"
            "Respond with PASS or FAIL on the first line, then provide your "
            "critique or confirmation on subsequent lines."
        )

    def _parse_eval(self, raw: str) -> tuple[bool, str]:
        """Parse evaluator response: first line = PASS/FAIL, rest = critique."""
        lines = raw.strip().splitlines()
        if not lines:
            return False, "No evaluator response"
        verdict = lines[0].strip().upper()
        passed = verdict.startswith("PASS")
        critique = "\n".join(lines[1:]).strip()
        return passed, critique

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
