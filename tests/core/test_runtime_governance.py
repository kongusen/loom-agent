"""Tests for runtime governance policy adapters."""

import pytest

from loom.runtime import GovernancePolicy, GovernanceRequest
from loom.safety.permissions import PermissionManager
from loom.safety.veto import VetoAuthority, VetoRule
from loom.tools.executor import ToolExecutor
from loom.tools.governance import GovernanceConfig, ToolGovernance
from loom.tools.registry import ToolRegistry
from loom.tools.schema import Tool, ToolDefinition
from loom.types import ToolCall


async def echo_handler(text: str) -> str:
    return text


def make_tool(name: str, *, is_read_only: bool = True) -> Tool:
    return Tool(
        definition=ToolDefinition(
            name=name,
            description=f"{name} tool",
            is_read_only=is_read_only,
        ),
        handler=echo_handler,
    )


def test_governance_policy_denies_from_permission_manager() -> None:
    permissions = PermissionManager()
    permissions.revoke("Bash", "execute", note="shell disabled")
    policy = GovernancePolicy.default(permission_manager=permissions)

    decision = policy.evaluate_tool(GovernanceRequest(tool_name="Bash"))

    assert decision.allowed is False
    assert decision.source == "permission"
    assert decision.reason == "shell disabled"


def test_governance_policy_denies_from_veto_authority() -> None:
    veto = VetoAuthority()
    veto.add_rule(
        VetoRule(
            name="no-prod",
            predicate=lambda tool, args: args.get("env") == "prod",
            reason="production is blocked",
        )
    )
    policy = GovernancePolicy.default(veto_authority=veto)

    decision = policy.evaluate_tool(
        GovernanceRequest(tool_name="deploy", arguments={"env": "prod"})
    )

    assert decision.allowed is False
    assert decision.source == "veto"
    assert decision.reason == "production is blocked"
    assert veto.audit_summary()["sources"] == ["rule:no-prod"]


def test_governance_policy_denies_from_tool_governance() -> None:
    tool_governance = ToolGovernance(GovernanceConfig(deny_tools={"Bash"}))
    policy = GovernancePolicy.default(tool_governance=tool_governance)

    decision = policy.evaluate_tool(GovernanceRequest(tool_name="Bash"))

    assert decision.allowed is False
    assert decision.source == "tool_governance"
    assert "explicitly denied" in decision.reason


def test_governance_policy_enforces_rate_limit_and_records_success() -> None:
    tool_governance = ToolGovernance(GovernanceConfig(max_calls_per_minute=1))
    policy = GovernancePolicy.default(tool_governance=tool_governance)
    request = GovernanceRequest(tool_name="Read")

    first = policy.evaluate_tool(request)
    policy.record_tool_result(request, success=True)
    second = policy.evaluate_tool(request)

    assert first.allowed is True
    assert second.allowed is False
    assert second.source == "rate_limit"


@pytest.mark.asyncio
async def test_tool_executor_uses_runtime_governance_policy() -> None:
    registry = ToolRegistry()
    registry.register(make_tool("Bash", is_read_only=False))
    policy = GovernancePolicy.deny_all("blocked by runtime policy")
    executor = ToolExecutor(registry, governance_policy=policy)

    result = await executor.execute(ToolCall(id="1", name="Bash", arguments={"text": "hello"}))

    assert result.is_error is True
    assert "blocked by runtime policy" in result.content


@pytest.mark.asyncio
async def test_tool_executor_records_runtime_governance_success() -> None:
    registry = ToolRegistry()
    registry.register(make_tool("Read"))
    tool_governance = ToolGovernance(GovernanceConfig(max_calls_per_minute=1))
    policy = GovernancePolicy.default(tool_governance=tool_governance)
    executor = ToolExecutor(registry, governance_policy=policy)

    first = await executor.execute(ToolCall(id="1", name="Read", arguments={"text": "hello"}))
    second = await executor.execute(ToolCall(id="2", name="Read", arguments={"text": "world"}))

    assert first.is_error is False
    assert second.is_error is True
    assert "Rate limit" in second.content or "rate limit" in second.content
