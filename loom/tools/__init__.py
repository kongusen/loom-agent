"""Tool registry and define_tool helper."""

from __future__ import annotations

import inspect
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from ..types import ToolCall, ToolContext, ToolDefinition, ToolExecutionConfig
from .builtin import delegate_tool, done_tool
from .mcp_client import McpClient, McpServerConfig, McpToolInfo, mcp_tools_to_definitions
from .schema import DictSchema, PydanticSchema
from .skill_tool import create_skill_tool
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
    "create_skill_tool",
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

    async def execute(
        self,
        call: ToolCall,
        ctx: ToolContext | None = None,
        config: ToolExecutionConfig | None = None,
        constraint_validator: Any = None,
    ) -> str:
        import asyncio
        import time

        # P0: 约束前置验证
        if constraint_validator:
            is_valid, error_msg = constraint_validator.validate_before_call(call)
            if not is_valid:
                return json.dumps({"error": error_msg})

        tool = self._tools.get(call.name)
        if not tool:
            return json.dumps({"error": f"Tool '{call.name}' not found"})

        ctx = ctx or ToolContext(agent_id="")
        config = config or ToolExecutionConfig()
        _start = time.monotonic()  # Track execution start time

        try:
            args = json.loads(call.arguments) if isinstance(call.arguments, str) else call.arguments
            parsed = tool.parameters.parse(args)
            result = tool.execute(parsed, ctx)

            if inspect.isawaitable(result):
                result = await asyncio.wait_for(result, timeout=config.timeout_ms / 1000)

            output = json.dumps(result) if not isinstance(result, str) else result

            # Check result size
            if len(output.encode()) > config.max_result_bytes:
                return json.dumps({"error": "Result too large"})

            return output

        except TimeoutError:
            logger.warning("Tool timeout: %s (%.2fs)", call.name, config.timeout_ms / 1000)
            return json.dumps({"error": f"Tool timeout after {config.timeout_ms}ms"})
        except Exception as e:
            logger.exception("Tool execution error: %s", call.name)
            return json.dumps({"error": str(e)})
