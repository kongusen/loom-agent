"""Tests for GeneratorEvaluatorLoop and SprintContract."""

from types import SimpleNamespace

import pytest

from loom.orchestration.events import CoordinationEventBus
from loom.orchestration.gen_eval import (
    GeneratorEvaluatorLoop,
    SprintContract,
    SprintResult,
)
from loom.types.results import SubAgentResult


# ── SprintContract ──────────────────────────────────────────────────────────

class TestSprintContract:
    def test_creation(self):
        contract = SprintContract(
            sprint=1,
            goal="build a thing",
            criteria=["criterion A", "criterion B"],
        )
        assert contract.sprint == 1
        assert contract.goal == "build a thing"
        assert len(contract.criteria) == 2
        assert contract.eval_tools == []

    def test_with_eval_tools(self):
        contract = SprintContract(
            sprint=2,
            goal="test something",
            criteria=["passes all checks"],
            eval_tools=["playwright", "pytest"],
        )
        assert contract.eval_tools == ["playwright", "pytest"]


# ── Stubs ────────────────────────────────────────────────────────────────────

class _StubManager:
    """Minimal SubAgentManager stub for testing."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self._call_count = 0
        self.prompts: list[str] = []

    async def spawn(self, goal: str, depth: int = 0, inherit_context: bool = True) -> SubAgentResult:
        self.prompts.append(goal)
        idx = min(self._call_count, len(self._responses) - 1)
        response = self._responses[idx]
        self._call_count += 1
        return SubAgentResult(success=True, output=response, depth=depth + 1)


class _FailingManager:
    """Stub that always returns a failed result."""

    async def spawn(self, goal: str, depth: int = 0, inherit_context: bool = True) -> SubAgentResult:
        return SubAgentResult(success=False, output="boom", depth=depth + 1, error="boom")


# ── GeneratorEvaluatorLoop ───────────────────────────────────────────────────

class TestGeneratorEvaluatorLoop:
    @pytest.mark.asyncio
    async def test_pass_on_first_sprint(self):
        """When evaluator returns PASS on the first sprint, loop exits early."""
        # evaluator: negotiate criteria, then evaluate → PASS
        evaluator = _StubManager([
            "criterion 1\ncriterion 2",  # negotiate
            "PASS\nLooks great",          # eval
        ])
        generator = _StubManager(["Here is the output"])

        loop = GeneratorEvaluatorLoop(generator=generator, evaluator=evaluator)
        results = await loop.run("do something", max_sprints=5)

        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].sprint == 1
        assert results[0].output == "Here is the output"
        assert results[0].critique == "Looks great"

    @pytest.mark.asyncio
    async def test_fail_then_pass_carries_critique(self):
        """Critique from sprint 1 FAIL is carried into sprint 2 generator prompt."""
        evaluator = _StubManager([
            "criterion A",      # negotiate sprint 1
            "FAIL\nMissing X",  # eval sprint 1
            "criterion A",      # negotiate sprint 2
            "PASS\nGood",       # eval sprint 2
        ])
        generator = _StubManager(["output v1", "output v2"])

        loop = GeneratorEvaluatorLoop(generator=generator, evaluator=evaluator)
        results = await loop.run("do something", max_sprints=5)

        assert len(results) == 2
        assert results[0].passed is False
        assert results[0].critique == "Missing X"
        assert results[1].passed is True
        # The generator's second prompt should mention prior critique
        gen_prompts = generator.prompts
        assert "Missing X" in gen_prompts[1]

    @pytest.mark.asyncio
    async def test_max_sprints_exhausted_returns_all(self):
        """When max_sprints is exhausted without PASS, all results are returned."""
        always_fail_eval = _StubManager(
            ["criterion A", "FAIL\nbad"] * 10
        )
        generator = _StubManager(["output"] * 10)

        loop = GeneratorEvaluatorLoop(generator=generator, evaluator=always_fail_eval)
        results = await loop.run("goal", max_sprints=3)

        assert len(results) == 3
        assert all(not r.passed for r in results)

    @pytest.mark.asyncio
    async def test_event_bus_receives_sprint_events(self):
        """sprint.passed and sprint.failed events are published to the event bus."""
        bus = CoordinationEventBus(delta_min=0.0)

        evaluator = _StubManager([
            "criterion A",
            "FAIL\nbad",
            "criterion A",
            "PASS\nok",
        ])
        generator = _StubManager(["v1", "v2"])

        loop = GeneratorEvaluatorLoop(generator=generator, evaluator=evaluator, event_bus=bus)
        results = await loop.run("goal", max_sprints=5)

        topics = [e.topic for e in bus.published_events]
        assert "sprint.failed" in topics
        assert "sprint.passed" in topics
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_no_event_bus_still_works(self):
        """Loop functions correctly when no event_bus is provided."""
        evaluator = _StubManager(["criterion A", "PASS\nok"])
        generator = _StubManager(["output"])

        loop = GeneratorEvaluatorLoop(generator=generator, evaluator=evaluator, event_bus=None)
        results = await loop.run("goal", max_sprints=1)
        assert len(results) == 1
        assert results[0].passed is True

    @pytest.mark.asyncio
    async def test_generator_failure_recorded(self):
        """A failed generator spawn produces a result with error prefix in output."""
        evaluator = _StubManager(["criterion A", "FAIL\nnot great"])
        generator = _FailingManager()

        loop = GeneratorEvaluatorLoop(generator=generator, evaluator=evaluator)
        results = await loop.run("goal", max_sprints=1)

        assert len(results) == 1
        assert "[generator error]" in results[0].output

    @pytest.mark.asyncio
    async def test_sprint_contract_criteria_used_in_eval_prompt(self):
        """The criteria from the contract appear in the evaluator's judgment prompt."""
        evaluator = _StubManager([
            "must have feature X\nmust be fast",
            "PASS\nAll criteria met",
        ])
        generator = _StubManager(["good output"])

        loop = GeneratorEvaluatorLoop(generator=generator, evaluator=evaluator)
        results = await loop.run("build something", max_sprints=1)

        # The eval prompt (second evaluator call) should contain the criteria text
        eval_prompt = evaluator.prompts[1]
        assert "must have feature X" in eval_prompt
        assert "must be fast" in eval_prompt
