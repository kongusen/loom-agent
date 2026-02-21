"""Loop strategies — pluggable execution patterns (ToolUse, ReAct, etc.)."""

from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncGenerator, Protocol, runtime_checkable

from ..types import (
    AgentEvent, TextDeltaEvent, ToolCallStartEvent, ToolCallEndEvent,
    StepStartEvent, StepEndEvent, ErrorEvent, DoneEvent, TokenUsage,
    CompletionParams, Message, AssistantMessage, ToolMessage,
    ToolCall, ToolContext, LLMProvider, ToolDefinition,
)
from ..errors import AgentAbortError, AgentMaxStepsError


def _accumulate_usage(total: TokenUsage, step: TokenUsage) -> None:
    total.prompt_tokens += step.prompt_tokens
    total.completion_tokens += step.completion_tokens
    total.total_tokens += step.total_tokens


@runtime_checkable
class LoopStrategy(Protocol):
    name: str
    def execute(self, ctx: LoopContext) -> AsyncGenerator[AgentEvent, None]: ...


class LoopContext:
    __slots__ = (
        "messages", "provider", "tools", "tool_registry",
        "max_steps", "streaming", "temperature", "max_tokens",
        "session_id", "tenant_id", "agent_id",
        "interceptors", "events", "signal", "tool_config",
    )

    def __init__(self, **kwargs) -> None:
        for k in self.__slots__:
            setattr(self, k, kwargs.get(k))


class ToolUseStrategy:
    """Default strategy: call LLM, execute tool calls, repeat."""

    name = "tool_use"

    async def execute(self, ctx: LoopContext) -> AsyncGenerator[AgentEvent, None]:
        messages = ctx.messages
        provider: LLMProvider = ctx.provider
        tools: list[ToolDefinition] = ctx.tools
        max_steps: int = ctx.max_steps
        usage = TokenUsage()
        start = time.monotonic()
        content = ""

        for step in range(max_steps):
            if _is_aborted(ctx):
                yield ErrorEvent(error="Aborted", recoverable=False)
                return

            yield StepStartEvent(step=step, total_steps=max_steps)
            await _run_interceptors(ctx, step, "tool_use")

            params = CompletionParams(
                messages=messages, tools=tools,
                max_tokens=ctx.max_tokens, temperature=ctx.temperature,
            )

            text = ""
            tool_calls: list[ToolCall] = []
            try:
                if ctx.streaming:
                    async for chunk in provider.stream(params):
                        if chunk.text:
                            text += chunk.text
                            yield TextDeltaEvent(text=chunk.text)
                        if chunk.tool_call:
                            tool_calls.append(chunk.tool_call)
                else:
                    result = await provider.complete(params)
                    text = result.content
                    tool_calls = result.tool_calls
                    _accumulate_usage(usage, result.usage)
                    if text:
                        yield TextDeltaEvent(text=text)
            except Exception as e:
                yield ErrorEvent(error=str(e), recoverable=False)
                return

            content += text
            messages.append(AssistantMessage(content=text, tool_calls=tool_calls))

            if not tool_calls:
                yield StepEndEvent(step=step, reason="complete")
                dur = int((time.monotonic() - start) * 1000)
                yield DoneEvent(content=content, steps=step + 1, duration_ms=dur, usage=usage)
                return

            for tc in tool_calls:
                yield ToolCallStartEvent(tool_call_id=tc.id, name=tc.name)
                t0 = time.monotonic()
                result_str = await _exec_tool(tc, ctx)
                dur_ms = int((time.monotonic() - t0) * 1000)
                messages.append(ToolMessage(content=result_str, tool_call_id=tc.id))
                yield ToolCallEndEvent(tool_call_id=tc.id, result=result_str, duration_ms=dur_ms)

                if tc.name == "done":
                    yield StepEndEvent(step=step, reason="complete")
                    dur = int((time.monotonic() - start) * 1000)
                    yield DoneEvent(content=result_str, steps=step + 1, duration_ms=dur, usage=usage)
                    return

            yield StepEndEvent(step=step, reason="tool_use")

        dur = int((time.monotonic() - start) * 1000)
        yield ErrorEvent(error=f"Max steps ({max_steps}) reached", recoverable=False)
        yield DoneEvent(content=content, steps=max_steps, duration_ms=dur, usage=usage)


async def _exec_tool(tc: ToolCall, ctx: LoopContext) -> str:
    try:
        args = json.loads(tc.arguments)
    except (json.JSONDecodeError, TypeError):
        args = {}
    tool_ctx = ToolContext(
        agent_id=getattr(ctx, "agent_id", ""),
        session_id=getattr(ctx, "session_id", None),
        tenant_id=getattr(ctx, "tenant_id", None),
    )
    timeout_ms = getattr(ctx.tool_config, "timeout_ms", 30000) if ctx.tool_config else 30000
    registry = ctx.tool_registry
    return await asyncio.wait_for(
        registry.execute(tc, tool_ctx),
        timeout=timeout_ms / 1000,
    )


def _is_aborted(ctx: LoopContext) -> bool:
    sig = ctx.signal
    return bool(sig and (sig.is_set() if hasattr(sig, "is_set") else False))


async def _run_interceptors(ctx: LoopContext, step: int, strategy: str) -> None:
    chain = ctx.interceptors
    if chain and hasattr(chain, "run"):
        from .interceptor import InterceptorContext
        ictx = InterceptorContext(
            messages=ctx.messages,
            metadata={"step": step, "strategy": strategy},
        )
        await chain.run(ictx)


_REACT_SUFFIX = """
Use this format:
Thought: <reasoning about what to do>
Action: use a tool OR respond to the user
Observation: <tool result>
... (repeat until done)
Final Answer: <your response>"""


class ReactStrategy:
    """ReAct strategy: Thought → Action → Observation loop."""

    name = "react"

    async def execute(self, ctx: LoopContext) -> AsyncGenerator[AgentEvent, None]:
        messages = ctx.messages
        provider: LLMProvider = ctx.provider
        tools: list[ToolDefinition] = ctx.tools
        max_steps: int = ctx.max_steps
        usage = TokenUsage()
        start = time.monotonic()
        content = ""

        # Inject ReAct framing
        if messages and getattr(messages[0], "role", "") == "system":
            messages[0] = type(messages[0])(
                content=messages[0].content + _REACT_SUFFIX,
                role="system",
            )

        for step in range(max_steps):
            if _is_aborted(ctx):
                yield ErrorEvent(error="Aborted", recoverable=False)
                return

            yield StepStartEvent(step=step, total_steps=max_steps)
            await _run_interceptors(ctx, step, "react")

            params = CompletionParams(
                messages=messages, tools=tools,
                max_tokens=ctx.max_tokens, temperature=ctx.temperature,
            )

            try:
                result = await provider.complete(params)
                text = result.content
                tool_calls = result.tool_calls
                _accumulate_usage(usage, result.usage)
            except Exception as e:
                yield ErrorEvent(error=str(e), recoverable=False)
                return

            if text:
                content += text
                yield TextDeltaEvent(text=text)

            has_final = "Final Answer:" in text
            if has_final or not tool_calls:
                yield StepEndEvent(step=step, reason="complete")
                final = text.split("Final Answer:")[-1].strip() if has_final else content
                dur = int((time.monotonic() - start) * 1000)
                yield DoneEvent(content=final, steps=step + 1, duration_ms=dur, usage=usage)
                return

            messages.append(AssistantMessage(content=text, tool_calls=tool_calls))

            for tc in tool_calls:
                yield ToolCallStartEvent(tool_call_id=tc.id, name=tc.name)
                t0 = time.monotonic()
                try:
                    result_str = await _exec_tool(tc, ctx)
                except asyncio.TimeoutError:
                    result_str = f"Error: Tool timed out"
                dur_ms = int((time.monotonic() - t0) * 1000)
                messages.append(ToolMessage(
                    content=f"Observation: {result_str}", tool_call_id=tc.id,
                ))
                yield ToolCallEndEvent(tool_call_id=tc.id, result=result_str, duration_ms=dur_ms)

            yield StepEndEvent(step=step, reason="tool_use")

        dur = int((time.monotonic() - start) * 1000)
        yield ErrorEvent(error=f"Max steps ({max_steps}) reached", recoverable=False)
        yield DoneEvent(content=content, steps=max_steps, duration_ms=dur, usage=usage)
