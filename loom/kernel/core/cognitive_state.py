"""
Cognitive Dynamics: Explicit State Space Modeling

This module implements the mathematical abstractions from cognitive_dynamics.md:
- S (State Space / 隐空间): High-dimensional latent space
- O (Observable Manifold / 显空间): Low-dimensional observable output
- π (Projection Operator / 投影算子): S → O transformation
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThoughtState(str, Enum):
    """State of a thought process."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class Thought:
    """
    A single thought in the cognitive state space.

    Represents an active sub-process in System 2 (Deep Thinking).
    """

    id: str
    task: str
    state: ThoughtState = ThoughtState.PENDING
    result: Any | None = None
    depth: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def duration(self) -> float | None:
        """Calculate thought duration if completed."""
        if self.completed_at:
            return self.completed_at - self.created_at
        return None


@dataclass
class CognitiveState:
    """
    Explicit State Space (S ∈ R^N).

    Represents the high-dimensional internal cognitive state,
    including all active thoughts, pending insights, and latent representations.

    Philosophy from cognitive_dynamics.md:
    - S is the "place of eighty-four thousand thoughts"
    - Contains all active nodes, memory vectors, reasoning chains, uncertain hypotheses
    - High-dimensional and potentially chaotic
    """

    # Active thoughts (System 2 processes)
    active_thoughts: list[Thought] = field(default_factory=list)

    # Pending insights awaiting projection
    pending_insights: list[dict[str, Any]] = field(default_factory=list)

    # Memory embeddings (if using vector representations)
    memory_embeddings: list[float] | None = None

    # Current attention focus
    attention_focus: str | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_thought(self, thought: Thought) -> None:
        """Add a new thought to the state space."""
        self.active_thoughts.append(thought)

    def complete_thought(self, thought_id: str, result: Any) -> Thought | None:
        """Mark a thought as completed and store its result."""
        for thought in self.active_thoughts:
            if thought.id == thought_id:
                thought.state = ThoughtState.COMPLETED
                thought.result = result
                thought.completed_at = time.time()
                return thought
        return None

    def remove_thought(self, thought_id: str) -> Thought | None:
        """Remove a completed/failed thought from active list."""
        for i, thought in enumerate(self.active_thoughts):
            if thought.id == thought_id:
                return self.active_thoughts.pop(i)
        return None

    def get_thought(self, thought_id: str) -> Thought | None:
        """Retrieve a thought by ID."""
        for thought in self.active_thoughts:
            if thought.id == thought_id:
                return thought
        return None

    def get_completed_thoughts(self) -> list[Thought]:
        """Get all completed thoughts awaiting projection."""
        return [t for t in self.active_thoughts if t.state == ThoughtState.COMPLETED]

    def dimensionality(self) -> int:
        """
        Calculate the dimensionality of the state space.

        N = number of active thoughts + pending insights + other latent factors
        """
        n = len(self.active_thoughts) + len(self.pending_insights)
        if self.memory_embeddings:
            n += len(self.memory_embeddings)
        return n


@dataclass
class Observable:
    """
    Observable Manifold (O ∈ R^M).

    The low-dimensional output that can be observed and communicated.
    """

    content: str  # The text/speech output
    type: str = "text"  # text, tool_call, etc.
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ProjectionOperator:
    """
    Projection Operator π: S → O.

    Implements the mathematical projection from high-dimensional cognitive state
    to low-dimensional observable output.

    Philosophy from cognitive_dynamics.md:
    - Collapses chaos (S) into order (O)
    - Internal state (多维混沌) must project to consistent output (一致线性)
    - This is the "做功 (Work)" mechanism
    """

    def __init__(self, strategy: str = "selective"):
        """
        Args:
            strategy: Projection strategy
                - "selective": Only project completed thoughts
                - "continuous": Project all state changes
                - "threshold": Project when confidence > threshold
        """
        self.strategy = strategy

    def project(self, state: CognitiveState) -> list[Observable]:
        """
        Project cognitive state S to observable manifold O.

        Returns a list of observables representing the projection.
        """
        observables = []

        if self.strategy == "selective":
            # Only project completed thoughts
            for thought in state.get_completed_thoughts():
                observable = Observable(
                    content=f"Deep Insight: {thought.result}",
                    type="thought_projection",
                    metadata={
                        "thought_id": thought.id,
                        "depth": thought.depth,
                        "duration": thought.duration(),
                        "task": thought.task,
                    },
                )
                observables.append(observable)

        elif self.strategy == "continuous":
            # Project all state changes (more verbose)
            for thought in state.active_thoughts:
                if thought.state == ThoughtState.RUNNING:
                    observable = Observable(
                        content=f"[Thinking] {thought.task}",
                        type="thought_progress",
                        metadata={"thought_id": thought.id, "state": thought.state.value},
                    )
                    observables.append(observable)

        return observables

    def collapse(self, state: CognitiveState) -> Observable:
        """
        Perform a single collapse operation: π(S) → o.

        This is the main projection method that takes the entire state
        and produces a single coherent observable output.
        """
        # Collect all completed insights
        insights = []
        for thought in state.get_completed_thoughts():
            if thought.result:
                insights.append(str(thought.result))

        # Combine into coherent output
        if insights:
            content = " | ".join(insights)
            return Observable(
                content=content,
                type="state_collapse",
                metadata={
                    "num_insights": len(insights),
                    "state_dimensionality": state.dimensionality(),
                },
            )
        else:
            return Observable(
                content="",
                type="state_collapse",
                metadata={"state_dimensionality": state.dimensionality()},
            )


# Example usage and doctest
if __name__ == "__main__":
    # Create a cognitive state
    state = CognitiveState()

    # Add some thoughts
    thought1 = Thought(id="t1", task="Analyze complexity", depth=1)
    thought1.state = ThoughtState.COMPLETED
    thought1.result = "Complexity is O(n log n)"

    thought2 = Thought(id="t2", task="Check edge cases", depth=1)
    thought2.state = ThoughtState.COMPLETED
    thought2.result = "Found 3 edge cases"

    state.add_thought(thought1)
    state.add_thought(thought2)

    print(f"State dimensionality: {state.dimensionality()}")

    # Create projection operator
    projector = ProjectionOperator(strategy="selective")

    # Project state to observables
    observables = projector.project(state)
    for obs in observables:
        print(f"Observable: {obs.content}")

    # Collapse to single output
    collapsed = projector.collapse(state)
    print(f"Collapsed: {collapsed.content}")
