"""
Recursion Control for Agent Executor

Provides generic recursion termination detection to prevent infinite loops
in agent execution. This is a framework-level capability that doesn't depend
on specific business logic.

New in Loom 0.0.4: Phase 2 - Execution Layer Optimization
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Any


class TerminationReason(str, Enum):
    """Reasons for terminating recursive execution"""

    MAX_ITERATIONS = "max_iterations"
    """Maximum iteration limit reached"""

    DUPLICATE_TOOLS = "duplicate_tools"
    """Detected repeated tool calls (same tool called multiple times in a row)"""

    LOOP_DETECTED = "loop_detected"
    """Detected a pattern loop in outputs"""

    ERROR_THRESHOLD = "error_threshold"
    """Error rate exceeded acceptable threshold"""


@dataclass
class RecursionState:
    """
    State information for recursion monitoring.

    This is a separate state object from TurnState to avoid coupling
    the recursion control logic with the turn management logic.

    Attributes:
        iteration: Current iteration count (0-based)
        tool_call_history: List of tool names called in recent iterations
        error_count: Number of errors encountered so far
        last_outputs: Recent output samples for loop detection
    """

    iteration: int
    """Current iteration count (0-based)"""

    tool_call_history: List[str]
    """History of tool names called (for duplicate detection)"""

    error_count: int
    """Number of errors encountered during execution"""

    last_outputs: List[Any]
    """Recent outputs for loop pattern detection"""


class RecursionMonitor:
    """
    Generic recursion monitoring and termination detection.

    This monitor provides framework-level recursion control without
    depending on any specific business logic. It detects common
    infinite loop patterns:

    1. Maximum iteration limit
    2. Repeated tool calls (same tool called N times in a row)
    3. Loop patterns in outputs
    4. High error rates

    Example:
        ```python
        # Create monitor with custom thresholds
        monitor = RecursionMonitor(
            max_iterations=50,
            duplicate_threshold=3,
            loop_detection_window=5,
            error_threshold=0.5
        )

        # Check if should terminate
        state = RecursionState(
            iteration=10,
            tool_call_history=["search", "search", "search"],
            error_count=2,
            last_outputs=[]
        )

        reason = monitor.check_termination(state)
        if reason:
            message = monitor.build_termination_message(reason)
            print(f"Terminating: {message}")
        ```
    """

    def __init__(
        self,
        max_iterations: int = 50,
        duplicate_threshold: int = 3,
        loop_detection_window: int = 5,
        error_threshold: float = 0.5
    ):
        """
        Initialize recursion monitor.

        Args:
            max_iterations: Maximum number of recursive iterations allowed
            duplicate_threshold: Number of consecutive duplicate tool calls before terminating
            loop_detection_window: Window size for loop pattern detection
            error_threshold: Maximum error rate (errors/iterations) before terminating
        """
        self.max_iterations = max_iterations
        self.duplicate_threshold = duplicate_threshold
        self.loop_detection_window = loop_detection_window
        self.error_threshold = error_threshold

    def check_termination(
        self,
        state: RecursionState
    ) -> Optional[TerminationReason]:
        """
        Check if recursive execution should terminate.

        This method runs multiple checks in priority order:
        1. Max iterations (highest priority - hard limit)
        2. Duplicate tool calls (likely stuck)
        3. Loop patterns (repeating behavior)
        4. Error threshold (too many failures)

        Args:
            state: Current recursion state

        Returns:
            TerminationReason if should terminate, None to continue
        """
        # Check 1: Maximum iterations (hard limit)
        if state.iteration >= self.max_iterations:
            return TerminationReason.MAX_ITERATIONS

        # Check 2: Duplicate tool calls (likely stuck)
        if self._detect_duplicate_tools(state.tool_call_history):
            return TerminationReason.DUPLICATE_TOOLS

        # Check 3: Loop patterns in outputs
        if self._detect_loop_pattern(state.last_outputs):
            return TerminationReason.LOOP_DETECTED

        # Check 4: Error rate threshold
        if self._check_error_threshold(state):
            return TerminationReason.ERROR_THRESHOLD

        return None

    def _detect_duplicate_tools(self, tool_history: List[str]) -> bool:
        """
        Detect if the same tool has been called too many times in a row.

        This indicates the agent is stuck in a loop, repeatedly trying
        the same tool without making progress.

        Args:
            tool_history: List of tool names (most recent last)

        Returns:
            True if duplicate pattern detected
        """
        if len(tool_history) < self.duplicate_threshold:
            return False

        # Check last N tool calls
        recent = tool_history[-self.duplicate_threshold:]

        # All the same? -> Stuck in loop
        return len(set(recent)) == 1

    def _detect_loop_pattern(self, outputs: List[Any]) -> bool:
        """
        Detect if outputs are repeating in a pattern.

        This checks if the agent is generating the same outputs
        repeatedly, indicating a stuck state.

        Args:
            outputs: Recent output values

        Returns:
            True if loop pattern detected
        """
        if len(outputs) < self.loop_detection_window * 2:
            return False

        window_size = self.loop_detection_window
        recent = outputs[-window_size * 2:]

        # Split into two halves and compare
        first_half = recent[:window_size]
        second_half = recent[window_size:]

        # If both halves are identical, we have a loop
        return first_half == second_half

    def _check_error_threshold(self, state: RecursionState) -> bool:
        """
        Check if error rate exceeds acceptable threshold.

        Too many errors indicate the agent cannot complete the task
        and should stop trying.

        Args:
            state: Current recursion state

        Returns:
            True if error rate exceeds threshold
        """
        if state.iteration == 0:
            return False

        error_rate = state.error_count / state.iteration
        return error_rate > self.error_threshold

    def build_termination_message(
        self,
        reason: TerminationReason
    ) -> str:
        """
        Build a user-friendly termination message.

        This message is injected into the conversation to prompt
        the LLM to complete the task with available information.

        Args:
            reason: The termination reason

        Returns:
            Formatted termination message
        """
        messages = {
            TerminationReason.DUPLICATE_TOOLS: (
                "⚠️ Detected repeated tool calls. "
                "Please proceed with available information."
            ),
            TerminationReason.LOOP_DETECTED: (
                "⚠️ Detected execution loop. "
                "Please break the pattern and complete the task."
            ),
            TerminationReason.MAX_ITERATIONS: (
                "⚠️ Maximum iterations reached. "
                "Please provide the best answer with current information."
            ),
            TerminationReason.ERROR_THRESHOLD: (
                "⚠️ Too many errors occurred. "
                "Please complete the task with current information."
            )
        }

        return messages.get(reason, "Please complete the task now.")

    def should_add_warning(
        self,
        state: RecursionState,
        warning_threshold: float = 0.8
    ) -> Optional[str]:
        """
        Check if a warning should be added before termination.

        This provides early warning when approaching limits,
        giving the agent a chance to wrap up gracefully.

        Args:
            state: Current recursion state
            warning_threshold: Fraction of limit at which to warn (0.0-1.0)

        Returns:
            Warning message if applicable, None otherwise
        """
        # Check if approaching max iterations
        progress = state.iteration / self.max_iterations
        if progress >= warning_threshold:
            remaining = self.max_iterations - state.iteration
            return (
                f"⚠️ Approaching iteration limit ({remaining} remaining). "
                f"Please work towards completing the task."
            )

        # Check if tool calls are becoming repetitive
        if len(state.tool_call_history) >= self.duplicate_threshold - 1:
            recent = state.tool_call_history[-(self.duplicate_threshold - 1):]
            if len(set(recent)) == 1:
                return (
                    f"⚠️ You've called '{recent[0]}' multiple times. "
                    f"Consider trying a different approach or completing the task."
                )

        return None
