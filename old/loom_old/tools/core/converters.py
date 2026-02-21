"""
Tool Converters - 工具转换器

将Python函数转换为MCP工具定义。
"""

import inspect
from collections.abc import Callable
from typing import Any, get_type_hints

from loom.tools.mcp_types import MCPToolDefinition


class FunctionToMCP:
    """
    将Python函数转换为MCP工具定义

    使用inspect模块解析函数签名，自动生成工具定义。
    """

    @staticmethod
    def convert(func: Callable[..., Any], name: str | None = None) -> MCPToolDefinition:
        """
        将Python函数转换为MCP工具定义

        Args:
            func: Python函数
            name: 工具名称（可选，默认使用函数名）

        Returns:
            MCP工具定义
        """
        func_name = name or func.__name__
        doc = inspect.getdoc(func) or "No description provided."

        # 解析函数签名
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            # 跳过self和cls参数
            if param_name in ("self", "cls"):
                continue

            # 获取参数类型
            py_type = type_hints.get(param_name, Any)
            json_type = FunctionToMCP._map_type(py_type)

            properties[param_name] = {"type": json_type}

            # 判断是否必需参数
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        input_schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        return MCPToolDefinition(
            name=func_name,
            description=doc,
            input_schema=input_schema,
        )

    @staticmethod
    def to_openai_format(func: Callable[..., Any], name: str | None = None) -> dict[str, Any]:
        """
        将Python函数直接转换为OpenAI工具格式

        Args:
            func: Python函数
            name: 工具名称（可选，默认使用函数名）

        Returns:
            OpenAI格式的工具定义 dict
        """
        mcp_def = FunctionToMCP.convert(func, name)
        return {
            "type": "function",
            "function": {
                "name": mcp_def.name,
                "description": mcp_def.description,
                "parameters": mcp_def.input_schema,
            },
        }

    @staticmethod
    def _map_type(py_type: type) -> str:
        """
        将Python类型映射到JSON Schema类型

        Args:
            py_type: Python类型

        Returns:
            JSON Schema类型字符串
        """
        if py_type is str:
            return "string"
        elif py_type is int:
            return "integer"
        elif py_type is float:
            return "number"
        elif py_type is bool:
            return "boolean"
        elif py_type is list or getattr(py_type, "__origin__", None) is list:
            return "array"
        elif py_type is dict or getattr(py_type, "__origin__", None) is dict:
            return "object"
        else:
            return "string"  # 默认降级为string
