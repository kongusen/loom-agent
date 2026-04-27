"""OpenAI provider."""

import inspect
import json
import threading
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

from ..types import ToolCall
from .base import (  # noqa: F401 (re-exported)
    CompletionParams,
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    TokenUsage,
    normalize_tool_call,
    parse_tool_arguments,
)


class OpenAIProvider(LLMProvider):
    """OpenAI chat-completions provider."""

    _shared_clients: dict[tuple[str, str | None, str | None], Any] = {}
    _pool_lock = threading.RLock()

    # Subclasses set this to the extensions key that enables thinking tokens
    # (e.g. "enable_thinking" for Qwen, "expose_reasoning" for DeepSeek/MiniMax).
    # When set and truthy, ``reasoning_content`` deltas are emitted as ThinkingDelta.
    _reasoning_ext_key: str | None = None

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        organization: str | None = None,
        client: Any | None = None,
        use_client_pool: bool = True,
    ):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.organization = organization
        self._client = client
        self._use_client_pool = use_client_pool

    @property
    def client(self) -> Any:
        """Lazily construct the OpenAI async client."""
        if self._client is None:
            if self._use_client_pool:
                with self._pool_lock:
                    pooled = self._shared_clients.get(self._pool_key())
                if pooled is not None:
                    self._client = pooled
                    return self._client

            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise ImportError(
                    "openai package is required to use OpenAIProvider. "
                    "Install loom-agent with the openai extra or add openai manually."
                ) from exc

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                organization=self.organization,
            )
            if self._use_client_pool:
                with self._pool_lock:
                    self._shared_clients[self._pool_key()] = self._client

        return self._client

    def _pool_key(self) -> tuple[str, str | None, str | None]:
        return (self.api_key, self.base_url, self.organization)

    @classmethod
    def clear_client_pool(cls) -> None:
        with cls._pool_lock:
            cls._shared_clients.clear()

    async def _complete(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> str:
        response = await self._complete_request(CompletionRequest.create(messages, params))
        return response.content

    async def _complete_response(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> CompletionResponse:
        return await self._complete_request(CompletionRequest.create(messages, params))

    async def _complete_request(
        self,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Generate a completion through OpenAI chat completions."""
        payload = self._build_request(request.messages, request.params)
        response = await self.client.chat.completions.create(**payload)
        choice = response.choices[0]
        message = getattr(choice, "message", None)
        content = self._extract_text(getattr(message, "content", ""))
        usage = getattr(response, "usage", None)
        return CompletionResponse(
            content=content,
            tool_calls=self._extract_tool_calls(getattr(message, "tool_calls", [])),
            usage=TokenUsage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            )
            if usage is not None
            else None,
            raw=response,
        )

    async def complete_streaming(
        self,
        messages: list,
        params: CompletionParams | None = None,
        on_token: Any | None = None,
    ) -> CompletionResponse:
        return await self._complete_request_streaming(
            CompletionRequest.create(messages, params),
            on_token,
        )

    async def _complete_request_streaming(
        self,
        request: CompletionRequest,
        on_token: Any | None = None,
    ) -> CompletionResponse:
        """Single streaming API call: yield tokens via *on_token*, accumulate
        tool-call deltas, return the complete ``CompletionResponse``."""
        payload = self._build_request(request.messages, request.params)
        stream = await self.client.chat.completions.create(**payload, stream=True)

        text_parts: list[str] = []
        # tool_deltas: index → {"id", "name", "arguments"}
        tool_deltas: dict[int, dict[str, str]] = {}

        async for chunk in stream:
            choices = getattr(chunk, "choices", [])
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue

            # --- text content ---
            content = getattr(delta, "content", None)
            if content:
                text_parts.append(content)
                if on_token is not None:
                    result = on_token(content)
                    if inspect.isawaitable(result):
                        await result

            # --- tool call deltas ---
            tc_deltas = getattr(delta, "tool_calls", None)
            if tc_deltas:
                for tc in tc_deltas:
                    idx = getattr(tc, "index", 0)
                    slot = tool_deltas.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                    if getattr(tc, "id", None):
                        slot["id"] += tc.id
                    fn = getattr(tc, "function", None)
                    if fn:
                        slot["name"] += getattr(fn, "name", "") or ""
                        slot["arguments"] += getattr(fn, "arguments", "") or ""

        tool_calls = self._parse_tool_deltas(tool_deltas)
        usage = getattr(chunk, "usage", None) if "chunk" in dir() else None  # type: ignore[possibly-undefined]
        return CompletionResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            usage=TokenUsage(
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            )
            if usage is not None
            else None,
        )

    def _parse_tool_deltas(self, tool_deltas: dict[int, dict[str, str]]) -> list[ToolCall]:
        tool_calls: list[ToolCall] = []
        for idx in sorted(tool_deltas.keys()):
            td = tool_deltas[idx]
            tool_call = normalize_tool_call(
                call_id=td["id"],
                name=td["name"],
                arguments=parse_tool_arguments(td["arguments"]),
            )
            if tool_call is not None:
                tool_calls.append(tool_call)
        return tool_calls

    async def stream(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> AsyncIterator[str]:
        """Stream completion chunks from OpenAI chat completions."""
        request = self._build_request(messages, params)
        stream = await self.client.chat.completions.create(**request, stream=True)
        async for chunk in stream:
            choices = getattr(chunk, "choices", [])
            if not choices:
                continue

            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue

            content = getattr(delta, "content", None)
            if not content:
                continue

            if isinstance(content, list):
                text = "".join(
                    part.get("text", "") if isinstance(part, dict) else getattr(part, "text", "")
                    for part in content
                )
                if text:
                    yield text
            else:
                yield content

    async def stream_events(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> AsyncGenerator[Any, None]:
        async for event in self._stream_request_events(CompletionRequest.create(messages, params)):
            yield event

    async def _stream_request_events(
        self,
        request: CompletionRequest,
    ) -> AsyncGenerator[Any, None]:
        """Yield typed StreamEvents from the OpenAI chat-completions SSE stream.

        Emits:
        - ``ThinkingDelta`` for ``reasoning_content`` tokens (when
          ``_reasoning_ext_key`` is set and truthy in extensions)
        - ``TextDelta`` for regular content tokens
        - ``ToolCallEvent`` for each tool call (assembled after stream ends)
        """
        from ..types.stream import TextDelta, ThinkingDelta, ToolCallEvent

        payload = self._build_request(request.messages, request.params)
        ext = request.params.extensions or {}
        expose_thinking = bool(self._reasoning_ext_key and ext.get(self._reasoning_ext_key))

        stream = await self.client.chat.completions.create(**payload, stream=True)
        # tool_deltas: index → {"id", "name", "arguments"}
        tool_deltas: dict[int, dict[str, str]] = {}

        async for chunk in stream:
            choices = getattr(chunk, "choices", [])
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue

            # Thinking tokens (Qwen3 / DeepSeek-R1 / MiniMax-M1)
            if expose_thinking:
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    yield ThinkingDelta(delta=reasoning)
                    continue

            # Regular text
            content = getattr(delta, "content", None)
            if content:
                if isinstance(content, list):
                    text = "".join(
                        p.get("text", "") if isinstance(p, dict) else getattr(p, "text", "")
                        for p in content
                    )
                    if text:
                        yield TextDelta(delta=text)
                else:
                    yield TextDelta(delta=content)

            # Accumulate tool-call deltas
            tc_deltas = getattr(delta, "tool_calls", None)
            if tc_deltas:
                for tc in tc_deltas:
                    idx = getattr(tc, "index", 0)
                    slot = tool_deltas.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                    if getattr(tc, "id", None):
                        slot["id"] += tc.id
                    fn = getattr(tc, "function", None)
                    if fn:
                        slot["name"] += getattr(fn, "name", "") or ""
                        slot["arguments"] += getattr(fn, "arguments", "") or ""

        # Emit assembled tool calls after stream ends
        for tool_call in self._parse_tool_deltas(tool_deltas):
            yield ToolCallEvent(
                id=tool_call.id,
                name=tool_call.name,
                arguments=tool_call.arguments,
            )

    def _build_request(
        self,
        messages: list,
        params: CompletionParams | None,
    ) -> dict[str, Any]:
        """Build a chat-completions request payload with multimodal support."""
        resolved = params or CompletionParams()
        converted_messages = self._convert_messages(messages)
        request = {
            "model": resolved.model,
            "messages": converted_messages,
            "temperature": resolved.temperature,
            "max_tokens": resolved.max_tokens,
        }
        tools = resolved.tool_dicts()
        if tools:
            request["tools"] = [
                {
                    "type": "function",
                    "function": tool,
                }
                for tool in tools
            ]
            request["tool_choice"] = resolved.tool_choice or "auto"
        return request

    def _convert_messages(self, messages: list) -> list[dict]:
        """Convert generic chat messages to OpenAI format with multimodal support (GPT-4 Vision)."""
        converted = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            if role == "assistant" and tool_calls:
                assistant_message: dict[str, Any] = {
                    "role": role,
                    "content": content or None,
                    "tool_calls": [
                        {
                            "id": tool_call["id"],
                            "type": "function",
                            "function": {
                                "name": tool_call["name"],
                                "arguments": json.dumps(
                                    tool_call.get("arguments", {}), ensure_ascii=False
                                ),
                            },
                        }
                        for tool_call in tool_calls
                    ],
                }
                converted.append(assistant_message)
                continue

            if role == "tool":
                converted.append(
                    {
                        "role": "tool",
                        "tool_call_id": message.get("tool_call_id"),
                        "content": content if isinstance(content, str) else str(content),
                    }
                )
                continue

            if isinstance(content, str):
                # Simple text content (backward compatible)
                converted.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Multimodal content with ContentBlocks
                content_parts = []
                for block in content:
                    if isinstance(block, dict):
                        # Already in dict format
                        block_type = block.get("type")
                        if block_type == "text":
                            content_parts.append({"type": "text", "text": block.get("text", "")})
                        elif block_type == "image":
                            # Convert to OpenAI image_url format
                            source = block.get("source", {})
                            if source.get("type") == "base64":
                                # Convert base64 to data URL
                                media_type = source.get("media_type", "image/png")
                                data = source.get("data", "")
                                image_url = f"data:{media_type};base64,{data}"
                            else:
                                # Use URL directly
                                image_url = source.get("url", "")

                            content_parts.append(
                                {"type": "image_url", "image_url": {"url": image_url}}
                            )
                    elif hasattr(block, "type"):
                        # ContentBlock dataclass
                        if block.type == "text":
                            content_parts.append(
                                {"type": "text", "text": getattr(block, "text", "")}
                            )
                        elif block.type == "image":
                            # Convert to OpenAI image_url format
                            source = getattr(block, "source", {})
                            if source.get("type") == "base64":
                                media_type = source.get("media_type", "image/png")
                                data = source.get("data", "")
                                image_url = f"data:{media_type};base64,{data}"
                            else:
                                image_url = source.get("url", "")

                            content_parts.append(
                                {"type": "image_url", "image_url": {"url": image_url}}
                            )

                converted.append({"role": role, "content": content_parts})
            else:
                # Fallback to string conversion
                converted.append({"role": role, "content": str(content)})

        return converted

    def _extract_text(self, content: Any) -> str:
        if isinstance(content, list):
            return "".join(
                part.get("text", "") if isinstance(part, dict) else getattr(part, "text", "")
                for part in content
            ).strip()
        return (content or "").strip()

    def _extract_tool_calls(self, value: Any) -> list[ToolCall]:
        tool_calls: list[ToolCall] = []
        for item in value or []:
            function = (
                item.get("function", {})
                if isinstance(item, dict)
                else getattr(item, "function", None)
            )
            if function is None:
                continue
            raw_arguments = (
                function.get("arguments", "{}")
                if isinstance(function, dict)
                else getattr(function, "arguments", "{}")
            )
            tool_call = normalize_tool_call(
                call_id=item.get("id", "") if isinstance(item, dict) else getattr(item, "id", ""),
                name=(
                    function.get("name", "")
                    if isinstance(function, dict)
                    else getattr(function, "name", "")
                ),
                arguments=parse_tool_arguments(raw_arguments),
            )
            if tool_call is not None:
                tool_calls.append(tool_call)
        return tool_calls
