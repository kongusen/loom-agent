"""
Tool Converters (M4)
"""

import inspect
from collections.abc import Callable
from typing import Any, get_type_hints

from loom.protocol.mcp import MCPToolDefinition


class FunctionToMCP:
    """
    Converts Python functions to MCP Tool Definitions.
    """

    @staticmethod
    def convert(func: Callable[..., Any], name: str | None = None) -> MCPToolDefinition:
        """
        Introspects a python function and returns an MCP Tool Definition.
        """
        func_name = name or func.__name__
        doc = inspect.getdoc(func) or "No description provided."

        # Parse arguments
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "self" or param_name == "cls":
                continue

            # Get type
            py_type = type_hints.get(param_name, Any)
            json_type = FunctionToMCP._map_type(py_type)

            prop_def = {"type": json_type}

            # TODO: Description from docstring parsing? (Google-style/NumPy-style)
            # For now, just basic type.

            properties[param_name] = prop_def

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        input_schema = {
            "type": "object",
            "properties": properties,
            "required": required
        }

        return MCPToolDefinition(
            name=func_name,
            description=doc,
            input_schema=input_schema
        )

    @staticmethod
    def _map_type(py_type: type) -> str:
        """Map Python type to JSON Schema type."""
        if py_type == str:
            return "string"
        elif py_type == int:
            return "integer"
        elif py_type == float:
            return "number"
        elif py_type == bool:
            return "boolean"
        elif py_type == list or getattr(py_type, "__origin__", None) == list:
            return "array"
        elif py_type == dict or getattr(py_type, "__origin__", None) == dict:
            return "object"
        else:
            return "string" # Default fallback
