"""Governance coverage for tools introduced through capabilities."""

import pytest

from loom import Agent, Model, Runtime
from loom.config import (
    PolicyConfig,
    ToolAccessPolicy,
    ToolPolicy,
    ToolRateLimitPolicy,
)
from loom.providers.base import CompletionResponse, LLMProvider
from loom.runtime import Capability, GovernancePolicy
from loom.tools.governance import GovernanceConfig, ToolGovernance
from loom.types import ToolCall


class MockProvider(LLMProvider):
    async def _complete_request(self, request):
        return CompletionResponse(content="ok")


def build_engine(agent: Agent):
    provider = MockProvider()
    agent._provider = provider
    agent._provider_resolved = True
    return agent._build_engine(provider)


@pytest.mark.asyncio
async def test_governance_denylist_blocks_builtin_capability_tool() -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[Capability.shell(require_approval=False)],
        policy=PolicyConfig(
            tools=ToolPolicy(access=ToolAccessPolicy(deny=["Bash"])),
        ),
        runtime=Runtime(governance=GovernancePolicy.default()),
    )
    engine = build_engine(agent)

    [result] = await engine.tool_runtime.execute_tools(
        [ToolCall(id="call_1", name="Bash", arguments={"command": "echo blocked"})]
    )

    assert result.is_error is True
    assert "explicitly denied" in result.content


@pytest.mark.asyncio
async def test_governance_read_only_mode_blocks_write_capability_tool() -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[Capability.files(read_only=False)],
        policy=PolicyConfig(
            tools=ToolPolicy(access=ToolAccessPolicy(read_only_only=True)),
        ),
        runtime=Runtime(governance=GovernancePolicy.default()),
    )
    engine = build_engine(agent)

    [result] = await engine.tool_runtime.execute_tools(
        [
            ToolCall(
                id="call_1",
                name="Write",
                arguments={"file_path": "/tmp/loom-governance-blocked.txt", "content": "no"},
            )
        ]
    )

    assert result.is_error is True
    assert "not read-only" in result.content


@pytest.mark.asyncio
async def test_governance_rate_limit_applies_to_capability_tools() -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[Capability.files(read_only=True)],
        policy=PolicyConfig(
            tools=ToolPolicy(rate_limits=ToolRateLimitPolicy(max_calls_per_minute=1)),
        ),
        runtime=Runtime(governance=GovernancePolicy.default()),
    )
    engine = build_engine(agent)

    first = await engine.tool_runtime.execute_tools(
        [
            ToolCall(
                id="call_1",
                name="Read",
                arguments={"file_path": "README.md", "limit": 1},
            )
        ]
    )
    second = await engine.tool_runtime.execute_tools(
        [
            ToolCall(
                id="call_2",
                name="Read",
                arguments={"file_path": "README.md", "limit": 1},
            )
        ]
    )

    assert first[0].is_error is False
    assert second[0].is_error is True
    assert "Rate limit" in second[0].content or "rate limit" in second[0].content


@pytest.mark.asyncio
async def test_mcp_capability_read_only_metadata_allows_read_only_policy() -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.mcp(
                "docs",
                mock_tools=[
                    {
                        "name": "search_docs",
                        "description": "Search docs",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                        "annotations": {"readOnlyHint": True},
                    }
                ],
                mock_tool_results={"search_docs": {"hits": ["loom"]}},
            )
        ],
        policy=PolicyConfig(
            tools=ToolPolicy(access=ToolAccessPolicy(read_only_only=True)),
        ),
        runtime=Runtime(governance=GovernancePolicy.default()),
    )
    engine = build_engine(agent)

    [result] = await engine.tool_runtime.execute_tools(
        [
            ToolCall(
                id="call_1",
                name="mcp__docs__search_docs",
                arguments={"query": "loom"},
            )
        ]
    )

    assert result.is_error is False
    assert "loom" in result.content


@pytest.mark.asyncio
async def test_mcp_capability_destructive_metadata_is_governed() -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.mcp(
                "deploy",
                mock_tools=[
                    {
                        "name": "delete_env",
                        "description": "Delete an environment",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"env": {"type": "string"}},
                            "required": ["env"],
                        },
                        "annotations": {"destructiveHint": True},
                    }
                ],
                mock_tool_results={"delete_env": {"deleted": True}},
            )
        ],
        runtime=Runtime(governance=GovernancePolicy.default()),
    )
    engine = build_engine(agent)

    [result] = await engine.tool_runtime.execute_tools(
        [
            ToolCall(
                id="call_1",
                name="mcp__deploy__delete_env",
                arguments={"env": "prod"},
            )
        ]
    )

    assert result.is_error is True
    assert "destructive" in result.content


@pytest.mark.asyncio
async def test_custom_governance_policy_can_veto_capability_tool() -> None:
    tool_governance = ToolGovernance(
        GovernanceConfig(
            context_policy=lambda tool_name, _context, arguments, _runtime: (
                False,
                "production docs are blocked",
            )
            if tool_name == "mcp__docs__search_docs" and arguments.get("query") == "prod"
            else (True, "")
        )
    )
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.mcp(
                "docs",
                mock_tools=[{"name": "search_docs", "description": "Search docs"}],
                mock_tool_results={"search_docs": {"hits": ["prod"]}},
            )
        ],
        runtime=Runtime(
            governance=GovernancePolicy.default(tool_governance=tool_governance),
        ),
    )
    engine = build_engine(agent)

    [result] = await engine.tool_runtime.execute_tools(
        [
            ToolCall(
                id="call_1",
                name="mcp__docs__search_docs",
                arguments={"query": "prod"},
            )
        ]
    )

    assert result.is_error is True
    assert "production docs are blocked" in result.content
