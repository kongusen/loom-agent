"""工具注册表"""

from ..schema import Tool


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具"""
        self.tools[tool.definition.name] = tool

    def get(self, name: str) -> Tool | None:
        """获取工具"""
        return self.tools.get(name)

    def list_tools(self) -> list[str]:
        """列出所有工具"""
        return list(self.tools.keys())


_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """获取全局注册表"""
    return _registry
