"""
工具构建器 - 提供创建工具的能力

特性：
1. @tool 装饰器 - 将函数转换为工具
2. ToolBuilder - 工具构建器类
3. 自动生成 schema
"""

from __future__ import annotations
from typing import Callable, Optional, Any, get_type_hints, List
import inspect
from functools import wraps


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Callable:
    """
    工具装饰器 - 将函数转换为工具

    使用方式：
    ```python
    from loom.builtin.tools import tool
    import loom

    @tool(name="calculator", description="Perform calculations")
    async def calculator(expression: str) -> float:
        '''Calculate mathematical expression'''
        return eval(expression)

    # 自动转换为 BaseTool
    agent = loom.agent(name="assistant", llm="openai", api_key="...", tools=[calculator])
    ```

    特性：
    - 自动从函数签名生成 schema
    - 支持类型提示
    - 支持文档字符串
    - 支持同步和异步函数

    Args:
        name: 工具名称（可选，默认使用函数名）
        description: 工具描述（可选，默认使用文档字符串）

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> "FunctionTool":
        # 获取函数信息
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or "No description"

        # 获取参数类型
        type_hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}
        sig = inspect.signature(func)

        # 生成 schema
        parameters = {"type": "object", "properties": {}, "required": []}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = type_hints.get(param_name, str)
            json_type = _python_type_to_json_type(param_type)

            parameters["properties"][param_name] = {
                "type": json_type,
                "description": f"Parameter {param_name}",
            }

            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)

        # 创建工具类
        class FunctionTool:
            """动态生成的工具类"""

            def __init__(self):
                self.name = tool_name
                self.description = tool_desc
                self._func = func
                self._parameters = parameters

            async def execute(self, **kwargs) -> Any:
                """执行工具"""
                if inspect.iscoroutinefunction(func):
                    return await func(**kwargs)
                else:
                    return func(**kwargs)

            def to_schema(self) -> dict:
                """转换为 OpenAI function calling schema"""
                return {
                    "type": "function",
                    "function": {
                        "name": self.name,
                        "description": self.description,
                        "parameters": self._parameters,
                    },
                }

            def __repr__(self) -> str:
                return f"Tool(name='{self.name}')"

        return FunctionTool()

    return decorator


def _python_type_to_json_type(py_type) -> str:
    """将 Python 类型转换为 JSON schema 类型"""
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        List: "array",
    }

    # 处理泛型（如 List[str]）
    origin = getattr(py_type, "__origin__", None)
    if origin:
        return type_map.get(origin, "string")

    return type_map.get(py_type, "string")


class ToolBuilder:
    """
    工具构建器 - 更灵活的工具创建方式

    使用方式：
    ```python
    from loom.builtin.tools import ToolBuilder

    tool = (
        ToolBuilder("web_search")
        .description("Search the web")
        .parameter("query", "string", "Search query")
        .parameter("limit", "integer", "Result limit", default=10)
        .execute(async_search_function)
        .build()
    )
    ```
    """

    def __init__(self, name: str):
        """
        初始化工具构建器

        Args:
            name: 工具名称
        """
        self.name = name
        self._description = ""
        self._parameters = {"type": "object", "properties": {}, "required": []}
        self._execute_func = None

    def description(self, desc: str) -> "ToolBuilder":
        """
        设置描述

        Args:
            desc: 工具描述

        Returns:
            self（支持链式调用）
        """
        self._description = desc
        return self

    def parameter(
        self,
        name: str,
        param_type: str,
        description: str,
        required: bool = True,
        default: Any = None,
    ) -> "ToolBuilder":
        """
        添加参数

        Args:
            name: 参数名
            param_type: 参数类型（"string", "integer", "number", "boolean", "array", "object"）
            description: 参数描述
            required: 是否必需
            default: 默认值

        Returns:
            self（支持链式调用）
        """
        self._parameters["properties"][name] = {
            "type": param_type,
            "description": description,
        }

        if default is not None:
            self._parameters["properties"][name]["default"] = default

        if required and default is None:
            self._parameters["required"].append(name)

        return self

    def execute(self, func: Callable) -> "ToolBuilder":
        """
        设置执行函数

        Args:
            func: 执行函数（同步或异步）

        Returns:
            self（支持链式调用）
        """
        self._execute_func = func
        return self

    def build(self) -> "CustomTool":
        """
        构建工具

        Returns:
            构建好的工具实例

        Raises:
            ValueError: 如果执行函数未设置
        """
        if not self._execute_func:
            raise ValueError("Execute function not set. Use .execute(func) first.")

        class CustomTool:
            def __init__(self, name, description, parameters, execute_func):
                self.name = name
                self.description = description
                self._parameters = parameters
                self._execute_func = execute_func

            async def execute(self, **kwargs) -> Any:
                if inspect.iscoroutinefunction(self._execute_func):
                    return await self._execute_func(**kwargs)
                else:
                    return self._execute_func(**kwargs)

            def to_schema(self) -> dict:
                return {
                    "type": "function",
                    "function": {
                        "name": self.name,
                        "description": self.description,
                        "parameters": self._parameters,
                    },
                }

            def __repr__(self) -> str:
                return f"Tool(name='{self.name}')"

        return CustomTool(
            self.name, self._description, self._parameters, self._execute_func
        )
