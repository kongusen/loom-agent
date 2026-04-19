"""Anthropic Claude provider."""

import inspect
import threading
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

from ..types import ToolCall
from .base import CompletionParams, CompletionResponse, LLMProvider, TokenUsage


class AnthropicProvider(LLMProvider):
    """Anthropic messages API provider."""

    _shared_clients: dict[tuple[str, str | None], Any] = {}
    _pool_lock = threading.RLock()

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        client: Any | None = None,
        use_client_pool: bool = True,
    ):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self._client = client
        self._use_client_pool = use_client_pool

    @property
    def client(self) -> Any:
        """Lazily construct the Anthropic async client."""
        if self._client is None:
            if self._use_client_pool:
                with self._pool_lock:
                    pooled = self._shared_clients.get(self._pool_key())
                if pooled is not None:
                    self._client = pooled
                    return self._client

            try:
                from anthropic import AsyncAnthropic
            except ImportError as exc:
                raise ImportError(
                    "anthropic package is required to use AnthropicProvider. "
                    "Install loom-agent with the anthropic extra or add anthropic manually."
                ) from exc

            self._client = AsyncAnthropic(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            if self._use_client_pool:
                with self._pool_lock:
                    self._shared_clients[self._pool_key()] = self._client

        return self._client

    def _pool_key(self) -> tuple[str, str | None]:
        return (self.api_key, self.base_url)

    @classmethod
    def clear_client_pool(cls) -> None:
        with cls._pool_lock:
            cls._shared_clients.clear()

    async def _complete(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> str:
        response = await self._complete_response(messages, params)
        return response.content

    async def _complete_response(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> CompletionResponse:
        """Generate a completion through Anthropic messages API."""
        request = self._build_request(messages, params)
        response = await self.client.messages.create(**request)
        usage = getattr(response, "usage", None)
        content_blocks = getattr(response, "content", [])
        return CompletionResponse(
            content=self._extract_text_blocks(content_blocks),
            tool_calls=self._extract_tool_calls(content_blocks),
            usage=TokenUsage(
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
            ) if usage is not None else None,
            raw=response,
        )

    async def complete_streaming(
        self,
        messages: list,
        params: CompletionParams | None = None,
        on_token: Any | None = None,
    ) -> CompletionResponse:
        """Stream tokens via *on_token* and return the complete response.

        Anthropic's streaming API delivers text deltas and tool_use blocks as
        separate content_block events.  We accumulate both in a single pass
        so no second API call is needed.
        """
        import json as _json
        request = self._build_request(messages, params)
        stream = await self.client.messages.create(**request, stream=True)

        text_parts: list[str] = []
        # tool_use blocks accumulated by index
        tool_blocks: dict[int, dict] = {}
        current_block_idx: int | None = None

        async for event in stream:
            event_type = getattr(event, "type", "")

            if event_type == "content_block_start":
                block = getattr(event, "content_block", None)
                idx = getattr(event, "index", 0)
                if block and getattr(block, "type", "") == "tool_use":
                    tool_blocks[idx] = {
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input_json": "",
                    }
                    current_block_idx = idx
                else:
                    current_block_idx = None

            elif event_type == "content_block_delta":
                delta = getattr(event, "delta", None)
                if delta is None:
                    continue
                delta_type = getattr(delta, "type", "")

                if delta_type == "text_delta":
                    text = getattr(delta, "text", "")
                    if text:
                        text_parts.append(text)
                        if on_token is not None:
                            result = on_token(text)
                            if inspect.isawaitable(result):
                                await result

                elif delta_type == "input_json_delta" and current_block_idx is not None:
                    partial = getattr(delta, "partial_json", "")
                    if partial and current_block_idx in tool_blocks:
                        tool_blocks[current_block_idx]["input_json"] += partial

        # Parse accumulated tool use blocks
        tool_calls: list[ToolCall] = []
        for idx in sorted(tool_blocks.keys()):
            tb = tool_blocks[idx]
            try:
                arguments = _json.loads(tb["input_json"] or "{}")
            except _json.JSONDecodeError:
                arguments = {}
            tool_calls.append(ToolCall(
                id=tb["id"],
                name=tb["name"],
                arguments=arguments if isinstance(arguments, dict) else {},
            ))

        return CompletionResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
        )

    async def stream(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> AsyncIterator[str]:
        """Stream completion chunks from Anthropic messages API."""
        request = self._build_request(messages, params)
        stream = await self.client.messages.create(**request, stream=True)

        async for event in stream:
            event_type = getattr(event, "type", "")
            if event_type == "content_block_delta":
                delta = getattr(event, "delta", None)
                text = getattr(delta, "text", "") if delta is not None else ""
                if text:
                    yield text

    async def stream_events(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> AsyncGenerator["Any", None]:
        """Yield typed StreamEvents from Anthropic's SSE stream (Mode B).

        Emits:
        - ``ThinkingDelta`` for each extended-thinking token
        - ``TextDelta`` for each assistant text token
        - ``ToolCallEvent`` once per tool block (after args fully assembled)
        """
        import json as _json

        from ..types.stream import TextDelta, ThinkingDelta, ToolCallEvent

        request = self._build_request(messages, params)
        stream = await self.client.messages.create(**request, stream=True)

        # tool_use blocks accumulated by content-block index
        tool_blocks: dict[int, dict] = {}
        current_block_idx: int | None = None

        async for event in stream:
            etype = getattr(event, "type", "")

            if etype == "content_block_start":
                block = getattr(event, "content_block", None)
                idx = getattr(event, "index", 0)
                current_block_idx = idx
                if block and getattr(block, "type", "") == "tool_use":
                    tool_blocks[idx] = {
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input_json": "",
                    }

            elif etype == "content_block_delta":
                delta = getattr(event, "delta", None)
                if delta is None:
                    continue
                dtype = getattr(delta, "type", "")

                if dtype == "text_delta":
                    text = getattr(delta, "text", "")
                    if text:
                        yield TextDelta(delta=text)

                elif dtype == "thinking_delta":
                    thinking = getattr(delta, "thinking", "")
                    if thinking:
                        yield ThinkingDelta(delta=thinking)

                elif dtype == "input_json_delta" and current_block_idx is not None:
                    partial = getattr(delta, "partial_json", "")
                    if partial and current_block_idx in tool_blocks:
                        tool_blocks[current_block_idx]["input_json"] += partial

            elif etype == "content_block_stop":
                # Emit ToolCallEvent once the block is fully assembled
                if current_block_idx is not None and current_block_idx in tool_blocks:
                    tb = tool_blocks[current_block_idx]
                    try:
                        arguments = _json.loads(tb["input_json"] or "{}")
                    except _json.JSONDecodeError:
                        arguments = {}
                    yield ToolCallEvent(
                        id=tb["id"],
                        name=tb["name"],
                        arguments=arguments if isinstance(arguments, dict) else {},
                    )

    def _build_request(
        self,
        messages: list,
        params: CompletionParams | None,
    ) -> dict[str, Any]:
        """Build an Anthropic messages request payload."""
        resolved = params or CompletionParams()
        system, converted = self._convert_messages(messages)
        request: dict[str, Any] = {
            "model": resolved.model,
            "messages": converted,
            "max_tokens": resolved.max_tokens,
            "temperature": resolved.temperature,
        }
        if system:
            request["system"] = system
        if resolved.tools:
            request["tools"] = [
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("parameters", {"type": "object", "properties": {}, "required": []}),
                }
                for tool in resolved.tools
            ]
            request["tool_choice"] = {"type": resolved.tool_choice} if resolved.tool_choice else {"type": "auto"}
        return request

    def _convert_messages(self, messages: list) -> tuple[str | None, list[dict]]:
        """Convert generic chat messages to Anthropic format with multimodal support."""
        system_parts: list[str] = []
        converted: list[dict] = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            if role == "system":
                # System messages must be text only
                if isinstance(content, list):
                    # Extract text from content blocks
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif hasattr(block, "type") and block.type == "text":
                            text_parts.append(getattr(block, "text", ""))
                    system_parts.append("".join(text_parts))
                else:
                    system_parts.append(content)
                continue

            if role == "assistant" and tool_calls:
                content_blocks: list[dict[str, Any]] = []
                if isinstance(content, str) and content:
                    content_blocks.append({"type": "text", "text": content})
                elif isinstance(content, list):
                    content_blocks.extend(self._convert_content_blocks(content))

                content_blocks.extend(
                    {
                        "type": "tool_use",
                        "id": tool_call["id"],
                        "name": tool_call["name"],
                        "input": tool_call.get("arguments", {}),
                    }
                    for tool_call in tool_calls
                )
                converted.append({"role": "assistant", "content": content_blocks})
                continue

            if role == "tool":
                converted.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.get("tool_call_id"),
                                "content": content if isinstance(content, str) else str(content),
                            }
                        ],
                    }
                )
                continue

            # Convert content to Anthropic format
            if isinstance(content, str):
                # Simple text content (backward compatible)
                converted.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Multimodal content with ContentBlocks
                converted.append({"role": role, "content": self._convert_content_blocks(content)})
            else:
                # Fallback to string conversion
                converted.append({"role": role, "content": str(content)})

        system = "\n\n".join(part for part in system_parts if part).strip() or None
        return system, converted

    def _extract_text_blocks(self, blocks: list[Any]) -> str:
        """Extract concatenated text from Anthropic content blocks."""
        parts: list[str] = []
        for block in blocks:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(block["text"])
                continue

            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", "")
                if text:
                    parts.append(text)

        return "".join(parts).strip()

    def _extract_tool_calls(self, blocks: list[Any]) -> list[ToolCall]:
        tool_calls: list[ToolCall] = []
        for block in blocks:
            if isinstance(block, dict):
                if block.get("type") == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=block.get("id", ""),
                            name=block.get("name", ""),
                            arguments=block.get("input", {}) if isinstance(block.get("input", {}), dict) else {},
                        )
                    )
                continue

            if getattr(block, "type", None) == "tool_use":
                arguments = getattr(block, "input", {})
                tool_calls.append(
                    ToolCall(
                        id=getattr(block, "id", ""),
                        name=getattr(block, "name", ""),
                        arguments=arguments if isinstance(arguments, dict) else {},
                    )
                )
        return tool_calls

    def _convert_content_blocks(self, content: list[Any]) -> list[dict[str, Any]]:
        content_blocks: list[dict[str, Any]] = []
        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type")
                if block_type == "text":
                    content_blocks.append({"type": "text", "text": block.get("text", "")})
                elif block_type == "image":
                    content_blocks.append({"type": "image", "source": block.get("source", {})})
                elif block_type == "document":
                    content_blocks.append({"type": "document", "source": block.get("source", {})})
                continue

            if hasattr(block, "type"):
                if block.type == "text":
                    content_blocks.append({"type": "text", "text": getattr(block, "text", "")})
                elif block.type == "image":
                    content_blocks.append({"type": "image", "source": getattr(block, "source", {})})
                elif block.type == "document":
                    content_blocks.append({"type": "document", "source": getattr(block, "source", {})})
        return content_blocks
