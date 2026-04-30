"""Tests for runtime feedback policy adapters."""

from types import SimpleNamespace

import pytest

from loom import Agent, Model, Runtime
from loom.evolution.engine import EvolutionEngine
from loom.evolution.strategies import ToolLearningStrategy
from loom.providers.base import CompletionResponse, LLMProvider
from loom.runtime import FeedbackEvent, FeedbackPolicy
from loom.runtime.engine import AgentEngine, EngineConfig
from loom.tools.schema import Tool, ToolDefinition, ToolParameter
from loom.types import ToolCall


async def echo_handler(text: str) -> str:
    return text


class MockProvider(LLMProvider):
    async def _complete_request(self, request):
        return CompletionResponse(content="ok")


def make_tool() -> Tool:
    return Tool(
        definition=ToolDefinition(
            name="Echo",
            description="Echo text",
            parameters=[ToolParameter(name="text", type="string", description="")],
        ),
        handler=echo_handler,
    )


def test_feedback_policy_none_ignores_events() -> None:
    policy = FeedbackPolicy.none()

    decision = policy.record(FeedbackEvent(type="tool_result", payload={"tool": "Read"}))

    assert decision.accepted is False
    assert decision.reason == "feedback disabled"
    assert policy.get_feedback() == []


def test_feedback_policy_collector_records_normalized_events() -> None:
    policy = FeedbackPolicy.collector()

    decision = policy.record(
        FeedbackEvent(
            type="tool_result",
            payload={
                "tool_name": "Read",
                "tool_call_id": "call_1",
                "success": True,
                "result": "done",
            },
            iteration=2,
        )
    )

    feedback = policy.get_feedback()
    assert decision.accepted is True
    assert feedback[0]["tool"] == "Read"
    assert feedback[0]["tool_name"] == "Read"
    assert feedback[0]["type"] == "success"
    assert feedback[0]["iteration"] == 2


@pytest.mark.asyncio
async def test_feedback_policy_attaches_to_runtime_tool_events() -> None:
    policy = FeedbackPolicy.collector()
    engine = AgentEngine(
        provider=MockProvider(),
        config=EngineConfig(enable_heartbeat=False, enable_memory=False, feedback_policy=policy),
        tools=[make_tool()],
    )

    await engine.tool_runtime.execute_tools([ToolCall(id="call_1", name="Echo", arguments={"text": "hello"})])

    feedback = policy.get_feedback()
    assert len(feedback) == 1
    assert feedback[0]["tool_name"] == "Echo"
    assert feedback[0]["success"] is True


def test_feedback_policy_evolution_wraps_existing_engine() -> None:
    evolution = EvolutionEngine()
    policy = FeedbackPolicy.evolution(evolution)

    policy.record(
        FeedbackEvent(
            type="tool_result",
            payload={"tool_name": "Search", "success": True, "result": "ok"},
        )
    )
    evolution.register_strategy(ToolLearningStrategy())
    agent = SimpleNamespace()
    policy.evolve(agent)

    assert agent.feedback_loop is evolution.feedback_loop
    assert agent.tool_learning["preferred_tools"] == ["Search"]


@pytest.mark.asyncio
async def test_agent_records_after_run_feedback_with_run_identity() -> None:
    policy = FeedbackPolicy.collector()
    agent = Agent(
        model=Model.openai("gpt-test"),
        runtime=Runtime(feedback=policy),
    )
    agent._provider = MockProvider()
    agent._provider_resolved = True

    session = agent.session()
    result = await session.run("collect run feedback")

    feedback = policy.get_feedback()
    after_run = [item for item in feedback if item["type"] == "after_run"][0]
    assert result.output == "ok"
    assert after_run["run_id"] == result.run_id
    assert after_run["session_id"] == session.id
    assert after_run["success"] is True
