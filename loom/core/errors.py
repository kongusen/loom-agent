from enum import Enum


class ErrorCategory(Enum):
    """Error classification for retry logic (T018 - US5)."""

    NETWORK_ERROR = "network_error"  # httpx.TimeoutException, httpx.ConnectError - retryable
    TIMEOUT_ERROR = "timeout_error"  # asyncio.TimeoutError - retryable
    RATE_LIMIT_ERROR = "rate_limit_error"  # 429 responses - retryable with backoff
    VALIDATION_ERROR = "validation_error"  # Pydantic ValidationError - non-retryable
    PERMISSION_ERROR = "permission_error"  # PermissionDeniedError - non-retryable
    AUTHENTICATION_ERROR = "authentication_error"  # 401/403 - non-retryable
    SERVICE_ERROR = "service_error"  # 5xx errors - retryable
    NOT_FOUND_ERROR = "not_found_error"  # 404, ToolNotFoundError - non-retryable
    UNKNOWN_ERROR = "unknown_error"  # Catch-all - non-retryable by default


class LoomException(Exception):
    """Base exception for Loom framework."""

    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR) -> None:
        super().__init__(message)
        self.category = category


class ToolNotFoundError(LoomException):
    """Tool not found in registry."""

    def __init__(self, message: str) -> None:
        super().__init__(message, category=ErrorCategory.NOT_FOUND_ERROR)


class ToolValidationError(LoomException):
    """Tool argument validation failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, category=ErrorCategory.VALIDATION_ERROR)


class PermissionDeniedError(LoomException):
    """Permission check failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, category=ErrorCategory.PERMISSION_ERROR)


class ToolExecutionTimeout(LoomException):
    """Tool execution exceeded timeout."""

    def __init__(self, message: str) -> None:
        super().__init__(message, category=ErrorCategory.TIMEOUT_ERROR)


class ExecutionAbortedError(LoomException):
    """Execution aborted by user."""

    def __init__(self, message: str) -> None:
        super().__init__(message, category=ErrorCategory.UNKNOWN_ERROR)


class RecursionLimitError(LoomException):
    """Sub-agent recursion depth exceeded (US3)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, category=ErrorCategory.VALIDATION_ERROR)

