from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


@dataclass
class Message:
    role: str  # user | assistant | system | tool
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tool_call_id: Optional[str] = None


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    tool_call_id: str
    status: str  # success | error | warning
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamEvent:
    type: str  # text_delta | tool_calls_start | tool_result | agent_finish | error | aborted
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    result: Optional[ToolResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Phase 2: Foundation Types for Claude Code Enhancements (v4.0.0)
# =============================================================================


# -----------------------------------------------------------------------------
# T011: MessageQueueItem - US1 Real-Time Steering
# -----------------------------------------------------------------------------
class MessageQueueItem(BaseModel):
    """Message queue item for h2A async message queue (US1)."""

    id: UUID = Field(default_factory=uuid4, description="Unique message ID")
    role: str = Field(..., description="Message role: user | assistant | system | tool")
    content: str = Field(..., description="Message content")
    priority: int = Field(default=5, ge=0, le=10, description="Priority 0-10 (10=highest)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    cancellable: bool = Field(default=True, description="Can this message be cancelled?")
    correlation_id: Optional[str] = Field(default=None, description="Request correlation ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# -----------------------------------------------------------------------------
# T012: CompressionMetadata - US2 Context Compression
# -----------------------------------------------------------------------------
class CompressionMetadata(BaseModel):
    """Metadata for AU2 8-segment compression (US2)."""

    original_message_count: int = Field(..., ge=1, description="Messages before compression")
    compressed_message_count: int = Field(..., ge=1, description="Messages after compression")
    original_token_count: int = Field(..., ge=1, description="Tokens before compression")
    compressed_token_count: int = Field(..., ge=1, description="Tokens after compression")
    compression_ratio: float = Field(..., ge=0.0, le=1.0, description="Reduction ratio (0.75 = 75%)")
    key_topics: List[str] = Field(default_factory=list, description="Extracted key topics")
    compression_method: str = Field(default="au2_8segment", description="Algorithm used")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Compression time")


# -----------------------------------------------------------------------------
# T013: SubAgentContext - US3 Sub-Agent Isolation
# -----------------------------------------------------------------------------
class SubAgentStatus(str, Enum):
    """Sub-agent execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SubAgentContext(BaseModel):
    """Context for I2A isolated sub-agent (US3)."""

    agent_id: UUID = Field(default_factory=uuid4, description="Sub-agent unique ID")
    parent_agent_id: Optional[UUID] = Field(default=None, description="Parent agent ID")
    agent_type: str = Field(default="general", description="AgentSpec type reference")
    tool_whitelist: Optional[List[str]] = Field(default=None, description="Allowed tools (None = all)")
    max_iterations: int = Field(default=50, ge=1, le=100, description="Max loop iterations")
    timeout_seconds: int = Field(default=300, ge=1, le=600, description="Max execution time")
    status: SubAgentStatus = Field(default=SubAgentStatus.PENDING, description="Current status")
    execution_depth: int = Field(default=0, ge=0, le=3, description="Nesting level")
    parent_correlation_id: Optional[str] = Field(default=None, description="Parent's correlation ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# T014: ToolExecutionStage - US4 Tool Pipeline
# -----------------------------------------------------------------------------
class ExecutionStage(str, Enum):
    """6-stage tool execution pipeline (MH1)."""

    DISCOVER = "discover"
    VALIDATE = "validate"
    AUTHORIZE = "authorize"
    CHECK_CANCEL = "check_cancel"
    EXECUTE = "execute"
    FORMAT = "format"


class StageStatus(str, Enum):
    """Status of pipeline stage."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ToolExecutionStageInfo(BaseModel):
    """Information about single pipeline stage."""

    stage_name: ExecutionStage = Field(..., description="Stage identifier")
    stage_status: StageStatus = Field(..., description="Stage result")
    start_time: Optional[datetime] = Field(default=None, description="Stage start")
    end_time: Optional[datetime] = Field(default=None, description="Stage end")
    duration_ms: Optional[float] = Field(default=None, description="Duration in milliseconds")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# T015: CircuitBreakerState - US5 Error Handling & Resilience
# -----------------------------------------------------------------------------
class CircuitState(str, Enum):
    """Circuit breaker state machine."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerState(BaseModel):
    """Circuit breaker state for service protection (US5)."""

    service_name: str = Field(..., description="Protected service identifier")
    state: CircuitState = Field(default=CircuitState.CLOSED, description="Current state")
    failure_count: int = Field(default=0, ge=0, description="Consecutive failures")
    success_count: int = Field(default=0, ge=0, description="Consecutive successes")
    failure_threshold: int = Field(default=5, ge=1, description="Failures to open circuit")
    success_threshold: int = Field(default=2, ge=1, description="Successes to close circuit")
    timeout_seconds: int = Field(default=60, ge=1, description="Timeout in OPEN state")
    last_failure_time: Optional[datetime] = Field(default=None)
    last_success_time: Optional[datetime] = Field(default=None)


# -----------------------------------------------------------------------------
# T016: LongTermMemory - US6 Three-Tier Memory System
# -----------------------------------------------------------------------------
class LongTermMemory(BaseModel):
    """Long-term memory stored in .loom/CLAUDE.md (US6)."""

    project_path: str = Field(..., description="Root project directory")
    memory_file_path: str = Field(..., description="Path to .loom/CLAUDE.md")
    sections: Dict[str, str] = Field(
        default_factory=dict,
        description="Markdown sections: code_style, architecture_decisions, user_preferences, etc.",
    )
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    checksum: Optional[str] = Field(default=None, description="MD5 checksum for integrity")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# T017: AgentEvent Types - Enhanced Events for Callbacks
# -----------------------------------------------------------------------------
class AgentEventType(str, Enum):
    """Enhanced agent event types."""

    TEXT_DELTA = "text_delta"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    COMPRESSION_START = "compression_start"
    COMPRESSION_COMPLETE = "compression_complete"
    SUBAGENT_SPAWNED = "subagent_spawned"
    SUBAGENT_COMPLETED = "subagent_completed"
    ERROR = "error"
    COMPLETION = "completion"


class BaseAgentEvent(BaseModel):
    """Base class for all agent events."""

    event_type: AgentEventType = Field(..., description="Event type identifier")
    correlation_id: Optional[str] = Field(default=None, description="Request correlation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TextDeltaEvent(BaseAgentEvent):
    """Streaming text delta event."""

    event_type: AgentEventType = Field(default=AgentEventType.TEXT_DELTA)
    content: str = Field(..., description="Text delta content")


class ToolCallEvent(BaseAgentEvent):
    """Tool call initiated event."""

    event_type: AgentEventType = Field(default=AgentEventType.TOOL_CALL)
    tool_call_id: str = Field(..., description="Tool call ID")
    tool_name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(..., description="Tool arguments")


class ToolResultEvent(BaseAgentEvent):
    """Tool execution result event."""

    event_type: AgentEventType = Field(default=AgentEventType.TOOL_RESULT)
    tool_call_id: str = Field(..., description="Tool call ID")
    status: str = Field(..., description="success | error | warning")
    content: str = Field(..., description="Result content")
    stages: List[ToolExecutionStageInfo] = Field(default_factory=list, description="Pipeline stages")


class CompressionEvent(BaseAgentEvent):
    """Context compression event."""

    event_type: AgentEventType = Field(default=AgentEventType.COMPRESSION_COMPLETE)
    compression_metadata: CompressionMetadata = Field(..., description="Compression details")


class SubAgentSpawnedEvent(BaseAgentEvent):
    """Sub-agent spawned event."""

    event_type: AgentEventType = Field(default=AgentEventType.SUBAGENT_SPAWNED)
    subagent_context: SubAgentContext = Field(..., description="Sub-agent details")


class ErrorEvent(BaseAgentEvent):
    """Error event."""

    event_type: AgentEventType = Field(default=AgentEventType.ERROR)
    error_message: str = Field(..., description="Error description")
    error_category: Optional[str] = Field(default=None, description="ErrorCategory enum value")
    recoverable: bool = Field(default=False, description="Is error recoverable?")


class CompletionEvent(BaseAgentEvent):
    """Agent completion event."""

    event_type: AgentEventType = Field(default=AgentEventType.COMPLETION)
    final_content: str = Field(..., description="Final response")
    model_used: Optional[str] = Field(default=None, description="Model identifier (if fallback occurred)")

