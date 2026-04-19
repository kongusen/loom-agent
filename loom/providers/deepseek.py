"""DeepSeek provider (OpenAI-compatible API).

Supports:
- ``deepseek-chat`` (DeepSeek-V3) — full tool calling support
- ``deepseek-reasoner`` (DeepSeek-R1) — chain-of-thought via
  ``reasoning_content``; note: tool calling is NOT supported on the
  reasoner model by the DeepSeek API.

Usage example::

    # Standard chat model with tools
    agent = create_agent(AgentConfig(
        model=ModelRef.deepseek("deepseek-chat"),
    ))

    # Reasoner / R1 for deep analysis (no tool calls)
    agent = create_agent(AgentConfig(
        model=ModelRef.deepseek("deepseek-reasoner"),
    ))

Provider-specific GenerationConfig.extensions keys:

- ``expose_reasoning`` (bool): When ``True``, prepend the chain-of-thought
  block to the returned ``content`` so downstream agents can see it.
  Defaults to ``False`` (reasoning is discarded from visible output but
  still influences the model's final answer).
"""

from typing import Any

from .base import CompletionParams, CompletionResponse, TokenUsage
from .openai import OpenAIProvider

_DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# Models that return reasoning_content
_REASONER_MODELS = {"deepseek-reasoner", "deepseek-r1"}


class DeepSeekProvider(OpenAIProvider):
    """DeepSeek chat-completions provider.

    Args:
        api_key: DeepSeek API key (https://platform.deepseek.com/).
        base_url: Override the DeepSeek endpoint (e.g. for a proxy or
            a compatible self-hosted deployment).
    """

    # DeepSeek-R1 thinking tokens are gated by "expose_reasoning" in extensions.
    _reasoning_ext_key = "expose_reasoning"

    def __init__(
        self,
        api_key: str,
        base_url: str = _DEEPSEEK_BASE_URL,
    ):
        super().__init__(api_key=api_key, base_url=base_url)

    # ------------------------------------------------------------------
    # Request building
    # ------------------------------------------------------------------

    def _build_request(
        self,
        messages: list,
        params: CompletionParams | None,
    ) -> dict[str, Any]:
        request = super()._build_request(messages, params)
        model = request.get("model", "")

        # deepseek-reasoner does not support tool calling — strip tools to
        # avoid a 400 error from the API.
        if model in _REASONER_MODELS:
            request.pop("tools", None)
            request.pop("tool_choice", None)

        return request

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    async def _complete_response(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> CompletionResponse:
        """Parse response and optionally surface reasoning_content."""
        request = self._build_request(messages, params)
        response = await self.client.chat.completions.create(**request)
        choice = response.choices[0]
        message = getattr(choice, "message", None)

        content = self._extract_text(getattr(message, "content", "") or "")
        # reasoning_content is the internal scratchpad from R1/Reasoner
        reasoning = getattr(message, "reasoning_content", None) or ""

        ext = (params.extensions if params is not None else None) or {}
        if ext.get("expose_reasoning") and reasoning:
            # Prepend <think>…</think> so the agent can optionally use it
            content = f"<think>\n{reasoning}\n</think>\n\n{content}".strip()
        elif not content and reasoning:
            # Fallback: surface reasoning if content is somehow empty
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

    async def stream(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ):
        """Stream completion chunks.

        For ``deepseek-reasoner``, thinking tokens (``delta.reasoning_content``)
        are yielded wrapped in ``<think>…</think>`` tags when
        ``expose_reasoning=True`` is set in extensions.  Regular content
        tokens are always yielded.
        """
        request = self._build_request(messages, params)
        ext = (params.extensions if params is not None else None) or {}
        expose = ext.get("expose_reasoning", False)

        stream = await self.client.chat.completions.create(**request, stream=True)
        in_thinking = False
        async for chunk in stream:
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
    # Context assembly
    # ------------------------------------------------------------------

    def _convert_messages(self, messages: list) -> list[dict]:
        """Convert messages to DeepSeek format.

        For the reasoner model, previous assistant turns must not include
        ``reasoning_content`` — only plain ``content`` is accepted.  Our
        internal message format never stores reasoning_content, so the
        standard OpenAI conversion is already correct.  This override
        exists for documentation clarity and future-proofing.
        """
        return super()._convert_messages(messages)
