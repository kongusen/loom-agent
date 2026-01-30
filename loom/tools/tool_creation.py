"""
Tool Creation - Dynamic tool creation capability

Allows agents to create new tools at runtime using Python code.
This extends the Tool Use paradigm with Tool Creation capability.
"""

import inspect
from collections.abc import Callable
from typing import Any


def create_tool_creation_tool() -> dict[str, Any]:
    """
    Create the tool_creation meta-tool definition

    This tool allows agents to define new tools dynamically by providing:
    - Tool name
    - Description
    - Parameters schema
    - Python implementation code

    Returns:
        Tool definition dict
    """
    return {
        "type": "function",
        "function": {
            "name": "create_tool",
            "description": (
                "Create a new tool dynamically. "
                "Define the tool's name, description, parameters, and Python implementation. "
                "The tool will be available for use in subsequent iterations. "
                "Use this when you need capabilities beyond existing tools."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_name": {
                        "type": "string",
                        "description": "Name of the new tool (snake_case)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Clear description of what the tool does",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "JSON schema for tool parameters",
                    },
                    "implementation": {
                        "type": "string",
                        "description": (
                            "Python function implementation. "
                            "Must define an async function with the same name as tool_name. "
                            "Example: async def my_tool(param1: str) -> str: ..."
                        ),
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this tool is needed",
                    },
                },
                "required": ["tool_name", "description", "parameters", "implementation"],
            },
        },
    }


class ToolCreationError(Exception):
    """Raised when tool creation fails"""

    pass


class DynamicToolExecutor:
    """Executes dynamically created tools in a controlled environment"""

    def __init__(self):
        self.created_tools: dict[str, Callable] = {}
        self.tool_definitions: dict[str, dict[str, Any]] = {}

    def validate_tool_code(self, tool_name: str, code: str) -> None:
        """
        Validate tool implementation code

        Args:
            tool_name: Name of the tool
            code: Python code to validate

        Raises:
            ToolCreationError: If code is invalid or unsafe
        """
        # Basic safety checks
        forbidden_keywords = [
            "import os",
            "import sys",
            "import subprocess",
            "__import__",
            "eval(",
            "exec(",
            "compile(",
            "open(",
            "file(",
        ]

        for keyword in forbidden_keywords:
            if keyword in code:
                raise ToolCreationError(
                    f"Forbidden keyword '{keyword}' found in tool implementation. "
                    f"Tool code must be safe and cannot access system resources directly."
                )

        # Check that code defines the expected function
        if f"async def {tool_name}" not in code and f"def {tool_name}" not in code:
            raise ToolCreationError(
                f"Tool implementation must define a function named '{tool_name}'"
            )

    async def create_tool(
        self,
        tool_name: str,
        description: str,
        parameters: dict[str, Any],
        implementation: str,
    ) -> str:
        """
        Create a new tool dynamically

        Args:
            tool_name: Name of the tool
            description: Tool description
            parameters: Parameter schema
            implementation: Python code implementing the tool

        Returns:
            Success message

        Raises:
            ToolCreationError: If tool creation fails
        """
        # Validate tool code
        self.validate_tool_code(tool_name, implementation)

        # Create execution namespace
        namespace: dict[str, Any] = {
            "__builtins__": {
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "len": len,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "reversed": reversed,
                "any": any,
                "all": all,
                "print": print,
            }
        }

        # Execute code to define the function
        try:
            exec(implementation, namespace)
        except Exception as e:
            raise ToolCreationError(f"Failed to execute tool code: {str(e)}") from e

        # Extract the function
        if tool_name not in namespace:
            raise ToolCreationError(f"Function '{tool_name}' not found in implementation")

        tool_func = namespace[tool_name]

        # Validate function signature
        if not callable(tool_func):
            raise ToolCreationError(f"'{tool_name}' is not callable")

        # Store the tool
        self.created_tools[tool_name] = tool_func
        self.tool_definitions[tool_name] = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": description,
                "parameters": parameters,
            },
        }

        return (
            f"Tool '{tool_name}' created successfully. You can now use it in subsequent iterations."
        )

    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a dynamically created tool

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ToolCreationError: If tool not found or execution fails
        """
        if tool_name not in self.created_tools:
            raise ToolCreationError(f"Tool '{tool_name}' not found")

        tool_func = self.created_tools[tool_name]

        try:
            # Check if function is async
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(**kwargs)
            else:
                result = tool_func(**kwargs)
            return result
        except Exception as e:
            raise ToolCreationError(f"Tool execution failed: {str(e)}") from e

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get all dynamically created tool definitions"""
        return list(self.tool_definitions.values())
