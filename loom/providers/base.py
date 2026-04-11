"""LLM Provider base interface"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from ..types import ToolCall
from ..utils.errors import ProviderError, ProviderUnavailableError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class CompletionParams:
    """LLM completion parameters"""
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    temperature: float = 1.0
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_choice: str | None = None


@dataclass
class TokenUsage:
    """Token usage statistics"""
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class CompletionResponse:
    """Structured completion payload."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage | None = None
    raw: Any | None = None


@dataclass
class RetryConfig:
    """Retry + circuit-breaker config."""
    max_retries: int = 3
    base_delay: float = 1.0       # seconds, exponential backoff
    circuit_open_after: int = 5   # consecutive failures before open
    circuit_reset_after: float = 60.0  # seconds before half-open


class CircuitBreaker:
    """Simple circuit breaker: closed → open → half-open."""

    def __init__(self, config: RetryConfig):
        self._cfg = config
        self._failures = 0
        self._opened_at: float | None = None

    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        import time
        if time.monotonic() - self._opened_at >= self._cfg.circuit_reset_after:
            self._opened_at = None  # half-open: allow one attempt
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._cfg.circuit_open_after:
            import time
            self._opened_at = time.monotonic()
            logger.warning("Circuit breaker opened after %d failures", self._failures)


class LLMProvider(ABC):
    """Abstract LLM Provider with built-in retry + circuit breaker."""

    def __init__(self, retry_config: RetryConfig | None = None):
        self._retry = retry_config or RetryConfig()
        self._circuit = CircuitBreaker(self._retry)

    @abstractmethod
    async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
        """Provider-specific completion (no retry logic)."""

    async def _complete_response(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> CompletionResponse:
        """Provider-specific structured completion (defaults to text-only)."""
        return CompletionResponse(content=await self._complete(messages, params))

    @abstractmethod
    def stream(self, messages: list, params: CompletionParams | None = None) -> AsyncIterator[str]:
        """Streaming completion (async generator)."""

    async def complete(self, messages: list, params: CompletionParams | None = None) -> str:
        """Completion with retry + circuit breaker."""
        if self._circuit.is_open():
            raise ProviderUnavailableError("Circuit breaker open: provider unavailable")

        last_exc: Exception | None = None
        for attempt in range(self._retry.max_retries):
            try:
                result = await self._complete(messages, params)
                self._circuit.record_success()
                return result
            except Exception as exc:
                last_exc = exc
                self._circuit.record_failure()
                if attempt < self._retry.max_retries - 1:
                    delay = self._retry.base_delay * (2 ** attempt)
                    logger.warning("Provider error (attempt %d/%d): %s — retrying in %.1fs",
                                   attempt + 1, self._retry.max_retries, exc, delay)
                    await asyncio.sleep(delay)

        if last_exc is None:
            raise ProviderUnavailableError("Provider completion failed with no exception details")
        raise self._normalize_provider_exception(last_exc)

    async def complete_response(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> CompletionResponse:
        """Structured completion with retry + circuit breaker."""
        if self._circuit.is_open():
            raise ProviderUnavailableError("Circuit breaker open: provider unavailable")

        last_exc: Exception | None = None
        for attempt in range(self._retry.max_retries):
            try:
                result = await self._complete_response(messages, params)
                self._circuit.record_success()
                return result
            except Exception as exc:
                last_exc = exc
                self._circuit.record_failure()
                if attempt < self._retry.max_retries - 1:
                    delay = self._retry.base_delay * (2 ** attempt)
                    logger.warning("Provider error (attempt %d/%d): %s — retrying in %.1fs",
                                   attempt + 1, self._retry.max_retries, exc, delay)
                    await asyncio.sleep(delay)

        if last_exc is None:
            raise ProviderUnavailableError("Provider completion failed with no exception details")
        raise self._normalize_provider_exception(last_exc)

    def _normalize_provider_exception(self, exc: Exception) -> ProviderError:
        if isinstance(exc, ProviderError):
            return exc

        message = str(exc)
        lowered = message.lower()
        if "rate limit" in lowered or "429" in lowered:
            return RateLimitError(message)
        return ProviderUnavailableError(message)
