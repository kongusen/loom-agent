"""Test tool governance and executor integration."""

import pytest

from loom.tools.executor import ToolExecutor
from loom.tools.governance import (
    GovernanceConfig,
    ParameterConstraint,
    ToolGovernance,
    ToolPolicy,
)
from loom.tools.registry import ToolRegistry
from loom.tools.schema import Tool, ToolDefinition
from loom.types import ToolCall


async def echo_handler(text: str) -> str:
    return text


def make_tool(
    name: str,
    *,
    is_read_only: bool = True,
    is_destructive: bool = False,
) -> Tool:
    return Tool(
        definition=ToolDefinition(
            name=name,
            description=f"{name} tool",
            is_read_only=is_read_only,
            is_destructive=is_destructive,
        ),
        handler=echo_handler,
    )


class TestToolGovernance:
    """Test governance decisions."""

    def test_allowlist_blocks_unknown_tool(self):
        gov = ToolGovernance(
            GovernanceConfig(allow_tools={"Read"}, default_allow=False)
        )
        ok, reason = gov.check_permission("Write")
        assert ok is False
        assert "allowlist" in reason

    def test_denylist_blocks_tool(self):
        gov = ToolGovernance(
            GovernanceConfig(deny_tools={"Bash"})
        )
        ok, reason = gov.check_permission("Bash")
        assert ok is False
        assert "explicitly denied" in reason

    def test_read_only_policy_blocks_writes(self):
        gov = ToolGovernance(
            GovernanceConfig(read_only_only=True)
        )
        ok, reason = gov.check_permission(
            "Write",
            ToolDefinition(name="Write", description="write", is_read_only=False),
        )
        assert ok is False
        assert "not read-only" in reason

    def test_destructive_policy_blocks_tool(self):
        gov = ToolGovernance(
            GovernanceConfig(allow_destructive=False)
        )
        ok, reason = gov.check_permission(
            "Delete",
            ToolDefinition(name="Delete", description="delete", is_destructive=True),
        )
        assert ok is False
        assert "destructive" in reason

    def test_record_call_updates_rate_limit_counter(self):
        gov = ToolGovernance()
        gov.record_call("Read")
        gov.record_call("Read")
        assert gov.call_counts["Read"] == 2

    def test_parameter_violation_is_structured(self):
        gov = ToolGovernance(
            GovernanceConfig(
                tool_policies={
                    "Write": ToolPolicy(
                        tool_name="Write",
                        parameter_constraints=[
                            ParameterConstraint(
                                parameter_name="path",
                                constraint_type="regex",
                                constraint_value=r"^/safe/",
                                error_message="path must stay under /safe",
                            )
                        ],
                    )
                }
            )
        )

        ok, reason = gov.check_permission("Write", arguments={"path": "/tmp/file.txt"})

        assert ok is False
        assert "parameter=path" in reason
        violations = gov.get_last_parameter_violations()
        assert len(violations) == 1
        assert violations[0].parameter == "path"
        assert violations[0].constraint_type == "regex"
        assert violations[0].value == "/tmp/file.txt"


class TestToolExecutor:
    """Test executor integration with governance."""

    @pytest.mark.asyncio
    async def test_executor_runs_allowed_tool(self):
        registry = ToolRegistry()
        registry.register(make_tool("Read"))
        executor = ToolExecutor(registry)

        result = await executor.execute(
            ToolCall(id="1", name="Read", arguments={"text": "hello"})
        )
        assert result.is_error is False
        assert result.content == "hello"

    @pytest.mark.asyncio
    async def test_executor_blocks_denied_tool(self):
        registry = ToolRegistry()
        registry.register(make_tool("Bash", is_read_only=False))
        governance = ToolGovernance(
            GovernanceConfig(deny_tools={"Bash"})
        )
        executor = ToolExecutor(registry, governance)

        result = await executor.execute(
            ToolCall(id="1", name="Bash", arguments={"text": "hello"})
        )
        assert result.is_error is True
        assert "Permission denied" in result.content

    @pytest.mark.asyncio
    async def test_executor_enforces_read_only_mode(self):
        registry = ToolRegistry()
        registry.register(make_tool("Write", is_read_only=False))
        governance = ToolGovernance(
            GovernanceConfig(read_only_only=True)
        )
        executor = ToolExecutor(registry, governance)

        result = await executor.execute(
            ToolCall(id="1", name="Write", arguments={"text": "hello"})
        )
        assert result.is_error is True
        assert "not read-only" in result.content

    @pytest.mark.asyncio
    async def test_executor_enforces_rate_limit(self):
        registry = ToolRegistry()
        registry.register(make_tool("Read"))
        governance = ToolGovernance(
            GovernanceConfig(max_calls_per_minute=1)
        )
        executor = ToolExecutor(registry, governance)

        first = await executor.execute(
            ToolCall(id="1", name="Read", arguments={"text": "hello"})
        )
        second = await executor.execute(
            ToolCall(id="2", name="Read", arguments={"text": "world"})
        )

        assert first.is_error is False
        assert second.is_error is True
        assert "Rate limit" in second.content
