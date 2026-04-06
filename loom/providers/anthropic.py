"""Anthropic Claude provider."""

from typing import Any, AsyncIterator

from .base import CompletionParams, LLMProvider


class AnthropicProvider(LLMProvider):
    """Anthropic messages API provider."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        client: Any | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self._client = client

    @property
    def client(self) -> Any:
        """Lazily construct the Anthropic async client."""
        if self._client is None:
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

        return self._client

    async def _complete(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> str:
        """Generate a completion through Anthropic messages API."""
        request = self._build_request(messages, params)
        response = await self.client.messages.create(**request)
        return self._extract_text_blocks(getattr(response, "content", []))

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
        return request

    def _convert_messages(self, messages: list) -> tuple[str | None, list[dict[str, str]]]:
        """Convert generic chat messages to Anthropic format."""
        system_parts: list[str] = []
        converted: list[dict[str, str]] = []

        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "system":
                system_parts.append(content)
                continue

            converted.append({"role": role, "content": content})

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
