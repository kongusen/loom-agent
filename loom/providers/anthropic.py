"""Anthropic Claude LLM provider."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from ..types import (
    AssistantMessage, CompletionResult, CompletionParams, StreamChunk, ToolCall,
    TokenUsage, Message, ToolDefinition,
)
from ..config import AgentConfig
from .base import BaseLLMProvider


def _msg_to_dict(m: Message) -> dict:
    # ToolMessage → Anthropic tool_result (must be role=user)
    if hasattr(m, "tool_call_id") and m.role == "tool":
        return {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content}],
        }
    # AssistantMessage with tool_calls → mixed content blocks
    if hasattr(m, "tool_calls") and m.tool_calls:
        blocks: list[dict] = []
        if m.content:
            blocks.append({"type": "text", "text": m.content})
        for tc in m.tool_calls:
            blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": json.loads(tc.arguments)})
        return {"role": "assistant", "content": blocks}
    return {"role": m.role, "content": m.content}


def _tools_to_dicts(tools: list[ToolDefinition]) -> list[dict]:
    return [
        {"name": t.name, "description": t.description, "input_schema": t.parameters.to_json_schema()}
        for t in tools
    ]


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, config: AgentConfig, **kwargs) -> None:
        super().__init__(**kwargs)
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError("pip install anthropic")
        self._client = AsyncAnthropic(api_key=config.api_key, base_url=config.base_url)
        self._model = config.model
        self._max_tokens = config.max_tokens

    async def _do_complete(self, params: CompletionParams) -> CompletionResult:
        system = "\n\n".join(m.content for m in params.messages if m.role == "system")
        msgs = [_msg_to_dict(m) for m in params.messages if m.role != "system"]
        kwargs: dict = {"model": self._model, "max_tokens": params.max_tokens, "messages": msgs}
        if system:
            kwargs["system"] = system
        if params.tools:
            kwargs["tools"] = _tools_to_dicts(params.tools)
        resp = await self._client.messages.create(**kwargs)
        text, tool_calls = "", []
        for block in resp.content:
            if block.type == "text":
                text += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=json.dumps(block.input)))
        usage = TokenUsage()
        if resp.usage:
            usage = TokenUsage(prompt_tokens=resp.usage.input_tokens, completion_tokens=resp.usage.output_tokens, total_tokens=resp.usage.input_tokens + resp.usage.output_tokens)
        return CompletionResult(content=text, tool_calls=tool_calls, usage=usage)

    async def _do_stream(self, params: CompletionParams) -> AsyncGenerator[StreamChunk, None]:
        system = "\n\n".join(m.content for m in params.messages if m.role == "system")
        msgs = [_msg_to_dict(m) for m in params.messages if m.role != "system"]
        kwargs: dict = {"model": self._model, "max_tokens": params.max_tokens, "messages": msgs}
        if system:
            kwargs["system"] = system
        if params.tools:
            kwargs["tools"] = _tools_to_dicts(params.tools)
        async with self._client.messages.stream(**kwargs) as stream:
            current_tool: dict | None = None
            async for event in stream:
                if event.type == "content_block_start" and event.content_block.type == "tool_use":
                    current_tool = {"id": event.content_block.id, "name": event.content_block.name, "args": ""}
                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        yield StreamChunk(text=event.delta.text)
                    elif hasattr(event.delta, "partial_json"):
                        if current_tool:
                            current_tool["args"] += event.delta.partial_json
                elif event.type == "content_block_stop" and current_tool:
                    yield StreamChunk(tool_call=ToolCall(
                        id=current_tool["id"], name=current_tool["name"], arguments=current_tool["args"],
                    ))
                    current_tool = None
                elif event.type == "message_stop":
                    yield StreamChunk(finish_reason="end_turn")
