"""Tests for AgentHarness and HarnessResult."""

import pytest

from loom.orchestration.harness import AgentHarness, HarnessResult
from loom.types.results import SubAgentResult


# ── Stubs ────────────────────────────────────────────────────────────────────

class _StubManager:
    """Minimal SubAgentManager stub."""

    def __init__(self, responses: list[str], *, fail: bool = False):
        self._responses = list(responses)
        self._call_count = 0
        self.prompts: list[str] = []
        self._fail = fail

    async def spawn(self, goal: str, depth: int = 0, inherit_context: bool = True) -> SubAgentResult:
        self.prompts.append(goal)
        if self._fail:
            return SubAgentResult(success=False, output="error", depth=depth + 1, error="error")
        idx = min(self._call_count, len(self._responses) - 1)
        response = self._responses[idx]
        self._call_count += 1
        return SubAgentResult(success=True, output=response, depth=depth + 1)


# ── HarnessResult ─────────────────────────────────────────────────────────────

class TestHarnessResult:
    def test_fields(self):
        result = HarnessResult(
            spec="spec text",
            output="final output",
            passed=True,
            sprints=2,
            critique="looks good",
        )
        assert result.spec == "spec text"
        assert result.output == "final output"
        assert result.passed is True
        assert result.sprints == 2
        assert result.critique == "looks good"
        assert result.sprint_results == []


# ── AgentHarness ─────────────────────────────────────────────────────────────

class TestAgentHarnessNoEvaluator:
    """Single-shot mode: generator only, no evaluator."""

    @pytest.mark.asyncio
    async def test_single_shot_pass(self):
        generator = _StubManager(["Here is the final answer"])
        harness = AgentHarness(generator=generator)

        result = await harness.run("Write a poem")

        assert isinstance(result, HarnessResult)
        assert result.passed is True
        assert result.output == "Here is the final answer"
        assert result.sprints == 1
        assert result.critique == ""
        assert result.spec == "Write a poem"   # no planner → spec == brief

    @pytest.mark.asyncio
    async def test_single_shot_generator_failure(self):
        generator = _StubManager([], fail=True)
        harness = AgentHarness(generator=generator)

        result = await harness.run("some brief")

        assert result.passed is False
        assert "[error]" in result.output


class TestAgentHarnessWithEvaluator:
    """Full Generator⇌Evaluator loop mode."""

    @pytest.mark.asyncio
    async def test_pass_on_first_sprint(self):
        evaluator = _StubManager(["criterion A", "PASS\nPerfect"])
        generator = _StubManager(["great output"])
        harness = AgentHarness(generator=generator, evaluator=evaluator, max_sprints=5)

        result = await harness.run("Build X")

        assert result.passed is True
        assert result.sprints == 1
        assert result.output == "great output"
        assert result.critique == "Perfect"
        assert len(result.sprint_results) == 1

    @pytest.mark.asyncio
    async def test_iterates_on_fail(self):
        evaluator = _StubManager([
            "criterion A",      # negotiate sprint 1
            "FAIL\nMissing Y",  # eval sprint 1
            "criterion A",      # negotiate sprint 2
            "PASS\nNow good",   # eval sprint 2
        ])
        generator = _StubManager(["v1", "v2"])
        harness = AgentHarness(generator=generator, evaluator=evaluator, max_sprints=5)

        result = await harness.run("Build X")

        assert result.passed is True
        assert result.sprints == 2
        assert result.output == "v2"
        assert len(result.sprint_results) == 2

    @pytest.mark.asyncio
    async def test_max_sprints_respected(self):
        evaluator = _StubManager(["criterion A", "FAIL\nbad"] * 10)
        generator = _StubManager(["output"] * 10)
        harness = AgentHarness(generator=generator, evaluator=evaluator, max_sprints=2)

        result = await harness.run("goal")

        assert result.sprints == 2
        assert result.passed is False


class TestAgentHarnessWithPlanner:
    """Full pipeline: planner expands brief, then generator⇌evaluator."""

    @pytest.mark.asyncio
    async def test_planner_expands_brief(self):
        planner = _StubManager(["Expanded spec: do A then B then C"])
        evaluator = _StubManager(["criterion A", "PASS\nDone"])
        generator = _StubManager(["implementation of A B C"])

        harness = AgentHarness(
            generator=generator,
            evaluator=evaluator,
            planner=planner,
            max_sprints=3,
        )

        result = await harness.run("brief description")

        assert result.spec == "Expanded spec: do A then B then C"
        assert result.passed is True
        # Generator should have received the expanded spec
        assert "Expanded spec" in generator.prompts[0]

    @pytest.mark.asyncio
    async def test_planner_failure_falls_back_to_brief(self):
        planner = _StubManager([], fail=True)
        generator = _StubManager(["output"])
        harness = AgentHarness(generator=generator, planner=planner)

        result = await harness.run("original brief")

        # Falls back to the original brief
        assert result.spec == "original brief"

    @pytest.mark.asyncio
    async def test_harness_result_completeness(self):
        """HarnessResult has all required fields populated after a full run."""
        planner = _StubManager(["Full spec"])
        evaluator = _StubManager(["pass criterion", "PASS\nAll good"])
        generator = _StubManager(["final output"])

        harness = AgentHarness(
            generator=generator,
            evaluator=evaluator,
            planner=planner,
        )
        result = await harness.run("brief")

        assert result.spec != ""
        assert result.output != ""
        assert isinstance(result.passed, bool)
        assert result.sprints >= 1
        assert isinstance(result.critique, str)
        assert isinstance(result.sprint_results, list)
