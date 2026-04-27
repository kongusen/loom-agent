"""Test evolution module - engine, strategies, feedback"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from loom.evolution.engine import EvolutionEngine
from loom.evolution.feedback import FeedbackLoop
from loom.evolution.strategies import (
    EvolutionStrategy,
    PolicyOptimizationStrategy,
    ToolLearningStrategy,
)
from loom.providers.base import CompletionParams, LLMProvider
from loom.runtime.engine import AgentEngine, EngineConfig
from loom.tools.schema import Tool, ToolDefinition, ToolParameter
from loom.types import ToolCall

# ── EvolutionEngine ──


class TestEvolutionEngine:
    def test_creation(self):
        engine = EvolutionEngine()
        assert engine.strategies == []

    def test_register_strategy(self):
        engine = EvolutionEngine()
        strategy = ToolLearningStrategy()
        engine.register_strategy(strategy)
        assert len(engine.strategies) == 1
        assert engine.strategies[0] is strategy

    def test_register_multiple_strategies(self):
        engine = EvolutionEngine()
        engine.register_strategy(ToolLearningStrategy())
        engine.register_strategy(PolicyOptimizationStrategy())
        assert len(engine.strategies) == 2

    def test_evolve_applies_all_strategies(self):
        engine = EvolutionEngine()
        mock_strategy = MagicMock(spec=EvolutionStrategy)
        engine.register_strategy(mock_strategy)

        agent = MagicMock()
        engine.evolve(agent)
        mock_strategy.apply.assert_called_once_with(agent)

    def test_evolve_with_multiple_strategies(self):
        engine = EvolutionEngine()
        s1 = MagicMock(spec=EvolutionStrategy)
        s2 = MagicMock(spec=EvolutionStrategy)
        engine.register_strategy(s1)
        engine.register_strategy(s2)

        agent = MagicMock()
        engine.evolve(agent)
        s1.apply.assert_called_once_with(agent)
        s2.apply.assert_called_once_with(agent)

    def test_evolve_no_strategies(self):
        engine = EvolutionEngine()
        agent = MagicMock()
        # Should not raise
        engine.evolve(agent)

    def test_has_internal_feedback_loop(self):
        engine = EvolutionEngine()
        assert isinstance(engine.feedback_loop, FeedbackLoop)

    def test_subscribe_to_engine_wires_feedback_loop(self):
        evo_engine = EvolutionEngine()
        mock_runtime = MagicMock()
        evo_engine.subscribe_to_engine(mock_runtime)
        mock_runtime.on.assert_called_once_with(
            "tool_result", evo_engine.feedback_loop._on_tool_result
        )

    def test_evolve_injects_feedback_loop_when_missing(self):
        evo_engine = EvolutionEngine()
        agent = SimpleNamespace()
        evo_engine.evolve(agent)
        assert agent.feedback_loop is evo_engine.feedback_loop

    def test_evolve_preserves_existing_feedback_loop(self):
        evo_engine = EvolutionEngine()
        existing = FeedbackLoop()
        agent = SimpleNamespace(feedback_loop=existing)
        evo_engine.evolve(agent)
        assert agent.feedback_loop is existing

    @pytest.mark.asyncio
    async def test_end_to_end_subscribe_and_evolve(self):
        """subscribe_to_engine() + evolve() collects real tool results."""

        class MockProvider(LLMProvider):
            async def _complete(self, messages, params=None):
                return "ok"

            def stream(self, messages, params=None):
                async def _gen():
                    yield "ok"

                return _gen()

        async def noop(**_):
            return "done"

        from loom.tools.schema import Tool, ToolDefinition, ToolParameter
        from loom.types import ToolCall

        tool = Tool(
            definition=ToolDefinition(
                name="Noop",
                description="No-op tool",
                parameters=[ToolParameter(name="x", type="string", description="")],
            ),
            handler=noop,
        )
        runtime = AgentEngine(
            provider=MockProvider(),
            config=EngineConfig(enable_heartbeat=False, enable_memory=False),
            tools=[tool],
        )
        evo = EvolutionEngine()
        evo.subscribe_to_engine(runtime)

        await runtime._execute_tools([ToolCall(id="c1", name="Noop", arguments={"x": "1"})])

        assert len(evo.feedback_loop.feedback) == 1
        assert evo.feedback_loop.feedback[0]["tool"] == "Noop"
        assert evo.feedback_loop.feedback[0]["success"] is True

        # evolve() injects feedback automatically - no manual wiring needed
        agent = SimpleNamespace()
        evo.register_strategy(ToolLearningStrategy())
        evo.evolve(agent)
        assert hasattr(agent, "tool_learning")


# ── EvolutionStrategy ──


class TestToolLearningStrategy:
    def test_is_strategy(self):
        strategy = ToolLearningStrategy()
        assert isinstance(strategy, EvolutionStrategy)

    def test_apply(self):
        strategy = ToolLearningStrategy()
        feedback_loop = FeedbackLoop()
        feedback_loop.add_feedback({"tool": "Read", "type": "success", "score": 0.9})
        feedback_loop.add_feedback({"tool": "Read", "type": "success", "score": 0.8})
        feedback_loop.add_feedback({"tool": "Bash", "type": "failure", "score": 0.1})
        agent = SimpleNamespace(feedback_loop=feedback_loop)

        result = strategy.apply(agent)

        assert result["preferred_tools"] == ["Read"]
        assert result["discouraged_tools"] == ["Bash"]
        assert result["tool_stats"]["Read"]["success_rate"] == 1.0
        assert agent.tool_learning is result
        assert agent.evolution_state["tool_learning"] is result

    def test_apply_reads_feedback_list(self):
        strategy = ToolLearningStrategy(success_threshold=0.5, min_examples=2)
        agent = SimpleNamespace(
            feedback=[
                {"tool_name": "Search", "success": True},
                {"tool_name": "Search", "success": True},
                {"tool_name": "Edit", "success": False},
            ]
        )

        result = strategy.apply(agent)

        assert result["preferred_tools"] == ["Search"]
        assert result["tool_stats"]["Edit"]["failures"] == 1


class TestPolicyOptimizationStrategy:
    def test_is_strategy(self):
        strategy = PolicyOptimizationStrategy()
        assert isinstance(strategy, EvolutionStrategy)

    def test_apply(self):
        strategy = PolicyOptimizationStrategy()
        feedback_loop = FeedbackLoop()
        feedback_loop.add_feedback({"tool": "Write", "type": "blocked_by_policy"})
        feedback_loop.add_feedback({"tool": "Write", "type": "success", "success": True})
        feedback_loop.add_feedback({"tool": "Deploy", "type": "approved"})
        feedback_loop.add_feedback({"tool": "Deploy", "risk": "critical"})
        agent = SimpleNamespace(
            feedback_loop=feedback_loop,
            policy={"deny": ["Delete"], "require_approval": ["Bash"]},
        )

        result = strategy.apply(agent)

        assert result["baseline_policy"]["deny"] == ["Delete"]
        assert "Deploy" in result["suggested_policy"]["deny"]
        assert "Write" in result["recommend_relax"]
        assert "Write" in result["suggested_policy"]["require_approval"]
        assert agent.policy_optimization is result

    def test_apply_supports_policy_object(self):
        strategy = PolicyOptimizationStrategy()
        policy = SimpleNamespace(deny=["Delete"], require_approval=["Bash"])
        agent = SimpleNamespace(
            feedback=[{"tool_name": "Read", "type": "blocked_by_policy"}],
            policy=policy,
        )

        result = strategy.apply(agent)

        assert result["baseline_policy"]["require_approval"] == ["Bash"]
        assert "Read" in result["suggested_policy"]["require_approval"]


# ── FeedbackLoop ──


class TestFeedbackLoop:
    def test_creation(self):
        loop = FeedbackLoop()
        assert loop.feedback == []

    def test_add_feedback(self):
        loop = FeedbackLoop()
        fb = {"type": "success", "score": 0.9}
        loop.add_feedback(fb)
        assert len(loop.feedback) == 1
        assert loop.feedback[0] == fb

    def test_add_multiple_feedback(self):
        loop = FeedbackLoop()
        loop.add_feedback({"type": "success", "score": 0.9})
        loop.add_feedback({"type": "failure", "score": 0.2})
        loop.add_feedback({"type": "partial", "score": 0.5})
        assert len(loop.feedback) == 3

    def test_get_feedback(self):
        loop = FeedbackLoop()
        fb1 = {"type": "a"}
        fb2 = {"type": "b"}
        loop.add_feedback(fb1)
        loop.add_feedback(fb2)
        result = loop.get_feedback()
        assert result == [fb1, fb2]

    def test_get_feedback_empty(self):
        loop = FeedbackLoop()
        assert loop.get_feedback() == []

    def test_feedback_preserves_order(self):
        loop = FeedbackLoop()
        for i in range(10):
            loop.add_feedback({"index": i})
        result = loop.get_feedback()
        assert [f["index"] for f in result] == list(range(10))

    @pytest.mark.asyncio
    async def test_feedback_loop_subscribes_to_engine_tool_events(self):
        class MockProvider(LLMProvider):
            async def _complete(
                self, messages: list, params: CompletionParams | None = None
            ) -> str:
                return "ok"

            def stream(self, messages: list, params: CompletionParams | None = None):
                async def _gen():
                    yield "ok"

                return _gen()

        async def echo_handler(text: str) -> str:
            return text

        tool = Tool(
            definition=ToolDefinition(
                name="Echo",
                description="Echo text",
                parameters=[ToolParameter(name="text", type="string", description="")],
            ),
            handler=echo_handler,
        )
        engine = AgentEngine(
            provider=MockProvider(),
            config=EngineConfig(enable_heartbeat=False, enable_memory=False),
            tools=[tool],
        )
        loop = FeedbackLoop()
        loop.subscribe_to_engine(engine)

        await engine._execute_tools(
            [ToolCall(id="call_1", name="Echo", arguments={"text": "hello"})]
        )

        assert len(loop.feedback) == 1
        assert loop.feedback[0]["tool"] == "Echo"
        assert loop.feedback[0]["type"] == "success"
        assert loop.feedback[0]["success"] is True

    def test_feedback_loop_subscription_requires_event_source(self):
        loop = FeedbackLoop()
        with pytest.raises(TypeError):
            loop.subscribe_to_engine(object())
