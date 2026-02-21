"""Tool registry and define_tool helper."""

from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from ..types import ToolCall, ToolContext, ToolDefinition
from .builtin import delegate_tool, done_tool
from .mcp_client import McpClient, McpServerConfig, McpToolInfo, mcp_tools_to_definitions
from .schema import DictSchema, PydanticSchema
from .system import list_dir_tool, read_file_tool, shell_tool, write_file_tool

__all__ = [
    "define_tool",
    "ToolRegistry",
    "delegate_tool",
    "done_tool",
    "McpClient",
    "McpServerConfig",
    "McpToolInfo",
    "mcp_tools_to_definitions",
    "DictSchema",
    "PydanticSchema",
    "list_dir_tool",
    "read_file_tool",
    "shell_tool",
    "write_file_tool",
]

logger = logging.getLogger(__name__)


def define_tool(
    name: str,
    description: str,
    parameters: type[BaseModel] | PydanticSchema,
    execute: Callable[..., Awaitable[Any]],
) -> ToolDefinition:
    schema = parameters if isinstance(parameters, PydanticSchema) else PydanticSchema(parameters)
    return ToolDefinition(name=name, description=description, parameters=schema, execute=execute)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    async def execute(self, call: ToolCall, ctx: ToolContext | None = None) -> str:
        tool = self._tools.get(call.name)
        if not tool:
            return json.dumps({"error": f"Tool '{call.name}' not found"})
        ctx = ctx or ToolContext(agent_id="")
        try:
            args = json.loads(call.arguments) if isinstance(call.arguments, str) else call.arguments
            parsed = tool.parameters.parse(args)
            result = tool.execute(parsed, ctx)
            if inspect.isawaitable(result):
                result = await result
            return json.dumps(result) if not isinstance(result, str) else result
        except Exception as e:
            logger.exception("Tool execution error: %s", call.name)
            return json.dumps({"error": str(e)})
