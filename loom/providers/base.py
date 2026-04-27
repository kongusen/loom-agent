"""LLM Provider base interface"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from ..types.stream import StreamEvent

from ..types import ToolCall
from ..utils.errors import ProviderError, ProviderUnavailableError, RateLimitError

logger = logging.getLogger(__name__)
T = TypeVar("T")


def parse_tool_arguments(value: Any) -> dict[str, Any]:
    """Normalize provider tool-call arguments into a dict."""
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def normalize_tool_call(
    *,
    call_id: Any,
    name: Any,
    arguments: Any,
) -> ToolCall | None:
    """Return a runtime ToolCall, or None when provider data is not executable."""
    normalized_name = str(name or "").strip()
    if not normalized_name:
        return None
    return ToolCall(
        id=str(call_id or ""),
        name=normalized_name,
        arguments=arguments if isinstance(arguments, dict) else {},
    )


@dataclass(frozen=True)
class ProviderToolParameter:
    """Provider-facing tool parameter descriptor."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any | None = None

    def to_json_schema_property(self) -> dict[str, Any]:
        schema: dict[str, Any] = {"type": self.type}
        if self.description:
            schema["description"] = self.description
        if self.default is not None:
            schema["default"] = self.default
        return schema


@dataclass(frozen=True)
class ProviderToolSpec:
    """Stable provider-facing function/tool descriptor."""

    name: str
    description: str = ""
    parameters: tuple[ProviderToolParameter, ...] = ()

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProviderToolSpec":
        parameter_schema = value.get("parameters", {})
        properties = parameter_schema.get("properties", {})
        required = set(parameter_schema.get("required", []))
        parameters = tuple(
            ProviderToolParameter(
                name=name,
                type=str(schema.get("type", "string")) if isinstance(schema, dict) else "string",
                description=str(schema.get("description", "")) if isinstance(schema, dict) else "",
                required=name in required,
                default=schema.get("default") if isinstance(schema, dict) else None,
            )
            for name, schema in properties.items()
        )
        return cls(
            name=str(value["name"]),
            description=str(value.get("description", "")),
            parameters=parameters,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the legacy provider function shape."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    parameter.name: parameter.to_json_schema_property()
                    for parameter in self.parameters
                },
                "required": [
                    parameter.name
                    for parameter in self.parameters
                    if parameter.required
                ],
            },
        }


@dataclass
class CompletionParams:
    """LLM completion parameters"""
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 4096
    temperature: float = 1.0
    tools: list[dict[str, Any] | ProviderToolSpec] = field(default_factory=list)
    tool_choice: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def tool_specs(self) -> list[ProviderToolSpec]:
        """Return tools as typed provider descriptors."""
        specs: list[ProviderToolSpec] = []
        for tool in self.tools:
            if isinstance(tool, ProviderToolSpec):
                specs.append(tool)
            else:
                specs.append(ProviderToolSpec.from_dict(tool))
        return specs

    def tool_dicts(self) -> list[dict[str, Any]]:
        """Return tools in the legacy provider function shape."""
        return [tool.to_dict() for tool in self.tool_specs()]


@dataclass
class CompletionRequest:
    """Stable provider request contract used by the runtime engine."""

    messages: list[dict[str, Any]]
    params: CompletionParams = field(default_factory=CompletionParams)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        messages: list[dict[str, Any]],
        params: CompletionParams | None = None,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> "CompletionRequest":
        return cls(
            messages=list(messages),
            params=params or CompletionParams(),
            metadata=dict(metadata or {}),
        )

    @property
    def tools(self) -> list[ProviderToolSpec]:
        """Typed tool descriptors attached to this request."""
        return self.params.tool_specs()


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


class LLMProvider:
    """Abstract LLM Provider with built-in retry + circuit breaker."""

    def __init__(self, retry_config: RetryConfig | None = None):
        self._retry = retry_config or RetryConfig()
        self._circuit = CircuitBreaker(self._retry)

    async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
        """Provider-specific completion (no retry logic)."""
        _ = messages, params
        raise NotImplementedError("provider must implement _complete() or _complete_request()")

    async def _complete_response(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> CompletionResponse:
        """Provider-specific structured completion (defaults to text-only)."""
        return CompletionResponse(content=await self._complete(messages, params))

    def stream(self, messages: list, params: CompletionParams | None = None) -> AsyncIterator[str]:
        """Streaming completion (async generator)."""
        request = CompletionRequest.create(messages, params)

        async def _gen() -> AsyncIterator[str]:
            async for event in self.stream_request_events(request):
                if getattr(event, "type", "") == "text_delta":
                    yield str(getattr(event, "delta", ""))

        return _gen()

    async def complete_streaming(
        self,
        messages: list,
        params: CompletionParams | None = None,
        on_token: "Any | None" = None,
    ) -> CompletionResponse:
        """Stream tokens via *on_token* callback and return the complete response.

        The default implementation calls ``complete_response`` once and fires
        *on_token* with the full content, so every provider works correctly
        even without a streaming override.  Providers that support real
        token-by-token streaming (OpenAI family) override this method to
        accumulate text *and* tool-call deltas in a single API call.

        Args:
            messages: Conversation messages.
            params: Completion parameters.
            on_token: Async or sync callable ``(text: str) -> None`` invoked
                for each token chunk.  May be ``None``.
        """
        import inspect
        response = await self._complete_response(messages, params)
        if on_token is not None and response.content:
            result = on_token(response.content)
            if inspect.isawaitable(result):
                await result
        return response

    async def stream_events(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> AsyncGenerator["StreamEvent", None]:
        """Yield typed StreamEvents (Mode B streaming).

        The default implementation performs a single batch completion and
        emits one ``TextDelta`` for the full response text plus one
        ``ToolCallEvent`` per tool call.  Providers that support real
        token-by-token streaming should override this method.
        """
        from ..types.stream import TextDelta, ToolCallEvent

        response = await self._complete_response(messages, params)
        if response.content:
            yield TextDelta(delta=response.content)
        for tc in response.tool_calls:
            yield ToolCallEvent(id=tc.id, name=tc.name, arguments=tc.arguments)

    async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
        """Provider-specific request-native completion (no retry logic)."""
        return await self._complete_response(request.messages, request.params)

    async def _complete_request_streaming(
        self,
        request: CompletionRequest,
        on_token: "Any | None" = None,
    ) -> CompletionResponse:
        """Provider-specific request-native streaming completion."""
        if self._overrides("complete_streaming"):
            return await self.complete_streaming(request.messages, request.params, on_token)

        import inspect

        response = await self._complete_request(request)
        if on_token is not None and response.content:
            result = on_token(response.content)
            if inspect.isawaitable(result):
                await result
        return response

    async def _stream_request_events(
        self,
        request: CompletionRequest,
    ) -> AsyncGenerator["StreamEvent", None]:
        """Provider-specific request-native typed streaming."""
        from ..types.stream import TextDelta, ToolCallEvent

        if self._overrides("stream_events"):
            async for event in self.stream_events(request.messages, request.params):
                yield event
            return

        response = await self._complete_request(request)
        if response.content:
            yield TextDelta(delta=response.content)
        for tc in response.tool_calls:
            yield ToolCallEvent(id=tc.id, name=tc.name, arguments=tc.arguments)

    async def complete_request(self, request: CompletionRequest) -> CompletionResponse:
        """Complete a structured request.

        New providers can override this method as their primary implementation.
        Existing providers remain compatible through ``complete_response``.
        """
        return await self._with_retry(lambda: self._complete_request(request))

    async def complete_request_streaming(
        self,
        request: CompletionRequest,
        on_token: "Any | None" = None,
    ) -> CompletionResponse:
        """Stream a structured request and return the final response."""
        return await self._with_retry(
            lambda: self._complete_request_streaming(request, on_token)
        )

    async def stream_request_events(
        self,
        request: CompletionRequest,
    ) -> AsyncGenerator["StreamEvent", None]:
        """Yield typed stream events for a structured request."""
        if self._circuit.is_open():
            raise ProviderUnavailableError("Circuit breaker open: provider unavailable")

        yielded = False
        try:
            async for event in self._stream_request_events(request):
                yielded = True
                yield event
            self._circuit.record_success()
        except Exception as exc:
            self._circuit.record_failure()
            if yielded:
                raise self._normalize_provider_exception(exc) from exc
            raise self._normalize_provider_exception(exc) from exc

    async def complete(self, messages: list, params: CompletionParams | None = None) -> str:
        """Completion with retry + circuit breaker."""
        if self._uses_request_native_completion():
            response = await self.complete_request(CompletionRequest.create(messages, params))
            return response.content
        return await self._with_retry(lambda: self._complete(messages, params))

    async def complete_response(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> CompletionResponse:
        """Structured completion with retry + circuit breaker."""
        if self._uses_request_native_completion():
            return await self.complete_request(CompletionRequest.create(messages, params))

        return await self._with_retry(lambda: self._complete_response(messages, params))

    async def _with_retry(self, operation: Callable[[], Awaitable[T]]) -> T:
        if self._circuit.is_open():
            raise ProviderUnavailableError("Circuit breaker open: provider unavailable")

        last_exc: Exception | None = None
        for attempt in range(self._retry.max_retries):
            try:
                result = await operation()
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

    def _uses_request_native_completion(self) -> bool:
        return self._overrides("_complete_request")

    def _overrides(self, method_name: str) -> bool:
        return getattr(type(self), method_name) is not getattr(LLMProvider, method_name)

    def _normalize_provider_exception(self, exc: Exception) -> ProviderError:
        if isinstance(exc, ProviderError):
            return exc

        message = str(exc)
        lowered = message.lower()
        if "rate limit" in lowered or "429" in lowered:
            return RateLimitError(message)
        return ProviderUnavailableError(message)
