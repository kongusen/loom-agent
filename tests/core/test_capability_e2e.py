"""End-to-end smoke tests for runtime capability activation."""

import pytest

from loom import (
    Agent,
    Capability,
    InMemorySessionStore,
    Model,
    Runtime,
    SessionConfig,
)
from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider
from loom.types import ToolCall


class CapabilitySmokeProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[CompletionRequest] = []

    async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            tool_names = [tool.name for tool in request.tools]
            assert "mcp__docs__search_docs" in tool_names
            return CompletionResponse(
                tool_calls=[
                    ToolCall(
                        id="call_docs_1",
                        name="mcp__docs__search_docs",
                        arguments={"query": "loom"},
                    )
                ]
            )
        return CompletionResponse(content="Docs say Loom has runtime capabilities.")


class RestoreSmokeProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[CompletionRequest] = []

    async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        contents = [str(message["content"]) for message in request.messages]
        assert any(
            "Docs say Loom has runtime capabilities." in content for content in contents
        )
        return CompletionResponse(content="Restored transcript is visible.")


@pytest.mark.asyncio
async def test_capability_runtime_chain_records_feedback_and_restores_session() -> None:
    store = InMemorySessionStore()
    runtime = Runtime.long_running(criteria=["MCP docs are queried"])
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.mcp(
                "docs",
                instructions="Use docs carefully.",
                mock_tools=[
                    {
                        "name": "search_docs",
                        "description": "Search docs",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ],
                mock_tool_results={"search_docs": {"hits": ["runtime capabilities"]}},
            ),
            Capability.skill(
                "repo-review",
                content="# Review\nPrefer explicit runtime capabilities.",
                when_to_use="review,diff",
                allowed_tools=["mcp__docs__search_docs"],
            ),
        ],
        runtime=runtime,
        session_store=store,
    )
    provider = CapabilitySmokeProvider()
    agent._provider = provider
    agent._provider_resolved = True

    session = agent.session(SessionConfig(id="capability-smoke"))
    result = await session.run("Use docs to summarize Loom capabilities")

    feedback = runtime.feedback.get_feedback()
    saved_transcript = store.load_transcript(result.run_id)

    assert result.output == "Docs say Loom has runtime capabilities."
    assert agent.ecosystem.skill_registry.get("repo-review") is not None
    assert any(
        item["event_type"] == "tool_result"
        and item["tool_name"] == "mcp__docs__search_docs"
        and item["success"] is True
        for item in feedback
    )
    assert saved_transcript is not None
    assert saved_transcript.output == result.output

    restored_agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.mcp(
                "docs",
                mock_tools=[{"name": "search_docs", "description": "Search docs"}],
                mock_tool_results={"search_docs": {"hits": ["runtime capabilities"]}},
            )
        ],
        runtime=Runtime.long_running(criteria=["prior context is visible"]),
        session_store=store,
    )
    restore_provider = RestoreSmokeProvider()
    restored_agent._provider = restore_provider
    restored_agent._provider_resolved = True

    restored = await restored_agent.session(
        SessionConfig(id="capability-smoke")
    ).run("Continue from the previous result")

    assert restored.output == "Restored transcript is visible."
