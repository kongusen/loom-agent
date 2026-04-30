"""Agent factory and public tool decorator."""

from __future__ import annotations

from collections.abc import Callable

from ..config import ToolSpec


def tool(
    func: Callable | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    read_only: bool = False,
    destructive: bool = False,
    concurrency_safe: bool = False,
    requires_permission: bool | None = None,
) -> ToolSpec | Callable[[Callable], ToolSpec]:
    """Build a stable ToolSpec from a Python function."""

    def decorator(inner: Callable) -> ToolSpec:
        return ToolSpec.from_function(
            inner,
            name=name,
            description=description,
            read_only=read_only,
            destructive=destructive,
            concurrency_safe=concurrency_safe,
            requires_permission=requires_permission,
        )

    if func is not None:
        return decorator(func)
    return decorator
