"""Event types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float | None = None


@dataclass
class TextDeltaEvent:
    text: str
    type: str = "text_delta"


@dataclass
class ReasoningDeltaEvent:
    text: str
    type: str = "reasoning_delta"


@dataclass
class ToolCallStartEvent:
    tool_call_id: str
    name: str
    input: object = None
    type: str = "tool_call_start"


@dataclass
class ToolCallDeltaEvent:
    tool_call_id: str
    partial_args: str = ""
    type: str = "tool_call_delta"


@dataclass
class ToolCallEndEvent:
    tool_call_id: str
    result: str
    duration_ms: int = 0
    token_cost: int = 0
    type: str = "tool_call_end"


@dataclass
class StepStartEvent:
    step: int
    total_steps: int = 0
    type: str = "step_start"


@dataclass
class StepEndEvent:
    step: int
    reason: str = "complete"  # "tool_use" | "complete" | "max_steps" | "abort"
    type: str = "step_end"


# Keep backward compat alias
StepEvent = StepStartEvent


@dataclass
class ErrorEvent:
    error: str
    recoverable: bool = False
    type: str = "error"


@dataclass
class DoneEvent:
    content: str
    tokens_used: int = 0
    steps: int = 0
    duration_ms: int = 0
    usage: TokenUsage = field(default_factory=TokenUsage)
    type: str = "done"


AgentEvent = (
    TextDeltaEvent
    | ReasoningDeltaEvent
    | ToolCallStartEvent
    | ToolCallDeltaEvent
    | ToolCallEndEvent
    | StepStartEvent
    | StepEndEvent
    | ErrorEvent
    | DoneEvent
)
