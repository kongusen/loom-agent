"""Sub-Agent management with recursion termination guarantee."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..runtime.delegation import DelegationRequest, DelegationResult
from ..types import SubAgentResult


class SubAgentManager:
    """Manage Sub-Agent spawning and lifecycle."""

    def __init__(self, parent: Any, max_depth: int = 5):
        self.parent = parent
        self.max_depth = max_depth
        self.children: list[Any] = []

    async def spawn(self, goal: str, depth: int, inherit_context: bool = True) -> SubAgentResult:
        """Spawn a sub-agent with recursion check."""
        return (
            await self.delegate(
                DelegationRequest(
                    goal=goal,
                    depth=depth,
                    inherit_context=inherit_context,
                )
            )
        ).to_subagent_result()

    async def delegate(self, request: DelegationRequest) -> DelegationResult:
        """Delegate one request using the runtime delegation protocol."""
        depth = request.depth
        if depth >= self.max_depth:
            return DelegationResult(
                success=False,
                output="Max depth reached - 能力边界已穷尽",
                depth=depth,
                error="MAX_DEPTH_EXCEEDED",
            )

        child = self._create_child(depth, inherit_context=request.inherit_context)
        child_depth = depth + 1
        try:
            result = await child.run(request.goal)
            output = result.output if hasattr(result, "output") else str(result)
            return DelegationResult(
                success=True,
                output=output,
                depth=child_depth,
            )
        except Exception as exc:
            return DelegationResult(
                success=False,
                output=str(exc),
                depth=child_depth,
                error=str(exc),
            )

    async def spawn_many(
        self,
        goals: list[str],
        depth: int,
        inherit_context: bool = True,
    ) -> list[SubAgentResult]:
        """Spawn a batch of sub-agents sequentially."""
        requests = [
            DelegationRequest(
                goal=goal,
                depth=depth,
                inherit_context=inherit_context,
            )
            for goal in goals
        ]
        return [result.to_subagent_result() for result in await self.delegate_many(requests)]

    async def delegate_many(
        self,
        requests: list[DelegationRequest],
    ) -> list[DelegationResult]:
        """Delegate a batch of requests sequentially."""
        return [await self.delegate(request) for request in requests]

    def _create_child(self, depth: int, inherit_context: bool) -> Any:
        """Create a child agent and optionally inherit selected context.

        When *inherit_context* is True the child receives a deep copy of the
        parent's full config (instructions, knowledge, model, tools).
        When False the child starts with a minimal config: same model/tools/
        generation settings but no inherited instructions or knowledge sources,
        giving it a blank working context.
        """
        from ..agent import Agent

        if isinstance(self.parent, Agent):
            if inherit_context:
                child = Agent(config=deepcopy(self.parent.config))
            else:
                from dataclasses import replace

                child = Agent(
                    config=replace(
                        self.parent.config,
                        instructions="",
                        knowledge=[],
                    )
                )
        else:
            child = self.parent

        _ = depth

        self.children.append(child)
        return child
