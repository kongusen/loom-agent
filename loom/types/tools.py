"""Tool types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ToolSchema(Protocol):
    def parse(self, raw: Any) -> Any: ...
    def to_json_schema(self) -> dict: ...


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: ToolSchema
    execute: Any  # (input, ctx) -> Awaitable[Any]


@dataclass
class ToolExecutionConfig:
    timeout_ms: int = 30000
    max_result_bytes: int = 100_000
    max_concurrency: int = 5


@dataclass
class ToolResult:
    tool_call_id: str
    tool_name: str
    success: bool
    result: Any = None
    error: Exception | None = None
    duration_ms: int = 0
    token_cost: int = 0


@dataclass
class ToolContext:
    agent_id: str
    session_id: str | None = None
    tenant_id: str | None = None
    signal: Any | None = None  # asyncio.Event for cancellation
    metadata: dict[str, Any] = field(default_factory=dict)
