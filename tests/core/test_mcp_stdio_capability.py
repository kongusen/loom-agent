"""Real stdio coverage for MCP capabilities."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from loom import Agent, Model, Runtime, SessionConfig
from loom.config import PolicyConfig, ToolAccessPolicy, ToolPolicy
from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider
from loom.runtime import Capability, GovernancePolicy
from loom.types import ToolCall


class StdioMCPProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[CompletionRequest] = []

    async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            tool_names = [tool.name for tool in request.tools]
            assert "mcp__local-docs__search_docs" in tool_names
            return CompletionResponse(
                tool_calls=[
                    ToolCall(
                        id="call_stdio_docs",
                        name="mcp__local-docs__search_docs",
                        arguments={"query": "loom"},
                    )
                ]
            )

        contents = [str(message["content"]) for message in request.messages]
        assert any("stdio-result:loom" in content for content in contents)
        return CompletionResponse(content="stdio MCP path is working")


@pytest.mark.asyncio
async def test_mcp_capability_uses_real_stdio_server_and_governance_metadata() -> None:
    server_path = Path(__file__).parents[1] / "fixtures" / "mcp_stdio_server.py"
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.mcp(
                "local-docs",
                command=sys.executable,
                args=[str(server_path)],
                instructions="Use local docs for runtime capability questions.",
            )
        ],
        policy=PolicyConfig(
            tools=ToolPolicy(access=ToolAccessPolicy(read_only_only=True)),
        ),
        runtime=Runtime(governance=GovernancePolicy.default()),
    )
    provider = StdioMCPProvider()
    agent._provider = provider
    agent._provider_resolved = True

    try:
        bridge = agent.ecosystem.mcp_bridge
        server = bridge.servers["local-docs"]

        assert server.connected is True
        assert bridge.list_tools("local-docs")[0]["name"] == "search_docs"
        assert bridge.list_resources("local-docs")[0]["uri"] == "loom://docs/runtime"

        result = await agent.session(SessionConfig(id="mcp-stdio-smoke")).run(
            "Search local docs for Loom runtime capabilities"
        )

        assert result.output == "stdio MCP path is working"
    finally:
        _terminate_stdio_processes(agent.ecosystem.mcp_bridge)


def _terminate_stdio_processes(bridge: Any) -> None:
    procs = getattr(bridge, "_stdio_procs", {})
    for proc in list(procs.values()):
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except TimeoutError:
                proc.kill()
    procs.clear()
