"""
Turn State Management for tt Recursive Execution

Provides immutable state tracking for the tt (tail-recursive) control loop.
Inspired by Claude Code's recursive conversation management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from uuid import uuid4


@dataclass(frozen=True)
class TurnState:
    """
    Immutable state for tt recursive execution.

    Design Principles:
    - Immutable: Uses frozen=True to prevent accidental mutation
    - Serializable: All fields are JSON-serializable for save/restore
    - Traceable: Contains turn_id and parent_turn_id for debugging

    Each recursive call to tt() creates a new TurnState via next_turn(),
    maintaining a clear lineage of turns.

    Attributes:
        turn_counter: Current recursion depth (0-based)
        turn_id: Unique identifier for this turn (UUID)
        max_iterations: Maximum recursion depth allowed
        compacted: Whether conversation history was compacted this turn
        parent_turn_id: ID of the parent turn (None for initial turn)
        metadata: Additional turn-specific data
        tool_call_history: History of tool names called (for recursion control)
        error_count: Number of errors encountered (for recursion control)
        last_outputs: Recent outputs for loop detection (for recursion control)

    Example:
        ```python
        # Initial turn
        state = TurnState.initial(max_iterations=10)
        print(state.turn_counter)  # 0
        print(state.is_initial)    # True

        # Next turn
        next_state = state.next_turn(compacted=False)
        print(next_state.turn_counter)  # 1
        print(next_state.parent_turn_id)  # <original turn_id>
        ```
    """

    turn_counter: int
    turn_id: str
    max_iterations: int = 10
    compacted: bool = False
    parent_turn_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Phase 2: Recursion control tracking
    tool_call_history: List[str] = field(default_factory=list)
    """History of tool names called (for recursion control)"""

    error_count: int = 0
    """Number of errors encountered during execution"""

    last_outputs: List[str] = field(default_factory=list)
    """Recent outputs for loop detection (limited to last 10)"""

    @staticmethod
    def initial(max_iterations: int = 10, **metadata) -> TurnState:
        """
        Create initial turn state for a new conversation.

        Args:
            max_iterations: Maximum recursion depth
            **metadata: Additional metadata to store

        Returns:
            TurnState: Initial state with turn_counter=0
        """
        return TurnState(
            turn_counter=0,
            turn_id=str(uuid4()),
            max_iterations=max_iterations,
            compacted=False,
            parent_turn_id=None,
            metadata=metadata
        )

    def next_turn(
        self,
        compacted: bool = False,
        tool_calls: Optional[List[str]] = None,
        had_error: bool = False,
        output: Optional[str] = None,
        **metadata_updates
    ) -> TurnState:
        """
        Create next turn state (immutable update).

        This is the key method for tail recursion: it creates a new TurnState
        with incremented counter while preserving other configuration.

        Args:
            compacted: Whether history was compacted in the next turn
            tool_calls: New tool calls to add to history
            had_error: Whether an error occurred in this turn
            output: Output content to add for loop detection
            **metadata_updates: Updates to metadata (merged with existing)

        Returns:
            TurnState: New state with turn_counter + 1

        Example:
            ```python
            state0 = TurnState.initial()
            state1 = state0.next_turn()  # turn_counter=1
            state2 = state1.next_turn()  # turn_counter=2
            ```
        """
        new_metadata = {**self.metadata, **metadata_updates}

        # Update tool call history
        new_tool_history = list(self.tool_call_history)
        if tool_calls:
            new_tool_history.extend(tool_calls)
        # Keep only last 20 tool calls
        new_tool_history = new_tool_history[-20:]

        # Update error count
        new_error_count = self.error_count + (1 if had_error else 0)

        # Update output history for loop detection
        new_outputs = list(self.last_outputs)
        if output:
            new_outputs.append(output)
        # Keep only last 10 outputs
        new_outputs = new_outputs[-10:]

        return TurnState(
            turn_counter=self.turn_counter + 1,
            turn_id=str(uuid4()),  # New unique ID
            max_iterations=self.max_iterations,
            compacted=compacted,
            parent_turn_id=self.turn_id,  # Link to parent
            metadata=new_metadata,
            tool_call_history=new_tool_history,
            error_count=new_error_count,
            last_outputs=new_outputs
        )

    def with_metadata(self, **kwargs) -> TurnState:
        """
        Create new state with updated metadata (without incrementing turn).

        Args:
            **kwargs: Metadata updates

        Returns:
            TurnState: New state with same turn_counter
        """
        new_metadata = {**self.metadata, **kwargs}

        return TurnState(
            turn_counter=self.turn_counter,
            turn_id=self.turn_id,
            max_iterations=self.max_iterations,
            compacted=self.compacted,
            parent_turn_id=self.parent_turn_id,
            metadata=new_metadata,
            tool_call_history=self.tool_call_history,
            error_count=self.error_count,
            last_outputs=self.last_outputs
        )

    @property
    def is_initial(self) -> bool:
        """Check if this is the initial turn."""
        return self.turn_counter == 0

    @property
    def is_final(self) -> bool:
        """Check if this turn has reached maximum depth."""
        return self.turn_counter >= self.max_iterations

    @property
    def remaining_iterations(self) -> int:
        """Get remaining recursion depth."""
        return max(0, self.max_iterations - self.turn_counter)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dict for saving/restoration.

        Returns:
            Dict: JSON-serializable representation
        """
        return {
            "turn_counter": self.turn_counter,
            "turn_id": self.turn_id,
            "max_iterations": self.max_iterations,
            "compacted": self.compacted,
            "parent_turn_id": self.parent_turn_id,
            "metadata": self.metadata,
            "tool_call_history": self.tool_call_history,
            "error_count": self.error_count,
            "last_outputs": self.last_outputs
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> TurnState:
        """
        Deserialize from dict.

        Args:
            data: Dictionary from to_dict()

        Returns:
            TurnState: Restored state
        """
        return TurnState(
            turn_counter=data["turn_counter"],
            turn_id=data["turn_id"],
            max_iterations=data.get("max_iterations", 10),
            compacted=data.get("compacted", False),
            parent_turn_id=data.get("parent_turn_id"),
            metadata=data.get("metadata", {}),
            tool_call_history=data.get("tool_call_history", []),
            error_count=data.get("error_count", 0),
            last_outputs=data.get("last_outputs", [])
        )

    def __repr__(self) -> str:
        """Human-readable representation."""
        return (
            f"TurnState(counter={self.turn_counter}/{self.max_iterations}, "
            f"id={self.turn_id[:8]}..., "
            f"compacted={self.compacted})"
        )
