"""Interceptor chain — middleware pipeline for message transformation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

from ..types import Message


@dataclass
class InterceptorContext:
    messages: list[Message]
    metadata: dict[str, Any] = field(default_factory=dict)


Next = Callable[[], Awaitable[None]]


@runtime_checkable
class Interceptor(Protocol):
    name: str
    async def intercept(self, ctx: InterceptorContext, next: Next) -> None: ...


class InterceptorChain:
    def __init__(self) -> None:
        self._interceptors: list[Interceptor] = []

    def use(self, interceptor: Interceptor) -> None:
        self._interceptors.append(interceptor)

    async def run(self, ctx: InterceptorContext) -> None:
        async def dispatch(i: int) -> None:
            if i >= len(self._interceptors):
                return
            await self._interceptors[i].intercept(ctx, lambda: dispatch(i + 1))
        await dispatch(0)
