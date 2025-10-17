"""US5: Error Classification and Retry Logic

Classifies errors into retryable/non-retryable categories and provides
actionable recovery guidance.
"""

from __future__ import annotations

import asyncio
from typing import Optional, Callable, Any, TypeVar
from loom.core.errors import ErrorCategory, LoomException

T = TypeVar('T')


class ErrorClassifier:
    """Classifies errors and determines retry strategy."""

    @staticmethod
    def classify(error: Exception) -> ErrorCategory:
        """Classify an error into a category.

        Args:
            error: The exception to classify

        Returns:
            ErrorCategory enum value
        """
        # Check if it's already a LoomException with category
        if isinstance(error, LoomException):
            return error.category

        # Classify by exception type
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # Network errors (retryable)
        if any(kw in error_type.lower() for kw in ['timeout', 'connect', 'network']):
            return ErrorCategory.TIMEOUT_ERROR if 'timeout' in error_type.lower() else ErrorCategory.NETWORK_ERROR

        # Rate limiting (retryable with backoff)
        if '429' in error_msg or 'rate limit' in error_msg:
            return ErrorCategory.RATE_LIMIT_ERROR

        # Service errors (5xx - retryable)
        if any(code in error_msg for code in ['500', '502', '503', '504']):
            return ErrorCategory.SERVICE_ERROR

        # Authentication errors (non-retryable)
        if any(code in error_msg for code in ['401', '403']) or 'auth' in error_msg:
            return ErrorCategory.AUTHENTICATION_ERROR

        # Not found errors (non-retryable)
        if '404' in error_msg or 'not found' in error_msg:
            return ErrorCategory.NOT_FOUND_ERROR

        # Validation errors (non-retryable)
        if 'validation' in error_type.lower():
            return ErrorCategory.VALIDATION_ERROR

        # Default: unknown (non-retryable)
        return ErrorCategory.UNKNOWN_ERROR

    @staticmethod
    def is_retryable(category: ErrorCategory) -> bool:
        """Determine if an error category is retryable.

        Args:
            category: The error category

        Returns:
            True if retryable, False otherwise
        """
        retryable_categories = {
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.TIMEOUT_ERROR,
            ErrorCategory.RATE_LIMIT_ERROR,
            ErrorCategory.SERVICE_ERROR,
        }
        return category in retryable_categories

    @staticmethod
    def get_recovery_guidance(error: Exception, category: ErrorCategory) -> str:
        """Get actionable recovery guidance for an error.

        Args:
            error: The exception
            category: The error category

        Returns:
            Human-readable recovery guidance
        """
        guidance_map = {
            ErrorCategory.NETWORK_ERROR: "Check network connectivity and retry. If problem persists, check service status.",
            ErrorCategory.TIMEOUT_ERROR: "Operation timed out. Try increasing timeout or simplifying the request.",
            ErrorCategory.RATE_LIMIT_ERROR: "Rate limit exceeded. Wait before retrying. Consider implementing backoff.",
            ErrorCategory.SERVICE_ERROR: "Service temporarily unavailable. Retry after a short delay.",
            ErrorCategory.VALIDATION_ERROR: "Invalid input parameters. Review and correct the request.",
            ErrorCategory.PERMISSION_ERROR: "Permission denied. Check access rights and credentials.",
            ErrorCategory.AUTHENTICATION_ERROR: "Authentication failed. Verify credentials and API keys.",
            ErrorCategory.NOT_FOUND_ERROR: "Resource not found. Verify the resource exists and path is correct.",
            ErrorCategory.UNKNOWN_ERROR: f"Unexpected error: {type(error).__name__}. Review error details.",
        }
        return guidance_map.get(category, "Unknown error. Review error details.")


class RetryPolicy:
    """Retry policy with exponential backoff.

    US5: Automatic retry with exponential backoff (1s, 2s, 4s, max 3 attempts)
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        """Initialize retry policy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff (2.0 = double each time)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt.

        Args:
            attempt: The retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)

    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function with retry logic.

        Args:
            func: The async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            The result of the function

        Raises:
            The last exception if all retries fail
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                last_exception = e
                category = ErrorClassifier.classify(e)

                # Don't retry if non-retryable
                if not ErrorClassifier.is_retryable(category):
                    raise

                # If this was the last attempt, raise
                if attempt >= self.max_retries:
                    raise

                # Calculate delay and wait
                delay = self.get_delay(attempt)
                await asyncio.sleep(delay)

        # Should not reach here, but if we do, raise the last exception
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry logic failed unexpectedly")
