"""Sub-Agent management with recursion termination guarantee."""

from __future__ import annotations
from typing import TYPE_CHECKING

from ..types import SubAgentResult

if TYPE_CHECKING:
    from ..agent import Agent


class SubAgentManager:
    """Manage Sub-Agent spawning and lifecycle."""

    def __init__(self, parent: Agent, max_depth: int = 5):
        self.parent = parent
        self.max_depth = max_depth
        self.children: list[Agent] = []

    async def spawn(self, goal: str, depth: int, inherit_context: bool = True) -> SubAgentResult:
        """Spawn a sub-agent with recursion check."""
        if depth >= self.max_depth:
            return SubAgentResult(
                success=False,
                output="Max depth reached - 能力边界已穷尽",
                depth=depth,
                error="MAX_DEPTH_EXCEEDED",
            )

        child = self._create_child(depth, inherit_context=inherit_context)
        try:
            result = await child.run(goal)
            return SubAgentResult(
                success=True,
                output=result,
                depth=child.depth,
            )
        except Exception as exc:
            return SubAgentResult(
                success=False,
                output=str(exc),
                depth=child.depth,
                error=str(exc),
            )

    async def spawn_many(
        self,
        goals: list[str],
        depth: int,
        inherit_context: bool = True,
    ) -> list[SubAgentResult]:
        """Spawn a batch of sub-agents sequentially."""
        results: list[SubAgentResult] = []
        for goal in goals:
            results.append(
                await self.spawn(goal, depth=depth, inherit_context=inherit_context)
            )
        return results

    def _create_child(self, depth: int, inherit_context: bool) -> Agent:
        """Create a child agent and optionally inherit selected context."""
        child = Agent(
            provider=self.parent.provider,
            runtime_config=self.parent.runtime.config,
        )
        child.depth = depth + 1

        if inherit_context:
            child.context.current_goal = self.parent.context.current_goal
            child.context.partitions.system = self.parent.context.partitions.system

        self.children.append(child)
        return child
