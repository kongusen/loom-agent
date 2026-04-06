"""Test evolution module - engine, strategies, feedback"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from loom.evolution.engine import EvolutionEngine
from loom.evolution.strategies import (
    EvolutionStrategy,
    ToolLearningStrategy,
    PolicyOptimizationStrategy,
)
from loom.evolution.feedback import FeedbackLoop


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
