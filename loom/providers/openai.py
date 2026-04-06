"""OpenAI provider."""

from typing import Any, AsyncIterator

from .base import CompletionParams, LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI chat-completions provider."""

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        organization: str | None = None,
        client: Any | None = None,
    ):
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
        """Generate a completion through OpenAI chat completions."""
        request = self._build_request(messages, params)
        response = await self.client.chat.completions.create(**request)
        choice = response.choices[0]
        content = getattr(choice.message, "content", "")
        if isinstance(content, list):
            return "".join(
                part.get("text", "") if isinstance(part, dict) else getattr(part, "text", "")
                for part in content
            ).strip()
        return (content or "").strip()

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
        """Build a chat-completions request payload."""
        resolved = params or CompletionParams()
        return {
            "model": resolved.model,
            "messages": messages,
            "temperature": resolved.temperature,
            "max_tokens": resolved.max_tokens,
        }
