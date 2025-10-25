"""
Agent Event System for Loom 2.0

This module defines the unified event model for streaming agent execution.
Inspired by Claude Code's event-driven architecture.

Example:
    ```python
    agent = Agent(llm=llm, tools=tools)

    async for event in agent.execute("Search for TODO comments"):
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)
        elif event.type == AgentEventType.TOOL_PROGRESS:
            print(f"\\nTool: {event.metadata['tool_name']}")
        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\\n✓ {event.content}")
    ```
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
import time
import uuid


class AgentEventType(Enum):
    """
    Agent event types for different execution phases.

    Event Categories:
    - Phase Events: Lifecycle events for execution phases
    - Context Events: Context assembly and management
    - RAG Events: Retrieval-augmented generation events
    - LLM Events: Language model interaction events
    - Tool Events: Tool execution and progress
    - Agent Events: High-level agent state changes
    - Error Events: Error handling and recovery
    """

    # ===== Phase Events =====
    PHASE_START = "phase_start"
    """A new execution phase has started"""

    PHASE_END = "phase_end"
    """An execution phase has completed"""

    # ===== Context Events =====
    CONTEXT_ASSEMBLY_START = "context_assembly_start"
    """Starting to assemble system context"""

    CONTEXT_ASSEMBLY_COMPLETE = "context_assembly_complete"
    """System context assembly completed"""

    COMPRESSION_APPLIED = "compression_applied"
    """Conversation history was compressed"""

    # ===== RAG Events =====
    RETRIEVAL_START = "retrieval_start"
    """Starting document retrieval"""

    RETRIEVAL_PROGRESS = "retrieval_progress"
    """Progress update during retrieval (documents found)"""

    RETRIEVAL_COMPLETE = "retrieval_complete"
    """Document retrieval completed"""

    # ===== LLM Events =====
    LLM_START = "llm_start"
    """LLM call initiated"""

    LLM_DELTA = "llm_delta"
    """Streaming text chunk from LLM"""

    LLM_COMPLETE = "llm_complete"
    """LLM call completed"""

    LLM_TOOL_CALLS = "llm_tool_calls"
    """LLM requested tool calls"""

    # ===== Tool Events =====
    TOOL_CALLS_START = "tool_calls_start"
    """Starting to execute tool calls"""

    TOOL_EXECUTION_START = "tool_execution_start"
    """Individual tool execution started"""

    TOOL_PROGRESS = "tool_progress"
    """Progress update from tool execution"""

    TOOL_RESULT = "tool_result"
    """Tool execution completed with result"""

    TOOL_ERROR = "tool_error"
    """Tool execution failed"""

    TOOL_CALLS_COMPLETE = "tool_calls_complete"
    """All tool calls completed (batch execution finished)"""

    # ===== Agent Events =====
    ITERATION_START = "iteration_start"
    """New agent iteration started (for recursive loops)"""

    ITERATION_END = "iteration_end"
    """Agent iteration completed"""

    RECURSION = "recursion"
    """Recursive call initiated (tt mode)"""

    AGENT_FINISH = "agent_finish"
    """Agent execution finished successfully"""

    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    """Maximum iteration limit reached"""

    EXECUTION_CANCELLED = "execution_cancelled"
    """Execution was cancelled via cancel_token"""

    # ===== Error Events =====
    ERROR = "error"
    """Error occurred during execution"""

    RECOVERY_ATTEMPT = "recovery_attempt"
    """Attempting to recover from error"""

    RECOVERY_SUCCESS = "recovery_success"
    """Error recovery succeeded"""

    RECOVERY_FAILED = "recovery_failed"
    """Error recovery failed"""


@dataclass
class ToolCall:
    """Represents a tool invocation request from the LLM"""

    id: str
    """Unique identifier for this tool call"""

    name: str
    """Name of the tool to execute"""

    arguments: Dict[str, Any]
    """Arguments to pass to the tool"""

    def __post_init__(self):
        if not self.id:
            self.id = f"call_{uuid.uuid4().hex[:8]}"


@dataclass
class ToolResult:
    """Represents the result of a tool execution"""

    tool_call_id: str
    """ID of the tool call this result corresponds to"""

    tool_name: str
    """Name of the tool that was executed"""

    content: str
    """Result content (or error message)"""

    is_error: bool = False
    """Whether this result represents an error"""

    execution_time_ms: Optional[float] = None
    """Time taken to execute the tool in milliseconds"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the execution"""


@dataclass
class AgentEvent:
    """
    Unified event model for agent execution streaming.

    All components in Loom 2.0 produce AgentEvent instances to communicate
    their state and progress. This enables:
    - Real-time progress updates to users
    - Fine-grained control over execution flow
    - Debugging and observability
    - Flexible consumption patterns

    Attributes:
        type: The type of event (see AgentEventType)
        timestamp: Unix timestamp when event was created
        phase: Optional execution phase name (e.g., "context", "retrieval", "llm")
        content: Optional text content (for LLM deltas, final responses)
        tool_call: Optional tool call request
        tool_result: Optional tool execution result
        error: Optional exception that occurred
        metadata: Additional event-specific data
        iteration: Current iteration number (for recursive loops)
        turn_id: Unique ID for this conversation turn
    """

    type: AgentEventType
    """The type of this event"""

    timestamp: float = field(default_factory=time.time)
    """Unix timestamp when this event was created"""

    # ===== Optional Fields (based on event type) =====

    phase: Optional[str] = None
    """Execution phase name (e.g., 'context_assembly', 'tool_execution')"""

    content: Optional[str] = None
    """Text content (for LLM_DELTA, AGENT_FINISH, etc.)"""

    tool_call: Optional[ToolCall] = None
    """Tool call request (for LLM_TOOL_CALLS, TOOL_EXECUTION_START)"""

    tool_result: Optional[ToolResult] = None
    """Tool execution result (for TOOL_RESULT, TOOL_ERROR)"""

    error: Optional[Exception] = None
    """Exception that occurred (for ERROR events)"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional event-specific data"""

    # ===== Tracking Fields =====

    iteration: Optional[int] = None
    """Current iteration number (for recursive agent loops)"""

    turn_id: Optional[str] = None
    """Unique identifier for this conversation turn"""

    def __post_init__(self):
        """Generate turn_id if not provided"""
        if self.turn_id is None:
            self.turn_id = f"turn_{uuid.uuid4().hex[:12]}"

    # ===== Convenience Constructors =====

    @classmethod
    def phase_start(cls, phase: str, **metadata) -> "AgentEvent":
        """Create a PHASE_START event"""
        return cls(
            type=AgentEventType.PHASE_START,
            phase=phase,
            metadata=metadata
        )

    @classmethod
    def phase_end(cls, phase: str, **metadata) -> "AgentEvent":
        """Create a PHASE_END event"""
        return cls(
            type=AgentEventType.PHASE_END,
            phase=phase,
            metadata=metadata
        )

    @classmethod
    def llm_delta(cls, content: str, **metadata) -> "AgentEvent":
        """Create an LLM_DELTA event for streaming text"""
        return cls(
            type=AgentEventType.LLM_DELTA,
            content=content,
            metadata=metadata
        )

    @classmethod
    def tool_progress(
        cls,
        tool_name: str,
        status: str,
        **metadata
    ) -> "AgentEvent":
        """Create a TOOL_PROGRESS event"""
        return cls(
            type=AgentEventType.TOOL_PROGRESS,
            metadata={"tool_name": tool_name, "status": status, **metadata}
        )

    @classmethod
    def tool_result(
        cls,
        tool_result: ToolResult,
        **metadata
    ) -> "AgentEvent":
        """Create a TOOL_RESULT event"""
        return cls(
            type=AgentEventType.TOOL_RESULT,
            tool_result=tool_result,
            metadata=metadata
        )

    @classmethod
    def agent_finish(cls, content: str, **metadata) -> "AgentEvent":
        """Create an AGENT_FINISH event"""
        return cls(
            type=AgentEventType.AGENT_FINISH,
            content=content,
            metadata=metadata
        )

    @classmethod
    def error(cls, error: Exception, **metadata) -> "AgentEvent":
        """Create an ERROR event"""
        return cls(
            type=AgentEventType.ERROR,
            error=error,
            metadata=metadata
        )

    # ===== Utility Methods =====

    def is_terminal(self) -> bool:
        """Check if this event signals execution completion"""
        return self.type in {
            AgentEventType.AGENT_FINISH,
            AgentEventType.MAX_ITERATIONS_REACHED,
            AgentEventType.ERROR
        }

    def is_llm_content(self) -> bool:
        """Check if this event contains LLM-generated content"""
        return self.type in {
            AgentEventType.LLM_DELTA,
            AgentEventType.LLM_COMPLETE,
            AgentEventType.AGENT_FINISH
        }

    def is_tool_event(self) -> bool:
        """Check if this is a tool-related event"""
        return self.type.value.startswith("tool_")

    def __repr__(self) -> str:
        """Human-readable representation"""
        parts = [f"AgentEvent({self.type.value}"]

        if self.phase:
            parts.append(f"phase={self.phase}")

        if self.content:
            preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
            parts.append(f"content='{preview}'")

        if self.tool_call:
            parts.append(f"tool={self.tool_call.name}")

        # Access instance variable directly to avoid class method with same name
        tool_result_instance = self.__dict__.get('tool_result')
        if tool_result_instance and isinstance(tool_result_instance, ToolResult):
            parts.append(f"tool={tool_result_instance.tool_name}")

        if self.error:
            parts.append(f"error={type(self.error).__name__}")

        if self.iteration is not None:
            parts.append(f"iter={self.iteration}")

        return ", ".join(parts) + ")"


# ===== Event Consumer Helpers =====

class EventCollector:
    """
    Helper class to collect and filter events during agent execution.

    Example:
        ```python
        collector = EventCollector()

        async for event in agent.execute(prompt):
            collector.add(event)

        # Get all LLM content
        llm_text = collector.get_llm_content()

        # Get all tool results
        tool_results = collector.get_tool_results()
        ```
    """

    def __init__(self):
        self.events: List[AgentEvent] = []

    def add(self, event: AgentEvent):
        """Add an event to the collection"""
        self.events.append(event)

    def filter(self, event_type: AgentEventType) -> List[AgentEvent]:
        """Get all events of a specific type"""
        return [e for e in self.events if e.type == event_type]

    def get_llm_content(self) -> str:
        """Reconstruct full LLM output from LLM_DELTA events"""
        deltas = self.filter(AgentEventType.LLM_DELTA)
        return "".join(e.content or "" for e in deltas)

    def get_tool_results(self) -> List[ToolResult]:
        """Get all tool results"""
        result_events = self.filter(AgentEventType.TOOL_RESULT)
        return [e.tool_result for e in result_events if e.tool_result]

    def get_errors(self) -> List[Exception]:
        """Get all errors that occurred"""
        error_events = self.filter(AgentEventType.ERROR)
        return [e.error for e in error_events if e.error]

    def get_final_response(self) -> Optional[str]:
        """Get the final agent response"""
        finish_events = self.filter(AgentEventType.AGENT_FINISH)
        if finish_events:
            return finish_events[-1].content
        return None
