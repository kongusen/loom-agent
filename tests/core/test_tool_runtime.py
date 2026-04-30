"""Tests for runtime tool coordination extraction."""

from unittest.mock import MagicMock

import pytest

from loom.runtime.engine import AgentEngine, EngineConfig
from loom.runtime.tool_runtime import ToolRuntime
from loom.safety.hooks import HookDecision
from loom.tools.executor import ToolExecutor
from loom.tools.registry import ToolRegistry
from loom.tools.schema import Tool, ToolDefinition
from loom.types import ToolCall, ToolResult


class _ContextManager:
    current_goal = "test goal"


class _HookOutcome:
    def __init__(self, decision, message=""):
        self.decision = decision
        self.message = message


class _HookManager:
    def __init__(self, decision=HookDecision.ALLOW, message="") -> None:
        self._decision = decision
        self._message = message

    def evaluate(self, *_args, **_kwargs):
        return _HookOutcome(self._decision, self._message)


class _ToolExecutor:
    async def execute(self, call, hook_decision=None):
        return ToolResult(
            tool_call_id=call.id,
            content=f"ran:{call.name}:{hook_decision}",
            is_error=False,
        )


class _Tool:
    class _Definition:
        name = "search"
        description = "search docs"
        parameters = []

    definition = _Definition()

    def to_dict(self):
        return {"name": "search"}


class _ToolRegistry:
    def list(self):
        return [_Tool()]


def _runtime(hook_manager, emit):
    return ToolRuntime(
        emit=emit,
        current_iteration=lambda: 3,
        context_manager=_ContextManager(),
        hook_manager=hook_manager,
        tool_registry=_ToolRegistry(),
        tool_executor=_ToolExecutor(),
        governance_policy=object(),
        tool_governance=object(),
        permission_manager=None,
        veto_authority=None,
    )


def test_tool_runtime_parses_tool_calls() -> None:
    runtime = _runtime(_HookManager(), emit=lambda *_a, **_k: None)
    response = {"tool_calls": [ToolCall(id="1", name="search", arguments={}), {"x": "y"}]}

    parsed = runtime.parse_tool_calls(response)

    assert len(parsed) == 1
    assert parsed[0].name == "search"


@pytest.mark.asyncio
async def test_tool_runtime_hook_deny_short_circuits() -> None:
    events: list[str] = []
    runtime = _runtime(
        _HookManager(HookDecision.DENY, "blocked"),
        emit=lambda name, **_payload: events.append(name),
    )

    results = await runtime.execute_tools([ToolCall(id="c1", name="search", arguments={})])

    assert len(results) == 1
    assert results[0].is_error is True
    assert "Hook denied" in str(results[0].content)
    assert events == ["before_tool", "tool_result"]


def test_agent_engine_tool_runtime_tracks_reassigned_registry() -> None:
    async def handler() -> str:
        return "ok"

    registry = ToolRegistry()
    registry.register(
        Tool(
            definition=ToolDefinition(name="dynamic", description="dynamic tool"),
            handler=handler,
        )
    )
    engine = AgentEngine(provider=MagicMock(), config=EngineConfig())

    engine.tool_registry = registry

    engine.runtime_wiring.refresh_tool_runtime()
    provider_specs = engine.tool_runtime.build_provider_tool_specs()
    assert [spec.name for spec in provider_specs] == ["dynamic"]


@pytest.mark.asyncio
async def test_agent_engine_tool_runtime_tracks_reassigned_executor() -> None:
    async def handler() -> str:
        return "ok"

    registry = ToolRegistry()
    registry.register(
        Tool(
            definition=ToolDefinition(name="dynamic", description="dynamic tool"),
            handler=handler,
        )
    )
    engine = AgentEngine(provider=MagicMock(), config=EngineConfig())

    engine.tool_registry = registry
    engine.tool_executor = ToolExecutor(registry)

    engine.runtime_wiring.refresh_tool_runtime()
    results = await engine.tool_runtime.execute_tools(
        [ToolCall(id="c1", name="dynamic", arguments={})]
    )
    assert len(results) == 1
    assert results[0].content == "ok"
