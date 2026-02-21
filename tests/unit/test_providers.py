"""Unit tests for providers module (base, retry, circuit breaker)."""

import pytest
from loom.providers.base import BaseLLMProvider, RetryConfig, CircuitBreakerConfig
from loom.types import CompletionParams, CompletionResult, TokenUsage, UserMessage
from loom.errors import LLMError


class _FakeProvider(BaseLLMProvider):
    def __init__(self, responses=None, fail_n=0, **kw):
        super().__init__(**kw)
        self._responses = responses or ["ok"]
        self._fail_n = fail_n
        self._calls = 0

    async def _do_complete(self, params):
        self._calls += 1
        if self._calls <= self._fail_n:
            raise LLMError("FAIL", "test", "boom")
        text = self._responses[min(self._calls - self._fail_n - 1, len(self._responses) - 1)]
        return CompletionResult(content=text, usage=TokenUsage(total_tokens=10))


class TestRetryConfig:
    def test_defaults(self):
        r = RetryConfig()
        assert r.max_retries == 3
        assert r.base_delay == 1.0


class TestCircuitBreakerConfig:
    def test_defaults(self):
        c = CircuitBreakerConfig()
        assert c.failure_threshold == 5


class TestBaseLLMProvider:
    async def test_complete_success(self):
        p = _FakeProvider(responses=["hello"])
        params = CompletionParams(messages=[UserMessage(content="hi")])
        r = await p.complete(params)
        assert r.content == "hello"

    async def test_retry_then_succeed(self):
        p = _FakeProvider(fail_n=2, retry=RetryConfig(max_retries=3, base_delay=0.01))
        params = CompletionParams(messages=[UserMessage(content="hi")])
        r = await p.complete(params)
        assert r.content == "ok"
        assert p._calls == 3

    async def test_retry_exhausted(self):
        p = _FakeProvider(fail_n=10, retry=RetryConfig(max_retries=1, base_delay=0.01))
        params = CompletionParams(messages=[UserMessage(content="hi")])
        with pytest.raises(LLMError):
            await p.complete(params)

    async def test_circuit_breaker_opens(self):
        p = _FakeProvider(
            fail_n=100,
            retry=RetryConfig(max_retries=0, base_delay=0.01),
            circuit_breaker=CircuitBreakerConfig(failure_threshold=3, reset_time=60),
        )
        params = CompletionParams(messages=[UserMessage(content="hi")])
        for _ in range(3):
            with pytest.raises(LLMError):
                await p.complete(params)
        with pytest.raises(LLMError, match="Circuit breaker open"):
            await p.complete(params)
