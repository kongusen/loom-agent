"""OrchestrateStrategy — auction-based agent selection with mitosis support."""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from ..errors import AuctionNoWinnerError
from ..types import (
    AgentEvent,
    DoneEvent,
    ErrorEvent,
    StepEndEvent,
    StepStartEvent,
    TextDeltaEvent,
    TokenUsage,
)

if TYPE_CHECKING:
    from .lifecycle import LifecycleManager
    from .planner import TaskPlanner
    from .reward import RewardBus


class OrchestrateStrategy:
    name = "orchestrate"

    def __init__(
        self, cluster, reward_bus: RewardBus, lifecycle: LifecycleManager, planner: TaskPlanner
    ) -> None:
        self._cluster = cluster
        self._reward = reward_bus
        self._lifecycle = lifecycle
        self._planner = planner

    async def execute(self, ctx) -> AsyncGenerator[AgentEvent, None]:
        from ..types import TaskAd

        start = time.monotonic()
        usage = TokenUsage()
        msgs = ctx.messages
        user_msg = next((m for m in reversed(msgs) if m.role == "user"), None)
        input_text = user_msg.content if user_msg else ""

        task = TaskAd(domain="general", description=input_text, estimated_complexity=0.5)
        yield StepStartEvent(step=0, total_steps=2)

        winner = self._cluster.select_winner(task)
        if not winner:
            yield ErrorEvent(error=str(AuctionNoWinnerError(task.task_id)), recoverable=False)
            yield DoneEvent(
                content="", steps=1, duration_ms=int((time.monotonic() - start) * 1000), usage=usage
            )
            return

        yield TextDeltaEvent(text=f"[Orchestrate] Winner: {winner.id}\n")

        if self._lifecycle.should_split(task, winner):
            yield TextDeltaEvent(text="[Orchestrate] Mitosis triggered\n")

        winner.status = "busy"
        done = await winner.agent.run(input_text)
        self._reward.evaluate(winner, task, True, token_cost=getattr(done, "tokens_used", 0))
        winner.status = "idle"
        winner.last_active_at = time.time()

        yield TextDeltaEvent(text=done.content)
        yield StepEndEvent(step=0, reason="complete")
        yield DoneEvent(
            content=done.content,
            steps=1,
            duration_ms=int((time.monotonic() - start) * 1000),
            usage=usage,
        )
