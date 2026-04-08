"""OpenAI provider."""

import json
from collections.abc import AsyncIterator
from typing import Any

from ..types import ToolCall
from .base import CompletionParams, CompletionResponse, LLMProvider, TokenUsage


class OpenAIProvider(LLMProvider):
    """OpenAI chat-completions provider."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        organization: str | None = None,
        client: Any | None = None,
    ):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.organization = organization
        self._client = client

    @property
    def client(self) -> Any:
        """Lazily construct the OpenAI async client."""
        if self._client is None:
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

        return self._client

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
        """Generate a completion through OpenAI chat completions."""
        request = self._build_request(messages, params)
        response = await self.client.chat.completions.create(**request)
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
            ) if usage is not None else None,
            raw=response,
        )

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
        if resolved.tools:
            request["tools"] = [
                {
                    "type": "function",
                    "function": tool,
                }
                for tool in resolved.tools
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
                                "arguments": json.dumps(tool_call.get("arguments", {}), ensure_ascii=False),
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

                            content_parts.append({
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            })
                    elif hasattr(block, "type"):
                        # ContentBlock dataclass
                        if block.type == "text":
                            content_parts.append({"type": "text", "text": getattr(block, "text", "")})
                        elif block.type == "image":
                            # Convert to OpenAI image_url format
                            source = getattr(block, "source", {})
                            if source.get("type") == "base64":
                                media_type = source.get("media_type", "image/png")
                                data = source.get("data", "")
                                image_url = f"data:{media_type};base64,{data}"
                            else:
                                image_url = source.get("url", "")

                            content_parts.append({
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            })

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
            function = item.get("function", {}) if isinstance(item, dict) else getattr(item, "function", None)
            if function is None:
                continue
            raw_arguments = (
                function.get("arguments", "{}")
                if isinstance(function, dict)
                else getattr(function, "arguments", "{}")
            )
            try:
                arguments = json.loads(raw_arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append(
                ToolCall(
                    id=str(item.get("id", "")) if isinstance(item, dict) else str(getattr(item, "id", "")),
                    name=(
                        str(function.get("name", ""))
                        if isinstance(function, dict)
                        else str(getattr(function, "name", ""))
                    ),
                    arguments=arguments if isinstance(arguments, dict) else {},
                )
            )
        return tool_calls
