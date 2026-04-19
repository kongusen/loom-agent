"""MiniMax provider (OpenAI-compatible API).

Supports:
- ``MiniMax-Text-01`` — high-quality chat, tool calling
- ``MiniMax-M1`` — reasoning model with chain-of-thought
  (``reasoning_content`` returned alongside ``content``)
- ``abab6.5s-chat`` — lightweight fast model

Usage example::

    agent = create_agent(AgentConfig(
        model=ModelRef.minimax("MiniMax-Text-01"),
    ))

    # M1 reasoning model
    agent = create_agent(AgentConfig(
        model=ModelRef.minimax("MiniMax-M1"),
    ))

Provider-specific GenerationConfig.extensions keys:

- ``expose_reasoning`` (bool): When ``True``, prepend the M1 reasoning
  block to the returned ``content``.  Defaults to ``False``.
"""

from typing import Any

from .base import CompletionParams, CompletionResponse, TokenUsage
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
    ):
        super().__init__(api_key=api_key, base_url=base_url)

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def stream(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ):
        """Stream completion chunks, yielding MiniMax-M1 thinking tokens
        when ``expose_reasoning=True`` is set in extensions."""
        request = self._build_request(messages, params)
        ext = (params.extensions if params is not None else None) or {}
        expose = ext.get("expose_reasoning", False)

        stream_resp = await self.client.chat.completions.create(**request, stream=True)
        in_thinking = False
        async for chunk in stream_resp:
            choices = getattr(chunk, "choices", [])
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue

            if expose:
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    if not in_thinking:
                        yield "<think>\n"
                        in_thinking = True
                    yield reasoning
                    continue
                if in_thinking:
                    yield "\n</think>\n\n"
                    in_thinking = False

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

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    async def _complete_response(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> CompletionResponse:
        """Parse response, extracting MiniMax-M1 reasoning_content."""
        request = self._build_request(messages, params)
        response = await self.client.chat.completions.create(**request)
        choice = response.choices[0]
        message = getattr(choice, "message", None)

        content = self._extract_text(getattr(message, "content", "") or "")
        reasoning = getattr(message, "reasoning_content", None) or ""

        ext = (params.extensions if params is not None else None) or {}
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
            ) if usage is not None else None,
            raw=response,
        )
