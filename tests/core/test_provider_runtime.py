"""Tests for provider coordination extraction."""

from unittest.mock import MagicMock

import pytest

from loom.providers.base import CompletionResponse
from loom.runtime.engine import AgentEngine, EngineConfig
from loom.runtime.provider_runtime import ProviderRuntime
from loom.types import Message
from loom.types.stream import TextDelta


class _Context:
    current_goal = "ship"


class _Config:
    model = "gpt-test"
    completion_max_tokens = 128
    temperature = 0.2
    extensions = {"trace": True}


class _Provider:
    def __init__(self) -> None:
        self.requests = []

    async def complete_request(self, request):
        self.requests.append(request)
        return CompletionResponse(content="done")

    async def complete_request_streaming(self, request, token_callback):
        token_callback("d")
        token_callback("one")
        return CompletionResponse(content="done")

    async def stream_request_events(self, request):
        yield TextDelta(delta="done")


def _runtime(provider=None) -> ProviderRuntime:
    return ProviderRuntime(
        provider=provider or _Provider(),
        config=_Config(),
        context_manager=_Context(),
        emit=lambda *_args, **_kwargs: 0,
        current_iteration=lambda: 2,
        build_provider_tools=lambda: [],
    )


def test_provider_runtime_builds_completion_request_metadata() -> None:
    runtime = _runtime()

    request = runtime.build_completion_request([Message(role="user", content="hello")])

    assert request.messages[0]["content"] == "hello"
    assert request.params.model == "gpt-test"
    assert request.metadata == {"goal": "ship", "iteration": 2, "tool_count": 0}


@pytest.mark.asyncio
async def test_provider_runtime_calls_request_native_provider() -> None:
    provider = _Provider()
    runtime = _runtime(provider)

    response = await runtime.call_llm([Message(role="user", content="hello")])

    assert response["content"] == "done"
    assert provider.requests[0].messages[0]["content"] == "hello"


def test_agent_engine_provider_runtime_tracks_reassigned_provider() -> None:
    engine = AgentEngine(provider=MagicMock(), config=EngineConfig())
    replacement = _Provider()

    engine.provider = replacement
    engine._refresh_runtime_wiring()

    assert engine.provider_runtime.provider is replacement
