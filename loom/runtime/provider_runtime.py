"""Provider coordination runtime extracted from AgentEngine internals."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Callable
from typing import Any

from ..providers.base import CompletionParams, CompletionRequest, LLMProvider
from ..types import Message

logger = logging.getLogger(__name__)


class ProviderRuntime:
    """Owns provider request construction and provider call dispatch."""

    def __init__(
        self,
        *,
        provider: Any,
        config: Any,
        context_manager: Any,
        emit: Callable[..., int],
        current_iteration: Callable[[], int],
        build_provider_tools: Callable[[], list[Any]],
    ) -> None:
        self.provider = provider
        self.config = config
        self.context_manager = context_manager
        self.emit = emit
        self.current_iteration = current_iteration
        self.build_provider_tools = build_provider_tools

    def to_provider_messages(self, messages: list[Message]) -> list[dict[str, Any]]:
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.name,
                        "arguments": tc.arguments,
                    }
                    for tc in msg.tool_calls
                ],
                "tool_call_id": msg.tool_call_id,
                "name": msg.name,
            }
            for msg in messages
        ]

    async def call_llm(
        self,
        messages: list[Message],
        token_callback: Callable[[str], Any] | None = None,
    ) -> dict[str, Any]:
        request = self.build_completion_request(messages)
        self.emit(
            "before_llm",
            request=request,
            iteration=self.current_iteration(),
            stream=token_callback is not None,
        )

        try:
            if token_callback is not None:
                response = await self.complete_provider_request_streaming(request, token_callback)
            else:
                response = await self.complete_provider_request(request)
            self.emit(
                "after_llm",
                request=request,
                response=response,
                iteration=self.current_iteration(),
                stream=token_callback is not None,
                error=None,
            )
            return {
                "content": response.content,
                "tool_calls": response.tool_calls,
                "usage": response.usage,
            }
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            self.emit(
                "after_llm",
                request=request,
                response=None,
                iteration=self.current_iteration(),
                stream=token_callback is not None,
                error=exc,
            )
            return {"content": f"Error: {exc}"}

    async def complete_provider_request(self, request: CompletionRequest) -> Any:
        return await self.provider.complete_request(request)

    async def complete_provider_request_streaming(
        self,
        request: CompletionRequest,
        token_callback: Callable[[str], Any],
    ) -> Any:
        if isinstance(self.provider, LLMProvider):
            return await self.provider.complete_request_streaming(request, token_callback)
        if hasattr(self.provider, "complete_request_streaming"):
            return await self.provider.complete_request_streaming(request, token_callback)
        response = await self.provider.complete_request(request)
        if getattr(response, "content", ""):
            token_callback(response.content)
        return response

    async def stream_provider_request(
        self,
        request: CompletionRequest,
    ) -> AsyncGenerator[Any, None]:
        if isinstance(self.provider, LLMProvider):
            async for event in self.provider.stream_request_events(request):
                yield event
            return
        if hasattr(self.provider, "stream_request_events"):
            async for event in self.provider.stream_request_events(request):
                yield event
            return
        raise TypeError("provider must implement stream_request_events(request)")

    def build_completion_params(self) -> CompletionParams:
        return CompletionParams(
            model=self.config.model,
            max_tokens=self.config.completion_max_tokens,
            temperature=self.config.temperature,
            tools=self.build_provider_tools(),
            extensions=dict(self.config.extensions),
        )

    def build_completion_request(self, messages: list[Message]) -> CompletionRequest:
        provider_messages = self.to_provider_messages(messages)
        params = self.build_completion_params()
        return CompletionRequest.create(
            provider_messages,
            params,
            metadata={
                "goal": self.context_manager.current_goal,
                "iteration": self.current_iteration(),
                "tool_count": len(params.tools),
            },
        )
