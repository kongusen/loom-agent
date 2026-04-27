"""Qwen provider (Alibaba Cloud DashScope, OpenAI-compatible).

Supports:
- Standard Qwen models (qwen-plus, qwen-turbo, qwen-max, qwen2.5-*)
- Qwen3 thinking models (enable_thinking via GenerationConfig.extensions)
- Tool calling through the OpenAI-compatible endpoint
- reasoning_content extraction from thinking responses

Usage example::

    agent = create_agent(AgentConfig(
        model=ModelRef.qwen("qwen3-235b-a22b"),
        generation=GenerationConfig(
            extensions={"enable_thinking": True, "thinking_budget": 8000}
        ),
    ))
"""

from typing import Any

from .base import CompletionParams, CompletionResponse, TokenUsage
from .openai import OpenAIProvider

_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class QwenProvider(OpenAIProvider):
    """Qwen provider via Alibaba Cloud DashScope OpenAI-compatible API.

    Args:
        api_key: DashScope API key (https://dashscope.console.aliyun.com/).
        base_url: Override the DashScope endpoint (e.g. for a proxy).

    Provider-specific GenerationConfig.extensions keys:

    - ``enable_thinking`` (bool): Enable chain-of-thought for Qwen3 models.
      Defaults to ``False``.  When enabled, the model returns
      ``reasoning_content`` alongside the regular ``content``.
    - ``thinking_budget`` (int): Maximum tokens for the thinking block
      (DashScope default is 8192 when thinking is enabled).
    - ``repetition_penalty`` (float): Penalise token repetition
      (alternative to temperature; e.g. 1.1).
    """

    # Qwen3 thinking tokens are gated by "enable_thinking" in extensions.
    _reasoning_ext_key = "enable_thinking"

    def __init__(
        self,
        api_key: str,
        base_url: str = _DASHSCOPE_BASE_URL,
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
        """Build request with Qwen-specific extensions."""
        request = super()._build_request(messages, params)
        ext = (params.extensions if params is not None else None) or {}

        extra_body: dict[str, Any] = {}

        # Thinking (Qwen3 models only)
        if ext.get("enable_thinking"):
            extra_body["enable_thinking"] = True
            if "thinking_budget" in ext:
                extra_body["thinking_budget"] = int(ext["thinking_budget"])
        elif "enable_thinking" in ext:
            # Explicit False — disable thinking even if model default is on
            extra_body["enable_thinking"] = False

        if extra_body:
            request["extra_body"] = extra_body

        # Repetition penalty (top-level param, not in extra_body)
        if "repetition_penalty" in ext:
            request["extra_body"] = request.get("extra_body") or {}
            request["extra_body"]["repetition_penalty"] = float(ext["repetition_penalty"])

        return request

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    async def stream(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ):
        """Stream completion chunks, yielding thinking tokens when enabled.

        When ``enable_thinking`` is set in extensions, thinking tokens
        (``delta.reasoning_content``) are yielded first wrapped in
        ``<think>…</think>`` tags, followed by the regular content tokens.
        """
        request = self._build_request(messages, params)
        ext = (params.extensions if params is not None else None) or {}
        expose = ext.get("enable_thinking", False)

        stream = await self.client.chat.completions.create(**request, stream=True)
        in_thinking = False
        async for chunk in stream:
            choices = getattr(chunk, "choices", [])
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue

            # Thinking delta (Qwen3)
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

            # Regular content delta
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

    async def _complete_response(
        self,
        messages: list,
        params: CompletionParams | None = None,
    ) -> CompletionResponse:
        """Parse response including Qwen3 reasoning_content."""
        request = self._build_request(messages, params)
        response = await self.client.chat.completions.create(**request)
        choice = response.choices[0]
        message = getattr(choice, "message", None)

        content = self._extract_text(getattr(message, "content", "") or "")
        # reasoning_content is the internal chain-of-thought from Qwen3
        reasoning = getattr(message, "reasoning_content", None) or ""

        # If the model only returned thinking (no content yet), surface it
        if not content and reasoning:
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
