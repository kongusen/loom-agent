"""Builtin tools - 使用正确的 schema"""

from .tools_registry import BUILTIN_TOOLS, register_all_tools
from .registry import get_registry


def get_builtin_tool(name: str):
    """Get a builtin tool by name

    Args:
        name: Tool name

    Returns:
        Tool instance or None if not found
    """
    for tool in BUILTIN_TOOLS:
        if tool.definition.name == name:
            return tool
    return None


__all__ = ["BUILTIN_TOOLS", "register_all_tools", "get_registry", "get_builtin_tool"]
