"""MiniMax provider (OpenAI-compatible API).

Supports:
- ``MiniMax-Text-01`` — high-quality chat, tool calling
- ``MiniMax-M1`` — reasoning model with chain-of-thought
  (``reasoning_content`` returned alongside ``content``)
- ``abab6.5s-chat`` — lightweight fast model

Usage example::

    agent = Agent(model=Model.minimax("MiniMax-Text-01"))

    # M1 reasoning model
    agent = Agent(model=Model.minimax("MiniMax-M1"))

Provider-specific Generation.extensions keys:

- ``expose_reasoning`` (bool): When ``True``, prepend the M1 reasoning
  block to the returned ``content``.  Defaults to ``False``.
"""

from .base import CompletionRequest, CompletionResponse, TokenUsage
from .openai import OpenAIProvider

_MINIMAX_BASE_URL = "https://api.minimax.chat/v1"

# Models that emit reasoning_content
_REASONING_MODELS = {"MiniMax-M1", "minimax-m1"}


class MiniMaxProvider(OpenAIProvider):
    """MiniMax provider via OpenAI-compatible API.

    Args:
        api_key: MiniMax API key (https://platform.minimaxi.com/).
        base_url: Override the MiniMax endpoint.
    """

    # MiniMax-M1 thinking tokens are gated by "expose_reasoning" in extensions.
    _reasoning_ext_key = "expose_reasoning"

    def __init__(
        self,
        api_key: str,
        base_url: str = _MINIMAX_BASE_URL,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    async def _complete_request(
        self,
        request: CompletionRequest,
    ) -> CompletionResponse:
        """Parse response, extracting MiniMax-M1 reasoning_content."""
        payload = self._build_request(request.messages, request.params)
        response = await self.client.chat.completions.create(**payload)
        choice = response.choices[0]
        message = getattr(choice, "message", None)

        content = self._extract_text(getattr(message, "content", "") or "")
        reasoning = getattr(message, "reasoning_content", None) or ""

        ext = request.params.extensions or {}
        if ext.get("expose_reasoning") and reasoning:
            content = f"<think>\n{reasoning}\n</think>\n\n{content}".strip()
        elif not content and reasoning:
            content = reasoning

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
