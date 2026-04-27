"""Google Gemini provider."""

import threading
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

from ..types import ToolCall
from .base import (
    CompletionParams,
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    normalize_tool_call,
)


class GeminiProvider(LLMProvider):
    """Google Gemini provider using google-generativeai SDK."""

    _shared_clients: dict[tuple[str], Any] = {}
    _pool_lock = threading.RLock()

    def __init__(
        self,
        api_key: str,
        client: Any | None = None,
        use_client_pool: bool = True,
    ):
        super().__init__()
        self.api_key = api_key
        self._client = client
        self._use_client_pool = use_client_pool

    @property
    def client(self) -> Any:
        """Lazily construct the Google GenerativeAI client."""
        if self._client is None:
            if self._use_client_pool:
                with self._pool_lock:
                    pooled = self._shared_clients.get(self._pool_key())
                if pooled is not None:
                    self._client = pooled
                    return self._client

            try:
                import google.generativeai as genai
            except ImportError as exc:
                raise ImportError(
                    "google-generativeai package is required to use GeminiProvider. "
                    "Install loom-agent with the gemini extra or add google-generativeai manually."
                ) from exc

            genai.configure(api_key=self.api_key)
            self._client = genai
            if self._use_client_pool:
                with self._pool_lock:
                    self._shared_clients[self._pool_key()] = self._client

        return self._client

    def _pool_key(self) -> tuple[str]:
        return (self.api_key,)

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
        """Generate a completion through Google Gemini API."""
        resolved = request.params

        # Convert messages to Gemini format
        contents = self._convert_messages(request.messages)

        # Create model
        model = self.client.GenerativeModel(resolved.model)

        # Generate content
        payload: dict[str, Any] = {
            "contents": contents,
            "generation_config": {
                "temperature": resolved.temperature,
                "max_output_tokens": resolved.max_tokens,
            },
        }
        tools = resolved.tool_dicts()
        if tools:
            payload["tools"] = self._build_tools(tools)
            if tool_config := self._build_tool_config(resolved.tool_choice):
                payload["tool_config"] = tool_config

        response = await model.generate_content_async(**payload)

        return CompletionResponse(
            content=self._extract_text(response),
            tool_calls=self._extract_tool_calls(response),
            raw=response,
        )

    async def stream(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> AsyncIterator[str]:
        """Stream completion chunks from Google Gemini API."""
        resolved = params or CompletionParams()

        # Convert messages to Gemini format
        contents = self._convert_messages(messages)

        # Create model
        model = self.client.GenerativeModel(resolved.model)

        # Stream content
        payload: dict[str, Any] = {
            "contents": contents,
            "generation_config": {
                "temperature": resolved.temperature,
                "max_output_tokens": resolved.max_tokens,
            },
            "stream": True,
        }
        tools = resolved.tool_dicts()
        if tools:
            payload["tools"] = self._build_tools(tools)
            if tool_config := self._build_tool_config(resolved.tool_choice):
                payload["tool_config"] = tool_config

        response = await model.generate_content_async(**payload)

        async for chunk in response:
            if chunk.text:
                yield chunk.text

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
        """Yield typed StreamEvents from the Gemini generate_content_async stream.

        Emits ``TextDelta`` for each text chunk and ``ToolCallEvent`` for
        any function_call parts encountered during streaming.
        """
        from ..types.stream import TextDelta, ToolCallEvent

        resolved = request.params
        contents = self._convert_messages(request.messages)
        model = self.client.GenerativeModel(resolved.model)

        payload: dict[str, Any] = {
            "contents": contents,
            "generation_config": {
                "temperature": resolved.temperature,
                "max_output_tokens": resolved.max_tokens,
            },
            "stream": True,
        }
        tools = resolved.tool_dicts()
        if tools:
            payload["tools"] = self._build_tools(tools)
            if tool_config := self._build_tool_config(resolved.tool_choice):
                payload["tool_config"] = tool_config

        response = await model.generate_content_async(**payload)

        seen_tool_ids: set[str] = set()
        async for chunk in response:
            # Text delta
            try:
                text = chunk.text
                if text:
                    yield TextDelta(delta=text)
            except Exception:
                pass

            # Tool calls (function_call parts in candidates)
            for tc in self._extract_tool_calls(chunk):
                if tc.id not in seen_tool_ids:
                    seen_tool_ids.add(tc.id)
                    yield ToolCallEvent(id=tc.id, name=tc.name, arguments=tc.arguments)

    def _convert_messages(self, messages: list) -> list[dict[str, Any]]:
        """Convert generic chat messages to Gemini format with multimodal support.

        Gemini uses a different message format:
        - role: "user" or "model" (not "assistant")
        - parts: list of content parts (text, inline_data for images)
        - system messages are handled separately or prepended to first user message
        """
        system_parts: list[str] = []
        converted: list[dict[str, Any]] = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            # Collect system messages
            if role == "system":
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
                parts = self._to_gemini_parts(content)
                parts.extend(
                    {
                        "function_call": {
                            "name": tool_call["name"],
                            "args": tool_call.get("arguments", {}),
                        }
                    }
                    for tool_call in tool_calls
                )
                converted.append({"role": "model", "parts": parts})
                continue

            if role == "tool":
                converted.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "function_response": {
                                    "name": message.get("name")
                                    or message.get("tool_call_id")
                                    or "tool",
                                    "response": {
                                        "content": content
                                        if isinstance(content, str)
                                        else str(content)
                                    },
                                }
                            }
                        ],
                    }
                )
                continue

            # Convert role: "assistant" -> "model"
            gemini_role = "model" if role == "assistant" else "user"

            # Convert content to Gemini parts format
            converted.append(
                {
                    "role": gemini_role,
                    "parts": self._to_gemini_parts(content),
                }
            )

        # Prepend system messages to first user message if any
        if system_parts and converted:
            system_text = "\n\n".join(system_parts)
            first_msg = converted[0]
            if first_msg["role"] == "user":
                # Prepend system context to first user message
                first_msg["parts"] = [{"text": f"{system_text}\n\n{first_msg['parts'][0]['text']}"}]
            else:
                # Insert system as first user message
                converted.insert(0, {"role": "user", "parts": [{"text": system_text}]})

        return converted

    def _extract_text(self, response: Any) -> str:
        """Extract text from Gemini response."""
        try:
            # Gemini response has .text attribute
            if hasattr(response, "text"):
                text = response.text
                if isinstance(text, str):
                    return text.strip()

            # Fallback: try to get from candidates
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                    parts = candidate.content.parts
                    text_parts = [part.text for part in parts if hasattr(part, "text")]
                    return "".join(text_parts).strip()

            return ""
        except Exception:
            return ""

    def _extract_tool_calls(self, response: Any) -> list[ToolCall]:
        tool_calls: list[ToolCall] = []
        for part in self._iter_parts(response):
            function_call = self._get_field(part, "function_call")
            if not function_call:
                continue
            name = self._get_field(function_call, "name", "")
            arguments = self._get_field(function_call, "args", {}) or {}
            tool_call = normalize_tool_call(
                call_id=f"{name}_{len(tool_calls) + 1}",
                name=name,
                arguments=arguments,
            )
            if tool_call is not None:
                tool_calls.append(tool_call)
        return tool_calls

    def _iter_parts(self, response: Any) -> list[Any]:
        candidates = getattr(response, "candidates", None)
        if not candidates:
            return []
        candidate = candidates[0]
        content = getattr(candidate, "content", None)
        if content is None:
            return []
        return list(getattr(content, "parts", []) or [])

    def _get_field(self, value: Any, field: str, default: Any = None) -> Any:
        if isinstance(value, dict):
            return value.get(field, default)
        return getattr(value, field, default)

    def _to_gemini_parts(self, content: Any) -> list[dict[str, Any]]:
        if isinstance(content, str):
            return [{"text": content}] if content else []
        if isinstance(content, list):
            parts: list[dict[str, Any]] = []
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type")
                    if block_type == "text":
                        parts.append({"text": block.get("text", "")})
                    elif block_type == "image":
                        source = block.get("source", {})
                        if source.get("type") == "base64":
                            parts.append(
                                {
                                    "inline_data": {
                                        "mime_type": source.get("media_type", "image/png"),
                                        "data": source.get("data", ""),
                                    }
                                }
                            )
                elif hasattr(block, "type"):
                    if block.type == "text":
                        parts.append({"text": getattr(block, "text", "")})
                    elif block.type == "image":
                        source = getattr(block, "source", {})
                        if source.get("type") == "base64":
                            parts.append(
                                {
                                    "inline_data": {
                                        "mime_type": source.get("media_type", "image/png"),
                                        "data": source.get("data", ""),
                                    }
                                }
                            )
            return parts
        return [{"text": str(content)}]

    def _build_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "function_declarations": [
                    {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get(
                            "parameters",
                            {"type": "object", "properties": {}, "required": []},
                        ),
                    }
                ]
            }
            for tool in tools
        ]

    def _build_tool_config(self, tool_choice: str | None) -> dict[str, Any] | None:
        if tool_choice is None:
            return {"function_calling_config": {"mode": "AUTO"}}
        normalized = tool_choice.lower()
        if normalized == "none":
            mode = "NONE"
        elif normalized in {"required", "any"}:
            mode = "ANY"
        else:
            mode = "AUTO"
        return {"function_calling_config": {"mode": mode}}
