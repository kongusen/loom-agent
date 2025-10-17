from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel, create_model

from .interfaces.tool import BaseTool


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    args_schema: Optional[Type[BaseModel]] = None,
    *,
    concurrency_safe: bool = True,
) -> Callable[[Callable[..., Any]], Type[BaseTool]]:
    """Decorator to turn a Python function into a Loom Tool.

    Example:
        @tool()
        def add(a: int, b: int) -> int:
            # Add two integers
            return a + b

        AddTool = add  # class deriving BaseTool
        my_tool = AddTool()
    """

    def wrapper(fn: Callable[..., Any]) -> Type[BaseTool]:
        tool_name = name or fn.__name__
        tool_desc = description or (inspect.getdoc(fn) or tool_name)
        schema = args_schema or _infer_args_schema(fn, tool_name)
        is_async = inspect.iscoroutinefunction(fn)

        class _FuncTool(BaseTool):  # type: ignore[override]
            name = tool_name
            description = tool_desc
            args_schema = schema

            async def run(self, **kwargs) -> Any:  # type: ignore[override]
                if is_async:
                    return await fn(**kwargs)  # type: ignore[misc]
                # Best-effort: offload to default executor to avoid blocking
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, lambda: fn(**kwargs))

            @property
            def is_concurrency_safe(self) -> bool:  # type: ignore[override]
                return concurrency_safe

        _FuncTool.__name__ = f"{tool_name.capitalize()}Tool"
        return _FuncTool

    return wrapper


def _infer_args_schema(fn: Callable[..., Any], tool_name: str) -> Type[BaseModel]:
    sig = inspect.signature(fn)
    fields = {}
    for name, param in sig.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        annotation = param.annotation if param.annotation is not inspect._empty else Any
        default = ... if param.default is inspect._empty else param.default
        fields[name] = (annotation, default)
    if not fields:
        # no-arg tool
        return create_model(f"{tool_name}_Args", __base__=BaseModel)  # type: ignore
    return create_model(f"{tool_name}_Args", __base__=BaseModel, **fields)  # type: ignore

