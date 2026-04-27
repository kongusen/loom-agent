"""Tool declaration adapters for public Agent tools."""

from __future__ import annotations

from typing import Any

from ..config import ToolSpec
from ..tools.base import Tool, ToolMetadata


def _tool_spec_to_tool(spec: ToolSpec) -> Tool:
    metadata = ToolMetadata(
        name=spec.name,
        description=spec.description,
        is_read_only=spec.read_only,
        is_destructive=spec.destructive,
        is_concurrency_safe=spec.concurrency_safe,
        requires_permission=spec.requires_permission,
    )
    schema = spec.to_input_schema()

    class DeclaredTool(Tool):
        def __init__(self) -> None:
            super().__init__(metadata)
            self._schema = schema
            self._handler = spec.handler

        def call(self, **kwargs: Any) -> dict[str, Any]:
            if self._handler is None:
                raise RuntimeError(f"Tool '{spec.name}' does not have a local handler")
            result = self._handler.invoke(**kwargs)
            return {"result": result}

        def input_schema(self) -> dict[str, Any]:
            return self._schema

    return DeclaredTool()


def _compile_tool_spec(spec: ToolSpec) -> Tool:
    return _tool_spec_to_tool(spec)
