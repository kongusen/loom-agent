"""
Fractal Utilities - Shared logic for fractal decomposition

Provides common utilities used by both AgentNode and FractalAgentNode
for fractal task decomposition and complexity estimation.
"""

from typing import Any

from loom.config.fractal import FractalConfig, GrowthTrigger


def estimate_task_complexity(task: str) -> float:
    """
    Estimate task complexity (0-1)

    Simple heuristic based on:
    - Task length
    - Number of conjunctions (and, or, then)
    - Keywords indicating multiple steps

    Args:
        task: Task description

    Returns:
        Complexity score between 0.0 and 1.0
    """
    task_lower = task.lower()

    # Length score
    length_score = min(1.0, len(task) / 1000)

    # Conjunction count
    conjunctions = ["and", "or", "then", "after", "before", "while"]
    conjunction_count = sum(task_lower.count(c) for c in conjunctions)
    conjunction_score = min(1.0, conjunction_count / 5)

    # Step indicators
    step_keywords = ["step", "phase", "first", "second", "finally", "component"]
    step_count = sum(task_lower.count(k) for k in step_keywords)
    step_score = min(1.0, step_count / 3)

    # Weighted average
    return (
        length_score * 0.3 +
        conjunction_score * 0.4 +
        step_score * 0.3
    )


def should_use_fractal(
    task: str,
    config: FractalConfig,
    routing_decision: Any | None = None
) -> bool:
    """
    Determine if fractal decomposition should be used

    Args:
        task: Task description
        config: Fractal configuration
        routing_decision: Optional routing decision from System 1/2 router

    Returns:
        True if fractal should be used
    """
    if not config or not config.enabled:
        return False

    trigger = config.growth_trigger

    # Never use fractal
    if trigger == GrowthTrigger.NEVER:
        return False

    # Always use fractal
    if trigger == GrowthTrigger.ALWAYS:
        return True

    # Manual only (don't auto-trigger)
    if trigger == GrowthTrigger.MANUAL:
        return False

    # SYSTEM2 trigger
    if trigger == GrowthTrigger.SYSTEM2:
        # Estimate complexity to determine if fractal growth should trigger
        complexity = estimate_task_complexity(task)
        return complexity > config.complexity_threshold

    return False
