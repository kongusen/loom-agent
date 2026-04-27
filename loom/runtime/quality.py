"""Runtime quality gate contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .task import RuntimeTask


@dataclass(slots=True)
class QualityContract:
    """Verifiable acceptance criteria for a runtime task."""

    goal: str
    criteria: list[str]
    eval_tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_task(
        cls,
        task: RuntimeTask,
        *,
        criteria: list[str] | None = None,
        eval_tools: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> QualityContract:
        """Build a contract from a normalized runtime task."""
        return cls(
            goal=task.goal,
            criteria=list(criteria if criteria is not None else task.criteria),
            eval_tools=list(eval_tools or []),
            metadata=dict(metadata or {}),
        )


@dataclass(slots=True)
class QualityResult:
    """Quality evaluation outcome."""

    passed: bool
    critique: str = ""
    raw_output: str = ""
    contract: QualityContract | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimeQualityGate(Protocol):
    """Protocol implemented by quality gates."""

    async def contract_for(
        self,
        task: RuntimeTask,
        *,
        iteration: int = 1,
    ) -> QualityContract: ...

    async def evaluate(
        self,
        output: str,
        contract: QualityContract,
    ) -> QualityResult: ...


class QualityGate:
    """Factory for built-in quality gate implementations."""

    @staticmethod
    def pass_fail() -> PassFailQualityGate:
        return PassFailQualityGate()

    @staticmethod
    def criteria(
        criteria: list[str] | None = None,
        *,
        goal: str | None = None,
        eval_tools: list[str] | None = None,
    ) -> CriteriaQualityGate:
        return CriteriaQualityGate(
            criteria=criteria,
            goal=goal,
            eval_tools=eval_tools,
        )

    @staticmethod
    def evaluator(
        evaluator: Any,
        *,
        parser: PassFailQualityGate | None = None,
    ) -> EvaluatorQualityGate:
        return EvaluatorQualityGate(evaluator=evaluator, parser=parser)


class PassFailQualityGate:
    """Parse explicit PASS/FAIL evaluator output into a QualityResult."""

    async def contract_for(
        self,
        task: RuntimeTask,
        *,
        iteration: int = 1,
    ) -> QualityContract:
        _ = iteration
        return QualityContract.from_task(task)

    async def evaluate(
        self,
        output: str,
        contract: QualityContract,
    ) -> QualityResult:
        return self.parse(output, contract=contract)

    def parse(
        self,
        raw: str,
        *,
        contract: QualityContract | None = None,
    ) -> QualityResult:
        """Parse evaluator text whose first line begins with PASS or FAIL."""
        lines = raw.strip().splitlines()
        if not lines:
            return QualityResult(
                passed=False,
                critique="No evaluator response",
                raw_output=raw,
                contract=contract,
            )
        verdict = lines[0].strip().upper()
        passed = verdict.startswith("PASS")
        critique = "\n".join(lines[1:]).strip()
        return QualityResult(
            passed=passed,
            critique=critique,
            raw_output=raw,
            contract=contract,
        )


class CriteriaQualityGate(PassFailQualityGate):
    """Quality gate with a static criteria contract and PASS/FAIL parsing."""

    def __init__(
        self,
        criteria: list[str] | None = None,
        *,
        goal: str | None = None,
        eval_tools: list[str] | None = None,
    ) -> None:
        self.criteria = list(criteria or [])
        self.goal = goal
        self.eval_tools = list(eval_tools or [])

    async def contract_for(
        self,
        task: RuntimeTask,
        *,
        iteration: int = 1,
    ) -> QualityContract:
        metadata = {"iteration": iteration}
        criteria = self.criteria or task.criteria
        return (
            QualityContract.from_task(
                task,
                criteria=criteria,
                eval_tools=self.eval_tools,
                metadata=metadata,
            )
            if self.goal is None
            else QualityContract(
                goal=self.goal,
                criteria=list(criteria),
                eval_tools=list(self.eval_tools),
                metadata=metadata,
            )
        )


class EvaluatorQualityGate:
    """Quality gate adapter for evaluator-style subagent managers."""

    def __init__(
        self,
        *,
        evaluator: Any,
        parser: PassFailQualityGate | None = None,
    ) -> None:
        self.evaluator = evaluator
        self.parser = parser or PassFailQualityGate()

    async def contract_for(
        self,
        task: RuntimeTask,
        *,
        iteration: int = 1,
    ) -> QualityContract:
        negotiate_prompt = self.build_contract_prompt(task.goal, iteration=iteration)
        result = await self.evaluator.spawn(negotiate_prompt, depth=0)
        raw = result.output if result.success else ""
        criteria = [line.strip() for line in str(raw).splitlines() if line.strip()]
        if not criteria:
            criteria = [f"Output addresses the goal: {task.goal}"]
        return QualityContract.from_task(
            task,
            criteria=criteria,
            metadata={"iteration": iteration},
        )

    async def evaluate(
        self,
        output: str,
        contract: QualityContract,
    ) -> QualityResult:
        eval_prompt = self.build_evaluation_prompt(output, contract)
        result = await self.evaluator.spawn(eval_prompt, depth=0)
        raw = result.output if result.success else "FAIL\nEvaluator error"
        return self.parser.parse(str(raw), contract=contract)

    def build_contract_prompt(self, goal: str, *, iteration: int = 1) -> str:
        """Prompt an evaluator to create verifiable criteria."""
        return (
            f"You are an Evaluator setting success criteria for iteration {iteration}.\n"
            f"Goal: {goal}\n\n"
            "List 3-5 concrete, verifiable criteria that the output must satisfy. "
            "Respond with one criterion per line, no numbering."
        )

    def build_evaluation_prompt(self, output: str, contract: QualityContract) -> str:
        """Prompt an evaluator to judge output against a quality contract."""
        criteria_md = "\n".join(f"- {c}" for c in contract.criteria)
        return (
            f"You are an Evaluator. Judge the following output.\n\n"
            f"**Goal:** {contract.goal}\n\n"
            f"**Success criteria:**\n{criteria_md}\n\n"
            f"**Output to evaluate:**\n{output}\n\n"
            "Respond with PASS or FAIL on the first line, then provide your "
            "critique or confirmation on subsequent lines."
        )
