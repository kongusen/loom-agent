"""Loop runner extracted from AgentEngine internals."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any

from ..runtime.loop import AgentLoop, LoopConfig
from ..types import LoopState, Message, ToolCall, ToolResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LoopTrace:
    """Internal trace event collected by non-streaming runs."""

    event: dict[str, Any]


@dataclass(slots=True)
class LoopStreamEvent:
    """Internal wrapper for user-visible streaming events."""

    event: Any


@dataclass(slots=True)
class LoopDone:
    """Internal terminal result emitted by the shared loop runner."""

    status: str
    output: str
    iterations: int


@dataclass(slots=True)
class RuntimeServices:
    """Explicit service boundary required by the shared L* loop."""

    context_manager: Any
    memory_runtime: Any
    max_iterations: Callable[[], int]
    set_current_iteration: Callable[[int], None]
    refresh_runtime_wiring: Callable[[], None]
    build_messages: Callable[[str], list[Message]]
    drain_signals: Callable[[], list[Any]]
    build_completion_request: Callable[[list[Message]], Any]
    stream_provider_request: Callable[[Any], AsyncGenerator[Any, None]]
    call_llm: Callable[[list[Message], Callable[[str], Any] | None], Any]
    parse_tool_calls: Callable[[dict[str, Any]], list[ToolCall]]
    execute_tools: Callable[[list[ToolCall]], Any]
    emit: Callable[..., int]


class LoopRunner:
    """Owns the shared L* loop for batch and streaming execution."""

    def __init__(
        self,
        *,
        services: RuntimeServices,
    ) -> None:
        self.services = services

    async def run_loop(
        self,
        goal: str,
        token_callback: Callable[[str], Any] | None = None,
    ) -> dict[str, Any]:
        """Run the L* execution loop and materialize a result dict."""
        events: list[dict[str, Any]] = []

        async for item in self.run_loop_core(
            goal,
            stream=False,
            token_callback=token_callback,
        ):
            if isinstance(item, LoopTrace):
                events.append(item.event)
            elif isinstance(item, LoopDone):
                return {
                    "status": item.status,
                    "output": item.output,
                    "events": events,
                    "iterations": item.iterations,
                }

        return {
            "status": "max_iterations",
            "output": "Max iterations reached",
            "events": events,
            "iterations": self.services.max_iterations(),
        }

    async def run_loop_core(
        self,
        goal: str,
        *,
        stream: bool,
        token_callback: Callable[[str], Any] | None = None,
    ) -> AsyncGenerator[Any, None]:
        loop = AgentLoop(
            LoopConfig(
                max_iterations=self.services.max_iterations(),
                rho_threshold=1.0,
            )
        )

        iteration = 0
        messages: list[Message] = self.services.build_messages(goal)

        def _append(msg: Message) -> None:
            messages.append(msg)
            self.services.context_manager.partitions.history.append(msg)

        while iteration < self.services.max_iterations():
            iteration += 1
            self.services.set_current_iteration(iteration)
            self.services.refresh_runtime_wiring()
            logger.debug("Loop iteration %s, state: %s", iteration, loop.state)

            if self.services.drain_signals():
                messages = self.services.build_messages(goal)
                yield LoopTrace({"type": "signals.ingested", "iteration": iteration})

            rho = self.services.context_manager.rho
            self.services.context_manager.dashboard.update_rho(rho)

            if self.services.context_manager.should_renew():
                logger.info("Context pressure ρ=1.0, renewing context")
                self.services.context_manager.renew()
                messages = self.services.build_messages(goal)
                self.services.emit("context_renewed", iteration=iteration)
                yield LoopTrace({"type": "context.renewed", "iteration": iteration})

            elif strategy := self.services.context_manager.should_compress():
                logger.info("Compressing context with strategy: %s", strategy)
                self.services.context_manager.compress(strategy)
                messages = self.services.build_messages(goal)
                self.services.emit(
                    "on_context_compact",
                    strategy=strategy,
                    iteration=iteration,
                    rho=self.services.context_manager.rho,
                )
                yield LoopTrace(
                    {
                        "type": "context.compressed",
                        "strategy": strategy,
                        "iteration": iteration,
                    }
                )

            if loop.state == LoopState.REASON:
                if stream:
                    from ..types.stream import ErrorEvent, TextDelta, ToolCallEvent

                    if self.services.drain_signals():
                        messages = self.services.build_messages(goal)
                    request = self.services.build_completion_request(messages)
                    text_parts: list[str] = []
                    tool_calls_seen: list[ToolCall] = []

                    try:
                        self.services.emit(
                            "before_llm",
                            request=request,
                            iteration=iteration,
                            stream=True,
                        )
                        async for event in self.services.stream_provider_request(request):
                            yield LoopStreamEvent(event)
                            if isinstance(event, TextDelta):
                                text_parts.append(event.delta)
                            elif isinstance(event, ToolCallEvent):
                                tool_calls_seen.append(
                                    ToolCall(
                                        id=event.id,
                                        name=event.name,
                                        arguments=event.arguments,
                                    )
                                )
                    except Exception as exc:
                        yield LoopStreamEvent(ErrorEvent(message=str(exc)))
                        self.services.emit(
                            "after_llm",
                            request=request,
                            response=None,
                            iteration=iteration,
                            stream=True,
                            error=exc,
                        )
                        return

                    response = {
                        "content": "".join(text_parts),
                        "tool_calls": tool_calls_seen,
                    }
                    self.services.emit(
                        "after_llm",
                        request=request,
                        response=response,
                        iteration=iteration,
                        stream=True,
                        error=None,
                    )
                else:
                    if self.services.drain_signals():
                        messages = self.services.build_messages(goal)
                    response = await self.services.call_llm(messages, token_callback)

                tool_calls = self.services.parse_tool_calls(response)

                if tool_calls:
                    content = str(response.get("content", "")).strip()
                    loop.state = LoopState.ACT
                    _append(Message(role="assistant", content=content, tool_calls=tool_calls))
                    yield LoopTrace(
                        {
                            "type": "tools.requested",
                            "count": len(tool_calls),
                            "iteration": iteration,
                        }
                    )
                else:
                    output = str(response.get("content", "")).strip()
                    _append(Message(role="assistant", content=output))
                    if output.lower().startswith("error:"):
                        yield LoopDone("provider_error", output, iteration)
                        return
                    yield LoopDone("success", output, iteration)
                    return

            elif loop.state == LoopState.ACT:
                last_message = messages[-1]
                tool_results: list[ToolResult] = await self.services.execute_tools(
                    last_message.tool_calls
                )
                if self.services.drain_signals():
                    messages = self.services.build_messages(goal)
                tool_names = {tool_call.id: tool_call.name for tool_call in last_message.tool_calls}

                error_count = 0
                for result in tool_results:
                    name = tool_names.get(result.tool_call_id)
                    if stream:
                        from ..types.stream import ToolResultEvent

                        content_str = (
                            result.content if isinstance(result.content, str) else str(result.content)
                        )
                        yield LoopStreamEvent(
                            ToolResultEvent(
                                tool_call_id=result.tool_call_id,
                                name=name or "",
                                content=content_str,
                                is_error=result.is_error,
                            )
                        )

                    _append(
                        Message(
                            role="tool",
                            content=result.content,
                            tool_call_id=result.tool_call_id,
                            name=name,
                        )
                    )
                    if result.is_error:
                        error_count += 1
                    else:
                        self.services.memory_runtime.remember_tool_result(
                            content=result.content,
                            tool_name=name,
                            iteration=iteration,
                        )

                if error_count:
                    for _ in range(error_count):
                        self.services.context_manager.dashboard.increment_errors()

                yield LoopTrace(
                    {
                        "type": "tools.executed",
                        "count": len(tool_results),
                        "iteration": iteration,
                    }
                )

                loop.state = LoopState.OBSERVE

            elif loop.state == LoopState.OBSERVE:
                loop.state = LoopState.DELTA

            elif loop.state == LoopState.DELTA:
                if self.services.context_manager.rho >= 0.9:
                    self.services.context_manager.renew()
                    messages = self.services.build_messages(goal)
                    self.services.emit("context_renewed", iteration=iteration)
                    yield LoopTrace({"type": "context.renewed", "iteration": iteration})
                loop.state = LoopState.REASON

        output = str(messages[-1].content) if messages else "Max iterations reached"
        yield LoopDone("max_iterations", output, iteration)
