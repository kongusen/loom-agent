"""Base LLM provider with retry and circuit breaker."""

from __future__ import annotations

import asyncio
import math
import random
import time
from dataclasses import dataclass
from typing import AsyncGenerator

from ..types import CompletionResult, CompletionParams, StreamChunk


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    reset_time: float = 60.0


class BaseLLMProvider:
    """Abstract base with retry + circuit breaker. Subclass and implement _do_complete/_do_stream."""

    def __init__(
        self,
        retry: RetryConfig | None = None,
        circuit_breaker: CircuitBreakerConfig | None = None,
    ) -> None:
        self._retry = retry or RetryConfig()
        self._cb = circuit_breaker or CircuitBreakerConfig()
        self._failures = 0
        self._last_failure = 0.0

    async def complete(self, params: CompletionParams) -> CompletionResult:
        self._check_circuit()
        return await self._with_retry(lambda: self._do_complete(params))

    async def stream(self, params: CompletionParams) -> AsyncGenerator[StreamChunk, None]:
        self._check_circuit()
        async for chunk in self._do_stream(params):
            yield chunk

    # -- Override these --

    async def _do_complete(self, params: CompletionParams) -> CompletionResult:
        raise NotImplementedError

    async def _do_stream(self, params: CompletionParams) -> AsyncGenerator[StreamChunk, None]:
        raise NotImplementedError
        yield  # pragma: no cover

    # -- Internals --

    def _check_circuit(self) -> None:
        if self._failures >= self._cb.failure_threshold:
            if time.time() - self._last_failure < self._cb.reset_time:
                from ..errors import LLMError
                raise LLMError("LLM_CIRCUIT_OPEN", "base", "Circuit breaker open")
            self._failures = 0

    async def _with_retry(self, fn):
        last_err = None
        for i in range(self._retry.max_retries + 1):
            try:
                result = await fn()
                self._failures = 0
                return result
            except Exception as e:
                last_err = e
                self._failures += 1
                self._last_failure = time.time()
                if i < self._retry.max_retries:
                    delay = min(
                        self._retry.base_delay * (2 ** i) + random.random() * 0.1,
                        self._retry.max_delay,
                    )
                    await asyncio.sleep(delay)
        raise last_err
