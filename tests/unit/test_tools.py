"""
Tools Module Unit Tests

测试工具模块的核心功能
"""

import pytest

from loom.tools.core.converters import FunctionToMCP
from loom.tools.core.registry import ToolRegistry
from loom.tools.mcp_types import MCPToolDefinition


class TestToolRegistry:
    """测试工具注册表"""

    def test_init(self):
        """测试初始化"""
        registry = ToolRegistry()
        assert len(registry._tools) == 0
        assert len(registry._definitions) == 0
        assert registry.tool_names == []
        assert registry.definitions == []

    def test_register_function(self):
        """测试注册函数"""
        registry = ToolRegistry()

        def sample_tool(x: int, y: int) -> int:
            """Add two numbers"""
            return x + y

        definition = registry.register_function(sample_tool)

        assert isinstance(definition, MCPToolDefinition)
        assert definition.name == "sample_tool"
        assert "sample_tool" in registry.tool_names
        assert len(registry.definitions) == 1

    def test_register_function_with_custom_name(self):
        """测试使用自定义名称注册函数"""
        registry = ToolRegistry()

        def my_func(x: int) -> int:
            """Test function"""
            return x * 2

        definition = registry.register_function(my_func, name="custom_name")

        assert definition.name == "custom_name"
        assert "custom_name" in registry.tool_names
        assert "my_func" not in registry.tool_names

    def test_get_definition(self):
        """测试获取工具定义"""
        registry = ToolRegistry()

        def tool1(x: int) -> int:
            """Tool 1"""
            return x

        registry.register_function(tool1)

        definition = registry.get_definition("tool1")
        assert definition is not None
        assert definition.name == "tool1"

        # 获取不存在的工具
        none_def = registry.get_definition("nonexistent")
        assert none_def is None

    def test_get_callable(self):
        """测试获取可调用对象"""
        registry = ToolRegistry()

        def tool1(x: int) -> int:
            """Tool 1"""
            return x + 1

        registry.register_function(tool1)

        callable_obj = registry.get_callable("tool1")
        assert callable_obj is not None
        assert callable_obj(5) == 6

        # 获取不存在的工具
        none_callable = registry.get_callable("nonexistent")
        assert none_callable is None

    def test_multiple_tools(self):
        """测试注册多个工具"""
        registry = ToolRegistry()

        def tool1(x: int) -> int:
            return x

        def tool2(y: str) -> str:
            return y

        def tool3(z: float) -> float:
            return z

        registry.register_function(tool1)
        registry.register_function(tool2)
        registry.register_function(tool3)

        assert len(registry.tool_names) == 3
        assert len(registry.definitions) == 3
        assert "tool1" in registry.tool_names
        assert "tool2" in registry.tool_names
        assert "tool3" in registry.tool_names


class TestFunctionToMCP:
    """测试函数到MCP转换器"""

    def test_convert_simple_function(self):
        """测试转换简单函数"""

        def add(x: int, y: int) -> int:
            """Add two numbers"""
            return x + y

        definition = FunctionToMCP.convert(add)

        assert definition.name == "add"
        assert definition.description == "Add two numbers"
        assert "properties" in definition.input_schema
        assert "x" in definition.input_schema["properties"]
        assert "y" in definition.input_schema["properties"]
        assert definition.input_schema["properties"]["x"]["type"] == "integer"
        assert definition.input_schema["properties"]["y"]["type"] == "integer"

    def test_convert_with_custom_name(self):
        """测试使用自定义名称转换"""

        def my_func(x: int) -> int:
            """Test function"""
            return x

        definition = FunctionToMCP.convert(my_func, name="custom_tool")

        assert definition.name == "custom_tool"

    def test_convert_function_without_docstring(self):
        """测试转换没有文档字符串的函数"""

        def no_doc(x: int) -> int:
            return x

        definition = FunctionToMCP.convert(no_doc)

        assert definition.description == "No description provided."

    def test_convert_required_parameters(self):
        """测试必需参数识别"""

        def func_with_required(a: int, b: str) -> str:
            """Function with required params"""
            return f"{a}{b}"

        definition = FunctionToMCP.convert(func_with_required)

        assert "required" in definition.input_schema
        assert "a" in definition.input_schema["required"]
        assert "b" in definition.input_schema["required"]
        assert len(definition.input_schema["required"]) == 2

    def test_convert_optional_parameters(self):
        """测试可选参数识别"""

        def func_with_optional(a: int, b: str = "default") -> str:
            """Function with optional params"""
            return f"{a}{b}"

        definition = FunctionToMCP.convert(func_with_optional)

        assert "required" in definition.input_schema
        assert "a" in definition.input_schema["required"]
        assert "b" not in definition.input_schema["required"]
        assert len(definition.input_schema["required"]) == 1

    def test_type_mapping_string(self):
        """测试字符串类型映射"""
        assert FunctionToMCP._map_type(str) == "string"

    def test_type_mapping_integer(self):
        """测试整数类型映射"""
        assert FunctionToMCP._map_type(int) == "integer"

    def test_type_mapping_float(self):
        """测试浮点数类型映射"""
        assert FunctionToMCP._map_type(float) == "number"

    def test_type_mapping_boolean(self):
        """测试布尔类型映射"""
        assert FunctionToMCP._map_type(bool) == "boolean"

    def test_type_mapping_list(self):
        """测试列表类型映射"""
        assert FunctionToMCP._map_type(list) == "array"

    def test_type_mapping_dict(self):
        """测试字典类型映射"""
        assert FunctionToMCP._map_type(dict) == "object"

    def test_type_mapping_unknown(self):
        """测试未知类型映射（降级为string）"""

        class CustomType:
            pass

        assert FunctionToMCP._map_type(CustomType) == "string"


class TestToolExecutor:
    """测试工具执行引擎"""

    def test_init(self):
        """测试初始化"""
        from loom.tools.core.executor import ToolExecutor

        executor = ToolExecutor()
        assert executor.parallel_execution is True

        executor_no_parallel = ToolExecutor(parallel_execution=False)
        assert executor_no_parallel.parallel_execution is False

    def test_is_read_only(self):
        """测试只读工具判断"""
        from loom.tools.core.executor import ToolExecutor

        executor = ToolExecutor()

        # 只读工具
        assert executor.is_read_only("read_file") is True
        assert executor.is_read_only("get_data") is True
        assert executor.is_read_only("list_items") is True
        assert executor.is_read_only("search_database") is True
        assert executor.is_read_only("query_api") is True
        assert executor.is_read_only("fetch_content") is True

        # 写入工具
        assert executor.is_read_only("write_file") is False
        assert executor.is_read_only("update_data") is False
        assert executor.is_read_only("delete_item") is False
        assert executor.is_read_only("create_record") is False

    @pytest.mark.asyncio
    async def test_execute_batch_empty(self):
        """测试执行空批次"""
        from loom.tools.core.executor import ToolExecutor

        executor = ToolExecutor()

        async def dummy_executor(name: str, args: dict):
            return "result"

        results = await executor.execute_batch([], dummy_executor)
        assert results == []

    @pytest.mark.asyncio
    async def test_execute_batch_single_tool(self):
        """测试执行单个工具"""
        from loom.tools.core.executor import ToolExecutor

        executor = ToolExecutor()

        async def dummy_executor(name: str, args: dict):
            return f"executed {name}"

        tool_calls = [{"name": "read_file", "arguments": {"path": "/test"}}]

        results = await executor.execute_batch(tool_calls, dummy_executor)

        assert len(results) == 1
        assert results[0].name == "read_file"
        assert results[0].result == "executed read_file"
        assert results[0].error is False

    @pytest.mark.asyncio
    async def test_execute_batch_parallel_read_only(self):
        """测试并行执行只读工具"""
        from loom.tools.core.executor import ToolExecutor

        executor = ToolExecutor(parallel_execution=True)

        async def dummy_executor(name: str, args: dict):
            return f"executed {name}"

        # 多个只读工具应该并行执行
        tool_calls = [
            {"name": "read_file", "arguments": {"path": "/test1"}},
            {"name": "get_data", "arguments": {"id": "123"}},
            {"name": "list_items", "arguments": {}},
        ]

        results = await executor.execute_batch(tool_calls, dummy_executor)

        assert len(results) == 3
        assert results[0].name == "read_file"
        assert results[1].name == "get_data"
        assert results[2].name == "list_items"
        assert all(not r.error for r in results)

    @pytest.mark.asyncio
    async def test_execute_batch_serial_write_tools(self):
        """测试串行执行写入工具"""
        from loom.tools.core.executor import ToolExecutor

        executor = ToolExecutor(parallel_execution=True)

        execution_order = []

        async def tracking_executor(name: str, args: dict):
            execution_order.append(name)
            return f"executed {name}"

        # 写入工具应该串行执行
        tool_calls = [
            {"name": "write_file", "arguments": {"path": "/test1"}},
            {"name": "update_data", "arguments": {"id": "123"}},
            {"name": "delete_item", "arguments": {"id": "456"}},
        ]

        results = await executor.execute_batch(tool_calls, tracking_executor)

        assert len(results) == 3
        assert execution_order == ["write_file", "update_data", "delete_item"]

    @pytest.mark.asyncio
    async def test_execute_batch_mixed_tools(self):
        """测试混合执行只读和写入工具"""
        from loom.tools.core.executor import ToolExecutor

        executor = ToolExecutor(parallel_execution=True)

        async def dummy_executor(name: str, args: dict):
            return f"executed {name}"

        # 混合只读和写入工具
        tool_calls = [
            {"name": "read_file", "arguments": {}},
            {"name": "get_data", "arguments": {}},
            {"name": "write_file", "arguments": {}},  # 写入工具会打断并行
            {"name": "list_items", "arguments": {}},
        ]

        results = await executor.execute_batch(tool_calls, dummy_executor)

        assert len(results) == 4
        assert results[0].name == "read_file"
        assert results[1].name == "get_data"
        assert results[2].name == "write_file"
        assert results[3].name == "list_items"

    @pytest.mark.asyncio
    async def test_execute_batch_with_error(self):
        """测试执行时的错误处理"""
        from loom.tools.core.executor import ToolExecutor

        executor = ToolExecutor()

        async def failing_executor(name: str, args: dict):
            if name == "failing_tool":
                raise ValueError("Tool execution failed")
            return f"executed {name}"

        tool_calls = [
            {"name": "read_file", "arguments": {}},
            {"name": "failing_tool", "arguments": {}},
            {"name": "get_data", "arguments": {}},
        ]

        results = await executor.execute_batch(tool_calls, failing_executor)

        assert len(results) == 3
        assert results[0].error is False
        assert results[1].error is True
        assert "Tool execution failed" in results[1].result
        assert results[2].error is False

    @pytest.mark.asyncio
    async def test_execute_batch_no_parallel(self):
        """测试禁用并行执行"""
        from loom.tools.core.executor import ToolExecutor

        executor = ToolExecutor(parallel_execution=False)

        execution_order = []

        async def tracking_executor(name: str, args: dict):
            execution_order.append(name)
            return f"executed {name}"

        # 即使是只读工具，也应该串行执行
        tool_calls = [
            {"name": "read_file", "arguments": {}},
            {"name": "get_data", "arguments": {}},
            {"name": "list_items", "arguments": {}},
        ]

        results = await executor.execute_batch(tool_calls, tracking_executor)

        assert len(results) == 3
        assert execution_order == ["read_file", "get_data", "list_items"]
