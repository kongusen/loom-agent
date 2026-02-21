"""Gemini LLM provider — uses OpenAI-compatible endpoint."""

from __future__ import annotations

from typing import AsyncGenerator

from ..types import AssistantMessage, CompletionResult, CompletionParams, StreamChunk, ToolCall, TokenUsage, ToolDefinition, Message
from ..config import AgentConfig
from .base import BaseLLMProvider


_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _msg_to_dict(m: Message) -> dict:
    d = {"role": m.role, "content": m.content}
    if hasattr(m, "tool_calls") and m.tool_calls:
        d["tool_calls"] = [
            {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.arguments}}
            for tc in m.tool_calls
        ]
    if hasattr(m, "tool_call_id"):
        d["tool_call_id"] = m.tool_call_id
    return d


def _tools_to_dicts(tools: list[ToolDefinition]) -> list[dict]:
    return [
        {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters.to_json_schema()}}
        for t in tools
    ]


class GeminiProvider(BaseLLMProvider):
    def __init__(self, config: AgentConfig, **kwargs) -> None:
        super().__init__(**kwargs)
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("pip install openai")
        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url or _GEMINI_BASE,
        )
        self._model = config.model or "gemini-2.0-flash"

    async def _do_complete(self, params: CompletionParams) -> CompletionResult:
        kwargs: dict = {
            "model": self._model,
            "messages": [_msg_to_dict(m) for m in params.messages],
            "temperature": params.temperature,
            "max_tokens": params.max_tokens,
        }
        if params.tools:
            kwargs["tools"] = _tools_to_dicts(params.tools)
        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        tool_calls = []
        if choice.message.tool_calls:
            tool_calls = [ToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments) for tc in choice.message.tool_calls]
        usage = TokenUsage()
        if resp.usage:
            usage = TokenUsage(prompt_tokens=resp.usage.prompt_tokens, completion_tokens=resp.usage.completion_tokens, total_tokens=resp.usage.total_tokens)
        return CompletionResult(content=choice.message.content or "", tool_calls=tool_calls, usage=usage)

    async def _do_stream(self, params: CompletionParams) -> AsyncGenerator[StreamChunk, None]:
        kwargs: dict = {
            "model": self._model,
            "messages": [_msg_to_dict(m) for m in params.messages],
            "temperature": params.temperature,
            "max_tokens": params.max_tokens,
            "stream": True,
        }
        if params.tools:
            kwargs["tools"] = _tools_to_dicts(params.tools)
        resp = await self._client.chat.completions.create(**kwargs)
        tc_buffers: dict[int, dict] = {}
        async for chunk in resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            finish = chunk.choices[0].finish_reason
            if delta and delta.content:
                yield StreamChunk(text=delta.content)
            if delta and delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tc_buffers:
                        tc_buffers[idx] = {"id": "", "name": "", "args": ""}
                    if tc.id:
                        tc_buffers[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        tc_buffers[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        tc_buffers[idx]["args"] += tc.function.arguments
            if finish:
                for buf in tc_buffers.values():
                    yield StreamChunk(tool_call=ToolCall(
                        id=buf["id"], name=buf["name"], arguments=buf["args"],
                    ))
                tc_buffers.clear()
                yield StreamChunk(finish_reason=finish)
