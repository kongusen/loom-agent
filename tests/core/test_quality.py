"""Tests for runtime quality contracts and gates."""

import pytest

from loom.orchestration.gen_eval import SprintContract
from loom.runtime.quality import QualityContract, QualityGate, QualityResult
from loom.runtime.task import RuntimeTask
from loom.types.results import SubAgentResult


class _StubEvaluator:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self._call_count = 0
        self.prompts: list[str] = []

    async def spawn(
        self, goal: str, depth: int = 0, inherit_context: bool = True
    ) -> SubAgentResult:
        self.prompts.append(goal)
        idx = min(self._call_count, len(self._responses) - 1)
        response = self._responses[idx]
        self._call_count += 1
        return SubAgentResult(success=True, output=response, depth=depth + 1)


def test_pass_fail_quality_gate_parses_pass() -> None:
    result = QualityGate.pass_fail().parse("PASS\nAll criteria met")

    assert result.passed is True
    assert result.critique == "All criteria met"


def test_pass_fail_quality_gate_parses_fail() -> None:
    result = QualityGate.pass_fail().parse("FAIL\nMissing required behavior")

    assert result.passed is False
    assert result.critique == "Missing required behavior"


def test_sprint_contract_adapts_to_quality_contract() -> None:
    sprint = SprintContract(
        sprint=3,
        goal="ship feature",
        criteria=["tests pass"],
        eval_tools=["pytest"],
    )

    contract = sprint.to_quality_contract()
    restored = SprintContract.from_quality_contract(contract, sprint=3)

    assert contract == QualityContract(
        goal="ship feature",
        criteria=["tests pass"],
        eval_tools=["pytest"],
        metadata={"sprint": 3},
    )
    assert restored == sprint


@pytest.mark.asyncio
async def test_criteria_quality_gate_uses_task_criteria() -> None:
    gate = QualityGate.criteria()
    task = RuntimeTask(goal="build api", criteria=["has tests"])

    contract = await gate.contract_for(task, iteration=2)
    result = await gate.evaluate("PASS\nok", contract)

    assert contract.goal == "build api"
    assert contract.criteria == ["has tests"]
    assert contract.metadata == {"iteration": 2}
    assert isinstance(result, QualityResult)
    assert result.passed is True


@pytest.mark.asyncio
async def test_evaluator_quality_gate_negotiates_and_evaluates() -> None:
    evaluator = _StubEvaluator(["criterion A\ncriterion B", "FAIL\nNeeds work"])
    gate = QualityGate.evaluator(evaluator)

    contract = await gate.contract_for(RuntimeTask(goal="do work"), iteration=1)
    result = await gate.evaluate("candidate output", contract)

    assert contract.criteria == ["criterion A", "criterion B"]
    assert result.passed is False
    assert result.critique == "Needs work"
    assert "success criteria" in evaluator.prompts[0]
    assert "candidate output" in evaluator.prompts[1]
