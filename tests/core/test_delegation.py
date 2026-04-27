"""Tests for runtime delegation policies."""

from types import SimpleNamespace

import pytest

from loom.runtime import DelegationPolicy, DelegationRequest, DelegationResult
from loom.types import SubAgentResult


class _StubManager:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, bool]] = []

    async def spawn(
        self,
        goal: str,
        depth: int = 0,
        inherit_context: bool = True,
    ) -> SubAgentResult:
        self.calls.append((goal, depth, inherit_context))
        return SubAgentResult(success=True, output=f"done:{goal}", depth=depth + 1)


@pytest.mark.asyncio
async def test_subagent_delegation_policy_wraps_spawn_manager() -> None:
    manager = _StubManager()
    policy = DelegationPolicy.subagents(manager)

    result = await policy.delegate(
        DelegationRequest(goal="build module", depth=2, inherit_context=False)
    )

    assert result == DelegationResult(
        success=True,
        output="done:build module",
        depth=3,
    )
    assert manager.calls == [("build module", 2, False)]


@pytest.mark.asyncio
async def test_depth_limited_delegation_policy_blocks_at_limit() -> None:
    manager = _StubManager()
    policy = DelegationPolicy.depth_limited(
        2,
        delegate=DelegationPolicy.subagents(manager),
    )

    result = await policy.delegate(DelegationRequest(goal="too deep", depth=2))

    assert result.success is False
    assert result.error == "MAX_DEPTH_EXCEEDED"
    assert result.depth == 2
    assert manager.calls == []


@pytest.mark.asyncio
async def test_local_delegation_policy_uses_subagent_manager() -> None:
    class Parent:
        async def run(self, goal: str):
            return SimpleNamespace(output=f"parent:{goal}")

    policy = DelegationPolicy.local(Parent(), max_depth=3)

    result = await policy.delegate(DelegationRequest(goal="child task", depth=0))

    assert result.success is True
    assert result.output == "parent:child task"
    assert result.depth == 1


@pytest.mark.asyncio
async def test_noop_delegation_policy_reports_missing_target() -> None:
    result = await DelegationPolicy.none().delegate(DelegationRequest(goal="task"))

    assert result.success is False
    assert result.error == "NO_DELEGATION_TARGET"
