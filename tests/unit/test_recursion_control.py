"""
Unit tests for RecursionMonitor (Phase 2: Execution Layer Optimization)

Tests the recursion control system to ensure it correctly detects
various termination conditions and prevents infinite loops.
"""

import pytest
from loom.core.recursion_control import (
    RecursionMonitor,
    RecursionState,
    TerminationReason
)


class TestRecursionMonitor:
    """Test suite for RecursionMonitor"""

    def test_max_iterations_termination(self):
        """Test that max iterations triggers termination"""
        monitor = RecursionMonitor(max_iterations=10)

        state = RecursionState(
            iteration=10,
            tool_call_history=[],
            error_count=0,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        assert reason == TerminationReason.MAX_ITERATIONS

    def test_max_iterations_not_reached(self):
        """Test that execution continues when below max iterations"""
        monitor = RecursionMonitor(max_iterations=10)

        state = RecursionState(
            iteration=5,
            tool_call_history=[],
            error_count=0,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        assert reason is None

    def test_duplicate_tools_detection(self):
        """Test detection of repeated tool calls"""
        monitor = RecursionMonitor(duplicate_threshold=3)

        # Same tool called 3 times in a row
        state = RecursionState(
            iteration=5,
            tool_call_history=["search", "search", "search"],
            error_count=0,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        assert reason == TerminationReason.DUPLICATE_TOOLS

    def test_duplicate_tools_not_detected(self):
        """Test that varied tool calls don't trigger duplicate detection"""
        monitor = RecursionMonitor(duplicate_threshold=3)

        state = RecursionState(
            iteration=5,
            tool_call_history=["search", "analyze", "search"],
            error_count=0,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        assert reason is None

    def test_loop_pattern_detection(self):
        """Test detection of repeating output patterns"""
        monitor = RecursionMonitor(loop_detection_window=3)

        # Pattern [A, B, C] repeated twice
        outputs = ["A", "B", "C", "A", "B", "C"]
        state = RecursionState(
            iteration=6,
            tool_call_history=[],
            error_count=0,
            last_outputs=outputs
        )

        reason = monitor.check_termination(state)
        assert reason == TerminationReason.LOOP_DETECTED

    def test_loop_pattern_not_detected(self):
        """Test that non-repeating patterns don't trigger loop detection"""
        monitor = RecursionMonitor(loop_detection_window=3)

        outputs = ["A", "B", "C", "D", "E", "F"]
        state = RecursionState(
            iteration=6,
            tool_call_history=[],
            error_count=0,
            last_outputs=outputs
        )

        reason = monitor.check_termination(state)
        assert reason is None

    def test_error_threshold_exceeded(self):
        """Test termination when error rate is too high"""
        monitor = RecursionMonitor(error_threshold=0.5)

        # 6 errors in 10 iterations = 60% error rate
        state = RecursionState(
            iteration=10,
            tool_call_history=[],
            error_count=6,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        assert reason == TerminationReason.ERROR_THRESHOLD

    def test_error_threshold_not_exceeded(self):
        """Test that acceptable error rates don't trigger termination"""
        monitor = RecursionMonitor(error_threshold=0.5)

        # 3 errors in 10 iterations = 30% error rate
        state = RecursionState(
            iteration=10,
            tool_call_history=[],
            error_count=3,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        assert reason is None

    def test_termination_message_generation(self):
        """Test that termination messages are correctly generated"""
        monitor = RecursionMonitor()

        # Test all termination reasons
        for reason in TerminationReason:
            message = monitor.build_termination_message(reason)
            assert isinstance(message, str)
            assert len(message) > 0
            assert "⚠️" in message

    def test_warning_at_threshold(self):
        """Test that warnings are issued near limits"""
        monitor = RecursionMonitor(max_iterations=10)

        # 80% of max iterations
        state = RecursionState(
            iteration=8,
            tool_call_history=[],
            error_count=0,
            last_outputs=[]
        )

        warning = monitor.should_add_warning(state, warning_threshold=0.8)
        assert warning is not None
        assert "remaining" in warning.lower()

    def test_no_warning_below_threshold(self):
        """Test that no warnings are issued below threshold"""
        monitor = RecursionMonitor(max_iterations=10)

        state = RecursionState(
            iteration=5,
            tool_call_history=[],
            error_count=0,
            last_outputs=[]
        )

        warning = monitor.should_add_warning(state, warning_threshold=0.8)
        assert warning is None

    def test_tool_repetition_warning(self):
        """Test warning for tool call repetition"""
        monitor = RecursionMonitor(duplicate_threshold=3)

        # 2 consecutive calls (one away from threshold)
        state = RecursionState(
            iteration=5,
            tool_call_history=["search", "search"],
            error_count=0,
            last_outputs=[]
        )

        warning = monitor.should_add_warning(state)
        assert warning is not None
        assert "search" in warning

    def test_custom_thresholds(self):
        """Test that custom thresholds are respected"""
        monitor = RecursionMonitor(
            max_iterations=100,
            duplicate_threshold=5,
            loop_detection_window=7,
            error_threshold=0.3
        )

        # Should not terminate at 50 iterations with default settings
        state = RecursionState(
            iteration=50,
            tool_call_history=[],
            error_count=0,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        assert reason is None

        # But should terminate at 100
        state = RecursionState(
            iteration=100,
            tool_call_history=[],
            error_count=0,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        assert reason == TerminationReason.MAX_ITERATIONS

    def test_empty_history_no_termination(self):
        """Test that empty histories don't cause false positives"""
        monitor = RecursionMonitor()

        state = RecursionState(
            iteration=0,
            tool_call_history=[],
            error_count=0,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        assert reason is None

    def test_priority_of_termination_reasons(self):
        """Test that max iterations has highest priority"""
        monitor = RecursionMonitor(
            max_iterations=10,
            duplicate_threshold=2
        )

        # Both max iterations and duplicate tools conditions met
        state = RecursionState(
            iteration=10,
            tool_call_history=["search", "search"],
            error_count=0,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        # Max iterations should be checked first
        assert reason == TerminationReason.MAX_ITERATIONS


class TestRecursionState:
    """Test suite for RecursionState"""

    def test_recursion_state_creation(self):
        """Test that RecursionState can be created correctly"""
        state = RecursionState(
            iteration=5,
            tool_call_history=["tool1", "tool2"],
            error_count=1,
            last_outputs=["output1", "output2"]
        )

        assert state.iteration == 5
        assert state.tool_call_history == ["tool1", "tool2"]
        assert state.error_count == 1
        assert state.last_outputs == ["output1", "output2"]

    def test_recursion_state_immutable(self):
        """Test that RecursionState fields are accessible"""
        state = RecursionState(
            iteration=0,
            tool_call_history=[],
            error_count=0,
            last_outputs=[]
        )

        # Should be able to read all fields
        assert state.iteration == 0
        assert state.tool_call_history == []
        assert state.error_count == 0
        assert state.last_outputs == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
