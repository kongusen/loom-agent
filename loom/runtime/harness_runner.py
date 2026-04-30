"""Harness execution coordinator extracted from AgentEngine."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .harness import HarnessContext, HarnessOutcome, HarnessRequest
from .task import RuntimeTask


@dataclass(slots=True)
class HarnessLoopRunner:
    """Runner exposed to harnesses for one raw L* loop execution."""

    run_loop: Callable[[str, Callable[[str], Any] | None], Awaitable[dict[str, Any]]]
    token_callback: Callable[[str], Any] | None = None

    async def run(self, task: Any) -> dict[str, Any]:
        goal = getattr(task, "goal", task)
        return await self.run_loop(str(goal), self.token_callback)


class HarnessRunner:
    """Runs the configured harness strategy, falling back to the raw L* loop."""

    def __init__(
        self,
        *,
        harness: Callable[[], Any],
        run_loop: Callable[[str, Callable[[str], Any] | None], Awaitable[dict[str, Any]]],
    ) -> None:
        self.harness = harness
        self.run_loop = run_loop

    async def run(
        self,
        goal: str,
        *,
        instructions: str,
        context: dict[str, Any] | None,
        session_id: str | None,
        token_callback: Callable[[str], Any] | None = None,
    ) -> dict[str, Any]:
        harness = self.harness()
        if harness is None:
            return await self.run_loop(goal, token_callback)

        task = RuntimeTask(
            goal=goal,
            input=context or {},
            metadata={"instructions": instructions},
        )
        request = HarnessRequest(
            task=task,
            context=HarnessContext(
                runner=HarnessLoopRunner(self.run_loop, token_callback),
                session_id=session_id,
                metadata={
                    "instructions": instructions,
                    "context": context or {},
                },
            ),
        )
        run = getattr(harness, "run", None)
        if not callable(run):
            raise TypeError(
                f"runtime harness must provide async run(request), got {type(harness).__name__}"
            )

        outcome = await run(request)
        if isinstance(outcome, str):
            outcome = HarnessOutcome(output=outcome)
        if not isinstance(outcome, HarnessOutcome):
            raise TypeError(
                f"runtime harness must return HarnessOutcome or str, got {type(outcome).__name__}"
            )

        return {
            "status": "success" if outcome.passed else "harness_failed",
            "output": outcome.output,
            "events": [
                {
                    "type": "harness.completed",
                    "harness": outcome.metadata.get("harness", type(harness).__name__),
                    "passed": outcome.passed,
                    "candidates": len(outcome.candidates),
                    "selected_candidate_id": outcome.selected_candidate_id,
                }
            ],
            "iterations": outcome.iterations,
            "harness": outcome.metadata,
            "candidates": [
                {
                    "id": candidate.id,
                    "content": candidate.content,
                    "score": candidate.score,
                    "rationale": candidate.rationale,
                    "metadata": candidate.metadata,
                }
                for candidate in outcome.candidates
            ],
            "selected_candidate_id": outcome.selected_candidate_id,
        }
