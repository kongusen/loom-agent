"""Tool registry"""

from .schema import Tool, ToolDefinition


class ToolRegistry:
    """Manage tool registration and lookup"""

    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool"""
        self.tools[tool.definition.name] = tool

    def get(self, name: str) -> Tool | None:
        """Get tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        """List all tool definitions"""
        return [tool.definition for tool in self.tools.values()]

    def list(self) -> list[Tool]:
        """List registered tool implementations."""
        return list(self.tools.values())

    def unregister(self, name: str):
        """Unregister a tool"""
        self.tools.pop(name, None)
