"""
Tool Registry - 工具注册表

管理可用工具的中央仓库。
"""

from collections.abc import Callable

from loom.protocol.mcp import MCPToolDefinition
from loom.tools.converters import FunctionToMCP


class ToolRegistry:
    """
    工具注册表

    管理所有可用工具的定义和可调用对象。
    """

    def __init__(self):
        """初始化工具注册表"""
        self._tools: dict[str, Callable] = {}
        self._definitions: dict[str, MCPToolDefinition] = {}

    def register_function(self, func: Callable, name: str | None = None) -> MCPToolDefinition:
        """
        注册Python函数为工具

        Args:
            func: Python函数
            name: 工具名称（可选，默认使用函数名）

        Returns:
            MCP工具定义
        """
        # 获取工具名称
        tool_name = name or func.__name__

        # 转换为MCP定义
        definition = FunctionToMCP.convert(func, name=tool_name)

        # 存储
        self._tools[tool_name] = func
        self._definitions[tool_name] = definition

        return definition

    def get_definition(self, name: str) -> MCPToolDefinition | None:
        """
        获取工具定义

        Args:
            name: 工具名称

        Returns:
            工具定义，如果不存在则返回None
        """
        return self._definitions.get(name)

    def get_callable(self, name: str) -> Callable | None:
        """
        获取工具的可调用对象

        Args:
            name: 工具名称

        Returns:
            可调用对象，如果不存在则返回None
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """
        检查工具是否存在

        Args:
            name: 工具名称

        Returns:
            是否存在
        """
        return name in self._tools

    @property
    def definitions(self) -> list[MCPToolDefinition]:
        """
        获取所有工具定义

        Returns:
            工具定义列表
        """
        return list(self._definitions.values())

    @property
    def tool_names(self) -> list[str]:
        """
        获取所有工具名称

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())
