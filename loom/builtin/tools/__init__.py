"""
Loom Builtin Tools - 工具构建能力

提供工具构建能力，而非预设工具：
- @tool: 装饰器，将函数转换为工具
- ToolBuilder: 工具构建器，流式 API
- MCP 兼容（待实现）
"""

from loom.builtin.tools.builder import tool, ToolBuilder

__all__ = [
    "tool",
    "ToolBuilder",
]
