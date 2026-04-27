"""Runtime delegation contracts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Protocol

from ..types import SubAgentResult


@dataclass(slots=True)
class DelegationRequest:
    """One subtask request sent from runtime to a delegation policy."""

    goal: str
    depth: int = 0
    inherit_context: bool = True
    timeout: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DelegationResult:
    """Normalized result returned by a runtime delegation policy."""

    success: bool
    output: Any
    depth: int
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_subagent_result(
        cls,
        result: SubAgentResult,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> DelegationResult:
        return cls(
            success=result.success,
            output=result.output,
            depth=result.depth,
            error=result.error,
            metadata=dict(metadata or {}),
        )

    def to_subagent_result(self) -> SubAgentResult:
        return SubAgentResult(
            success=self.success,
            output=self.output,
            depth=self.depth,
            error=self.error,
        )


class RuntimeDelegationPolicy(Protocol):
    """Protocol implemented by delegation policies."""

    async def delegate(self, request: DelegationRequest) -> DelegationResult: ...

    async def delegate_many(
        self,
        requests: list[DelegationRequest],
    ) -> list[DelegationResult]: ...


class DelegationPolicy:
    """Factory for built-in runtime delegation policies."""

    @staticmethod
    def none() -> NoopDelegationPolicy:
        return NoopDelegationPolicy()

    @staticmethod
    def subagents(manager: Any) -> SubAgentDelegationPolicy:
        return SubAgentDelegationPolicy(manager)

    @staticmethod
    def local(parent: Any, *, max_depth: int = 5) -> RuntimeDelegationPolicy:
        from ..orchestration.subagent import SubAgentManager

        return SubAgentManager(parent=parent, max_depth=max_depth)

    @staticmethod
    def depth_limited(
        max_depth: int,
        delegate: RuntimeDelegationPolicy | None = None,
    ) -> DepthLimitedDelegationPolicy:
        return DepthLimitedDelegationPolicy(
            max_depth=max_depth,
            delegate=delegate or NoopDelegationPolicy(),
        )


class NoopDelegationPolicy:
    """Delegation policy used when no sub-agent backend is configured."""

    async def delegate(self, request: DelegationRequest) -> DelegationResult:
        return DelegationResult(
            success=False,
            output="",
            depth=request.depth,
            error="NO_DELEGATION_TARGET",
            metadata={"policy": "none"},
        )

    async def delegate_many(
        self,
        requests: list[DelegationRequest],
    ) -> list[DelegationResult]:
        return [await self.delegate(request) for request in requests]


class SubAgentDelegationPolicy:
    """Adapter for existing SubAgentManager-like objects."""

    def __init__(self, manager: Any) -> None:
        self.manager = manager

    async def delegate(self, request: DelegationRequest) -> DelegationResult:
        spawn = getattr(self.manager, "spawn", None)
        if not callable(spawn):
            raise TypeError("Sub-agent delegation manager must provide spawn()")

        coro = spawn(
            request.goal,
            depth=request.depth,
            inherit_context=request.inherit_context,
        )
        if request.timeout is not None:
            result = await asyncio.wait_for(coro, timeout=request.timeout)
        else:
            result = await coro
        return _coerce_result(result, request)

    async def delegate_many(
        self,
        requests: list[DelegationRequest],
    ) -> list[DelegationResult]:
        spawn_many = getattr(self.manager, "spawn_many", None)
        if callable(spawn_many) and all(request.timeout is None for request in requests):
            raw_results = await spawn_many(
                [request.goal for request in requests],
                depth=requests[0].depth if requests else 0,
                inherit_context=requests[0].inherit_context if requests else True,
            )
            return [
                _coerce_result(result, request)
                for result, request in zip(raw_results, requests, strict=True)
            ]
        return [await self.delegate(request) for request in requests]


class DepthLimitedDelegationPolicy:
    """Guard a delegation policy with a recursion depth limit."""

    def __init__(
        self,
        *,
        max_depth: int,
        delegate: RuntimeDelegationPolicy,
    ) -> None:
        self.max_depth = max_depth
        self.delegate_policy = delegate

    async def delegate(self, request: DelegationRequest) -> DelegationResult:
        if request.depth >= self.max_depth:
            return DelegationResult(
                success=False,
                output="Max depth reached - 能力边界已穷尽",
                depth=request.depth,
                error="MAX_DEPTH_EXCEEDED",
                metadata={"policy": "depth_limited", "max_depth": self.max_depth},
            )
        return await self.delegate_policy.delegate(request)

    async def delegate_many(
        self,
        requests: list[DelegationRequest],
    ) -> list[DelegationResult]:
        return [await self.delegate(request) for request in requests]


def _coerce_result(result: Any, request: DelegationRequest) -> DelegationResult:
    if isinstance(result, DelegationResult):
        return result
    if isinstance(result, SubAgentResult):
        return DelegationResult.from_subagent_result(result)
    return DelegationResult(
        success=True,
        output=getattr(result, "output", result),
        depth=request.depth + 1,
    )
