"""Structured error hierarchy — mirrors Amoba's LoomError tree."""

from __future__ import annotations


class LoomError(Exception):
    def __init__(self, code: str, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.cause = cause

    @classmethod
    def wrap(cls, err: Exception) -> LoomError:
        if isinstance(err, LoomError):
            return err
        return LoomError("UNKNOWN", str(err), err)


class LLMError(LoomError):
    def __init__(
        self,
        code: str,
        provider: str,
        message: str,
        status_code: int | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(code, message, cause)
        self.provider = provider
        self.status_code = status_code


class LLMRateLimitError(LLMError):
    def __init__(self, provider: str, retry_after_ms: int | None = None) -> None:
        super().__init__("LLM_RATE_LIMIT", provider, f"Rate limited by {provider}", 429)
        self.retry_after_ms = retry_after_ms


class LLMAuthError(LLMError):
    def __init__(self, provider: str) -> None:
        super().__init__("LLM_AUTH_ERROR", provider, f"Auth failed for {provider}", 401)


class LLMStreamInterruptedError(LLMError):
    def __init__(
        self, provider: str, partial_content: str = "", cause: Exception | None = None
    ) -> None:
        super().__init__(
            "LLM_STREAM_INTERRUPTED", provider, f"Stream interrupted from {provider}", cause=cause
        )
        self.partial_content = partial_content


class ToolError(LoomError):
    def __init__(
        self, code: str, tool_name: str, message: str, cause: Exception | None = None
    ) -> None:
        super().__init__(code, message, cause)
        self.tool_name = tool_name


class ToolTimeoutError(ToolError):
    def __init__(self, tool_name: str, timeout_ms: int) -> None:
        super().__init__(
            "TOOL_TIMEOUT", tool_name, f'Tool "{tool_name}" timed out after {timeout_ms}ms'
        )
        self.timeout_ms = timeout_ms


class ToolResultTooLargeError(ToolError):
    def __init__(self, tool_name: str, size_bytes: int, limit_bytes: int) -> None:
        super().__init__(
            "TOOL_RESULT_TOO_LARGE",
            tool_name,
            f'Tool "{tool_name}" result {size_bytes}B exceeds limit {limit_bytes}B',
        )
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes


class AuctionNoWinnerError(LoomError):
    def __init__(self, task_id: str) -> None:
        super().__init__("AUCTION_NO_WINNER", f"No agent won auction for task {task_id}")
        self.task_id = task_id


class MitosisError(LoomError):
    def __init__(self, parent_id: str, message: str, cause: Exception | None = None) -> None:
        super().__init__("MITOSIS_FAILED", message, cause)
        self.parent_id = parent_id


class ApoptosisRejectedError(LoomError):
    def __init__(self, node_id: str, reason: str) -> None:
        super().__init__("APOPTOSIS_REJECTED", f"Cannot recycle node {node_id}: {reason}")
        self.node_id = node_id


class AgentAbortError(LoomError):
    def __init__(self) -> None:
        super().__init__("AGENT_ABORT", "Agent execution was aborted")


class AgentMaxStepsError(LoomError):
    def __init__(self, steps: int, partial_content: str = "") -> None:
        super().__init__("AGENT_MAX_STEPS", f"Agent reached max steps ({steps})")
        self.steps = steps
        self.partial_content = partial_content
