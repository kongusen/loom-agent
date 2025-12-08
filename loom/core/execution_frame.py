"""
Execution Frame: The Core Data Structure for Recursive State Machine

This module implements the "stack frame" concept for loom-agent's recursive execution.
Each frame represents one level of the tt (thought-tool) recursion, containing:
- Complete message history snapshot
- Compressed context state
- Tool execution results
- LLM responses
- Execution phase information

Design Philosophy:
- Inspired by Python's call stack and React's Fiber architecture
- Enables time-travel debugging through frame navigation
- Supports event sourcing through complete state capture
- Immutable design for reliable state tracking

Key Difference from LangGraph:
- LangGraph: Flat state dictionary with graph nodes
- loom-agent: Hierarchical execution frames with recursive depth

Example:
    ```python
    # Initial frame
    frame0 = ExecutionFrame.initial(
        prompt="Search Python docs",
        max_iterations=10
    )

    # After LLM call
    frame1 = frame0.with_llm_response(
        response="I'll search for Python documentation",
        tool_calls=[ToolCall(name="search", args={"query": "Python"})]
    )

    # After tool execution
    frame2 = frame1.with_tool_results([
        ToolResult(tool_call_id="call_1", content="Found 10 docs")
    ])

    # Navigate the stack
    print(frame2.parent_frame_id)  # → frame1.frame_id
    print(frame2.depth)            # → 2
    ```
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import uuid4


class ExecutionPhase(Enum):
    """
    Execution phases in the tt recursive loop.

    Maps to AgentExecutor phases:
    - INITIAL: Frame just created
    - CONTEXT_ASSEMBLY: Phase 1 - Building system context
    - LLM_CALL: Phase 2 - Calling LLM
    - DECISION: Phase 3 - Determining next action
    - TOOL_EXECUTION: Phase 4 - Executing tools
    - RECURSION: Phase 5 - Preparing recursive call
    - COMPLETED: Frame finished executing
    - TERMINATED: Frame terminated early (error/limit)
    """
    INITIAL = "initial"
    CONTEXT_ASSEMBLY = "context_assembly"
    LLM_CALL = "llm_call"
    DECISION = "decision"
    TOOL_EXECUTION = "tool_execution"
    RECURSION = "recursion"
    COMPLETED = "completed"
    TERMINATED = "terminated"


@dataclass(frozen=True)
class ExecutionFrame:
    """
    Immutable execution frame representing one level of tt recursion.

    This is the core data structure that enables:
    - Time-travel debugging (navigate frame history)
    - Event sourcing (reconstruct from events)
    - Checkpointing (serialize/deserialize frames)
    - Context management (track what LLM sees)

    Attributes:
        frame_id: Unique identifier for this frame
        parent_frame_id: ID of parent frame (None for root)
        depth: Recursion depth (0-indexed)
        phase: Current execution phase
        created_at: Unix timestamp when frame was created

        # Message & Context
        messages: List of message dictionaries (user/assistant/tool)
        context_snapshot: Compressed context from ContextAssembler
        context_metadata: Metadata about context assembly decisions

        # LLM Interaction
        llm_response: Complete LLM response text
        llm_tool_calls: Tool calls requested by LLM

        # Tool Execution
        tool_results: Results from tool executions in this frame

        # Recursion Control (from old TurnState)
        max_iterations: Maximum recursion depth allowed
        tool_call_history: History of tool names (last 20)
        error_count: Number of errors encountered
        last_outputs: Recent outputs for loop detection (last 10)

        # Metadata
        metadata: Additional frame-specific data
    """

    # Identity & Navigation
    frame_id: str
    parent_frame_id: Optional[str] = None
    depth: int = 0
    phase: ExecutionPhase = ExecutionPhase.INITIAL
    created_at: float = field(default_factory=time.time)

    # Message History & Context
    messages: List[Dict[str, Any]] = field(default_factory=list)
    """Complete message history at this frame"""

    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    """Compressed context from ContextAssembler (your 8-segment compression)"""

    context_metadata: Dict[str, Any] = field(default_factory=dict)
    """
    Metadata about context assembly:
    - components_included: List of component names
    - components_truncated: List of truncated components
    - token_usage: Token budget usage
    - compression_applied: Whether compression was triggered
    """

    # LLM Interaction
    llm_response: Optional[str] = None
    """Complete LLM response text"""

    llm_tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    """Tool calls requested by LLM (serialized ToolCall objects)"""

    # Tool Execution
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    """Tool execution results (serialized ToolResult objects)"""

    # Recursion Control (inherited from TurnState)
    max_iterations: int = 10
    tool_call_history: List[str] = field(default_factory=list)
    error_count: int = 0
    last_outputs: List[str] = field(default_factory=list)

    # Extensibility
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ===== Factory Methods =====

    @staticmethod
    def initial(
        prompt: str,
        max_iterations: int = 50,
        system_instructions: Optional[str] = None,
        **metadata
    ) -> ExecutionFrame:
        """
        Create initial frame for a new execution.

        Args:
            prompt: User's initial prompt
            max_iterations: Maximum recursion depth
            system_instructions: Optional system instructions
            **metadata: Additional metadata

        Returns:
            ExecutionFrame: Initial frame at depth 0
        """
        messages = []
        if system_instructions:
            messages.append({"role": "system", "content": system_instructions})
        messages.append({"role": "user", "content": prompt})

        return ExecutionFrame(
            frame_id=str(uuid4()),
            parent_frame_id=None,
            depth=0,
            phase=ExecutionPhase.INITIAL,
            messages=messages,
            max_iterations=max_iterations,
            metadata=metadata
        )

    # ===== Immutable Update Methods =====

    def with_phase(self, phase: ExecutionPhase) -> ExecutionFrame:
        """Transition to a new execution phase."""
        return ExecutionFrame(
            frame_id=self.frame_id,
            parent_frame_id=self.parent_frame_id,
            depth=self.depth,
            phase=phase,
            created_at=self.created_at,
            messages=self.messages,
            context_snapshot=self.context_snapshot,
            context_metadata=self.context_metadata,
            llm_response=self.llm_response,
            llm_tool_calls=self.llm_tool_calls,
            tool_results=self.tool_results,
            max_iterations=self.max_iterations,
            tool_call_history=self.tool_call_history,
            error_count=self.error_count,
            last_outputs=self.last_outputs,
            metadata=self.metadata
        )

    def with_context(
        self,
        context_snapshot: Dict[str, Any],
        context_metadata: Dict[str, Any]
    ) -> ExecutionFrame:
        """Update context after assembly."""
        return ExecutionFrame(
            frame_id=self.frame_id,
            parent_frame_id=self.parent_frame_id,
            depth=self.depth,
            phase=ExecutionPhase.CONTEXT_ASSEMBLY,
            created_at=self.created_at,
            messages=self.messages,
            context_snapshot=context_snapshot,
            context_metadata=context_metadata,
            llm_response=self.llm_response,
            llm_tool_calls=self.llm_tool_calls,
            tool_results=self.tool_results,
            max_iterations=self.max_iterations,
            tool_call_history=self.tool_call_history,
            error_count=self.error_count,
            last_outputs=self.last_outputs,
            metadata=self.metadata
        )

    def with_llm_response(
        self,
        response: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> ExecutionFrame:
        """Update frame after LLM call."""
        # Track output for loop detection
        new_outputs = list(self.last_outputs)
        new_outputs.append(response[:200])  # First 200 chars
        new_outputs = new_outputs[-10:]  # Keep last 10

        return ExecutionFrame(
            frame_id=self.frame_id,
            parent_frame_id=self.parent_frame_id,
            depth=self.depth,
            phase=ExecutionPhase.LLM_CALL,
            created_at=self.created_at,
            messages=self.messages,
            context_snapshot=self.context_snapshot,
            context_metadata=self.context_metadata,
            llm_response=response,
            llm_tool_calls=tool_calls or [],
            tool_results=self.tool_results,
            max_iterations=self.max_iterations,
            tool_call_history=self.tool_call_history,
            error_count=self.error_count,
            last_outputs=new_outputs,
            metadata=self.metadata
        )

    def with_tool_results(
        self,
        tool_results: List[Dict[str, Any]],
        had_error: bool = False
    ) -> ExecutionFrame:
        """Update frame after tool execution."""
        # Track tool calls for recursion control
        new_tool_history = list(self.tool_call_history)
        for result in tool_results:
            new_tool_history.append(result["tool_name"])
        new_tool_history = new_tool_history[-20:]  # Keep last 20

        # Update error count
        new_error_count = self.error_count + (1 if had_error else 0)

        return ExecutionFrame(
            frame_id=self.frame_id,
            parent_frame_id=self.parent_frame_id,
            depth=self.depth,
            phase=ExecutionPhase.TOOL_EXECUTION,
            created_at=self.created_at,
            messages=self.messages,
            context_snapshot=self.context_snapshot,
            context_metadata=self.context_metadata,
            llm_response=self.llm_response,
            llm_tool_calls=self.llm_tool_calls,
            tool_results=tool_results,
            max_iterations=self.max_iterations,
            tool_call_history=new_tool_history,
            error_count=new_error_count,
            last_outputs=self.last_outputs,
            metadata=self.metadata
        )

    def next_frame(self, new_messages: List[Dict[str, Any]]) -> ExecutionFrame:
        """
        Create next frame for recursion (the key method for tt recursion).

        This creates a child frame with:
        - Incremented depth
        - New frame_id
        - Updated message history
        - Link to parent via parent_frame_id

        Args:
            new_messages: Updated message list after adding LLM response and tool results

        Returns:
            ExecutionFrame: New frame at depth + 1
        """
        return ExecutionFrame(
            frame_id=str(uuid4()),
            parent_frame_id=self.frame_id,  # Link to parent
            depth=self.depth + 1,
            phase=ExecutionPhase.INITIAL,
            created_at=time.time(),
            messages=new_messages,
            context_snapshot={},  # Reset context
            context_metadata={},
            llm_response=None,
            llm_tool_calls=[],
            tool_results=[],
            max_iterations=self.max_iterations,
            tool_call_history=self.tool_call_history,  # Carry forward
            error_count=self.error_count,
            last_outputs=self.last_outputs,
            metadata=self.metadata
        )

    def with_metadata(self, **kwargs) -> ExecutionFrame:
        """Update metadata without changing other fields."""
        new_metadata = {**self.metadata, **kwargs}

        return ExecutionFrame(
            frame_id=self.frame_id,
            parent_frame_id=self.parent_frame_id,
            depth=self.depth,
            phase=self.phase,
            created_at=self.created_at,
            messages=self.messages,
            context_snapshot=self.context_snapshot,
            context_metadata=self.context_metadata,
            llm_response=self.llm_response,
            llm_tool_calls=self.llm_tool_calls,
            tool_results=self.tool_results,
            max_iterations=self.max_iterations,
            tool_call_history=self.tool_call_history,
            error_count=self.error_count,
            last_outputs=self.last_outputs,
            metadata=new_metadata
        )

    # ===== Properties =====

    @property
    def is_root(self) -> bool:
        """Check if this is the root frame."""
        return self.depth == 0 and self.parent_frame_id is None

    @property
    def is_final(self) -> bool:
        """Check if this frame reached maximum depth."""
        return self.depth >= self.max_iterations

    @property
    def remaining_iterations(self) -> int:
        """Get remaining recursion depth."""
        return max(0, self.max_iterations - self.depth)

    @property
    def has_tool_calls(self) -> bool:
        """Check if LLM requested tool calls."""
        return len(self.llm_tool_calls) > 0

    @property
    def needs_recursion(self) -> bool:
        """Check if this frame should recurse (has tool calls and not final)."""
        return self.has_tool_calls and not self.is_final

    # ===== Serialization (Checkpointing) =====

    def to_checkpoint(self) -> Dict[str, Any]:
        """
        Serialize frame to checkpoint (complete state for persistence).

        This is more comprehensive than to_dict() - it includes everything
        needed to fully restore execution state.

        Returns:
            Dict: JSON-serializable checkpoint
        """
        return {
            # Identity
            "frame_id": self.frame_id,
            "parent_frame_id": self.parent_frame_id,
            "depth": self.depth,
            "phase": self.phase.value,
            "created_at": self.created_at,

            # State
            "messages": self.messages,
            "context_snapshot": self.context_snapshot,
            "context_metadata": self.context_metadata,
            "llm_response": self.llm_response,
            "llm_tool_calls": self.llm_tool_calls,
            "tool_results": self.tool_results,

            # Recursion Control
            "max_iterations": self.max_iterations,
            "tool_call_history": self.tool_call_history,
            "error_count": self.error_count,
            "last_outputs": self.last_outputs,

            # Metadata
            "metadata": self.metadata,

            # Version for future compatibility
            "checkpoint_version": "1.0"
        }

    @staticmethod
    def from_checkpoint(data: Dict[str, Any]) -> ExecutionFrame:
        """
        Deserialize frame from checkpoint.

        Args:
            data: Checkpoint dictionary from to_checkpoint()

        Returns:
            ExecutionFrame: Restored frame
        """
        return ExecutionFrame(
            frame_id=data["frame_id"],
            parent_frame_id=data.get("parent_frame_id"),
            depth=data["depth"],
            phase=ExecutionPhase(data["phase"]),
            created_at=data["created_at"],
            messages=data.get("messages", []),
            context_snapshot=data.get("context_snapshot", {}),
            context_metadata=data.get("context_metadata", {}),
            llm_response=data.get("llm_response"),
            llm_tool_calls=data.get("llm_tool_calls", []),
            tool_results=data.get("tool_results", []),
            max_iterations=data.get("max_iterations", 10),
            tool_call_history=data.get("tool_call_history", []),
            error_count=data.get("error_count", 0),
            last_outputs=data.get("last_outputs", []),
            metadata=data.get("metadata", {})
        )

    # ===== Debug Representation =====

    def __repr__(self) -> str:
        """Human-readable representation."""
        return (
            f"ExecutionFrame("
            f"id={self.frame_id[:8]}..., "
            f"depth={self.depth}/{self.max_iterations}, "
            f"phase={self.phase.value}, "
            f"tools={len(self.llm_tool_calls)}, "
            f"parent={'root' if self.is_root else self.parent_frame_id[:8] + '...'}"
            f")"
        )

    def summary(self) -> str:
        """
        Get a human-readable summary of this frame.

        Returns:
            str: Multi-line summary for debugging
        """
        lines = [
            f"Frame {self.frame_id[:8]}... (depth {self.depth}/{self.max_iterations})",
            f"  Phase: {self.phase.value}",
            f"  Messages: {len(self.messages)}",
            f"  LLM Response: {len(self.llm_response or '')} chars",
            f"  Tool Calls: {len(self.llm_tool_calls)}",
            f"  Tool Results: {len(self.tool_results)}",
            f"  Context: {len(self.context_snapshot)} components",
            f"  Errors: {self.error_count}",
        ]

        if self.parent_frame_id:
            lines.append(f"  Parent: {self.parent_frame_id[:8]}...")

        return "\n".join(lines)
