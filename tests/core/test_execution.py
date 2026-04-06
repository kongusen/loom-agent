"""Test execution components"""

import pytest
from loom.execution.loop import Loop
from loom.execution.state_machine import StateMachine
from loom.execution.observer import Observer
from loom.execution.decision import DecisionEngine
from loom.types import LoopState


class TestLoop:
    """Test Loop"""

    def test_loop_creation(self):
        """Test Loop creation"""
        loop = Loop(max_steps=50)
        assert loop.max_steps == 50
        assert loop.step_count == 0
        assert loop.turn_count == 0

    def test_loop_step_renew(self):
        """Test loop step with context renewal"""
        loop = Loop()
        result = loop.step(context_rho=1.0, depth=5, max_depth=10)
        assert result.state == LoopState.RENEW
        assert result.should_continue is True

    def test_loop_step_max_steps(self):
        """Test loop step reaches max steps"""
        loop = Loop(max_steps=2)
        loop.step(0.5, 5, 10)
        result = loop.step(0.5, 5, 10)
        assert result.state == LoopState.GOAL_REACHED
        assert result.should_continue is False


class TestStateMachine:
    """Test StateMachine"""

    def test_state_machine_creation(self):
        """Test StateMachine creation"""
        sm = StateMachine()
        assert sm is not None


class TestObserver:
    """Test Observer"""

    def test_observer_creation(self):
        """Test Observer creation"""
        observer = Observer()
        assert observer is not None


class TestDecisionEngine:
    """Test DecisionEngine"""

    def test_decision_engine_creation(self):
        """Test DecisionEngine creation"""
        engine = DecisionEngine()
        assert engine is not None

    def test_decision_engine_decide(self):
        """Test decision making"""
        engine = DecisionEngine()
        result = engine.decide(context_rho=0.5, depth=5, max_depth=10)
        assert result is not None
        assert result.should_continue is not None
