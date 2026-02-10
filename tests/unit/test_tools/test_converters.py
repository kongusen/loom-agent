"""
Tests for Tool Converters

测试将函数转换为MCP工具定义的功能
"""

from loom.tools.mcp_types import MCPToolDefinition
from loom.tools.core.converters import FunctionToMCP


class TestFunctionToMCPConvert:
    """测试 FunctionToMCP.convert 方法"""

    def test_convert_simple_function(self):
        """测试转换简单函数"""

        def my_tool(name: str, count: int) -> str:
            """A simple test tool"""
            return f"{name}: {count}"

        result = FunctionToMCP.convert(my_tool)

        assert isinstance(result, MCPToolDefinition)
        assert result.name == "my_tool"
        assert result.description == "A simple test tool"
        assert result.input_schema["type"] == "object"
        assert "name" in result.input_schema["properties"]
        assert "count" in result.input_schema["properties"]
        assert result.input_schema["properties"]["name"]["type"] == "string"
        assert result.input_schema["properties"]["count"]["type"] == "integer"
        assert "name" in result.input_schema["required"]
        assert "count" in result.input_schema["required"]

    def test_convert_with_custom_name(self):
        """测试使用自定义名称转换"""

        def my_tool(value: str) -> str:
            """A tool"""
            return value

        result = FunctionToMCP.convert(my_tool, name="custom_name")

        assert result.name == "custom_name"

    def test_convert_function_with_self_parameter(self):
        """测试转换带self参数的函数（实例方法）"""

        class MyClass:
            def my_method(self, name: str, count: int) -> str:
                """An instance method tool"""
                return f"{name}: {count}"

        # 使用未绑定的方法来触发line 46的continue分支
        result = FunctionToMCP.convert(MyClass.my_method)

        assert result.name == "my_method"
        # self 参数应该被跳过，只包含 name 和 count
        assert "name" in result.input_schema["properties"]
        assert "count" in result.input_schema["properties"]
        assert "self" not in result.input_schema["properties"]
        assert len(result.input_schema["properties"]) == 2

    def test_convert_function_with_cls_parameter(self):
        """测试转换带cls参数的函数（类方法）"""

        class MyClass:
            @classmethod
            def my_class_method(cls, name: str, value: int) -> str:
                """A class method tool"""
                return f"{name}: {value}"

        result = FunctionToMCP.convert(MyClass.my_class_method)

        assert result.name == "my_class_method"
        # cls 参数应该被跳过
        assert "name" in result.input_schema["properties"]
        assert "value" in result.input_schema["properties"]
        assert "cls" not in result.input_schema["properties"]
        assert len(result.input_schema["properties"]) == 2

    def test_convert_function_with_default_parameters(self):
        """测试转换带默认参数的函数"""

        def my_tool(name: str, count: int = 10) -> str:
            """A tool with defaults"""
            return f"{name}: {count}"

        result = FunctionToMCP.convert(my_tool)

        # name 是必需的，count 有默认值所以不是必需的
        assert "name" in result.input_schema["required"]
        assert "count" not in result.input_schema["required"]

    def test_convert_function_with_no_docstring(self):
        """测试转换没有文档字符串的函数"""

        def my_tool(value: str) -> str:
            return value

        result = FunctionToMCP.convert(my_tool)

        assert result.description == "No description provided."

    def test_convert_function_with_all_types(self):
        """测试转换包含所有类型的函数"""

        def my_tool(
            name: str,
            count: int,
            price: float,
            active: bool,
            items: list,
            metadata: dict,
        ) -> str:
            """A tool with all types"""
            return "done"

        result = FunctionToMCP.convert(my_tool)

        assert result.input_schema["properties"]["name"]["type"] == "string"
        assert result.input_schema["properties"]["count"]["type"] == "integer"
        assert result.input_schema["properties"]["price"]["type"] == "number"
        assert result.input_schema["properties"]["active"]["type"] == "boolean"
        assert result.input_schema["properties"]["items"]["type"] == "array"
        assert result.input_schema["properties"]["metadata"]["type"] == "object"

    def test_convert_function_with_optional_only(self):
        """测试转换只有可选参数的函数"""

        def my_tool(name: str = "default", count: int = 0) -> str:
            """A tool with only optional params"""
            return f"{name}: {count}"

        result = FunctionToMCP.convert(my_tool)

        assert len(result.input_schema["required"]) == 0

    def test_convert_function_no_parameters(self):
        """测试转换无参数函数"""

        def my_tool() -> str:
            """A tool with no parameters"""
            return "done"

        result = FunctionToMCP.convert(my_tool)

        assert len(result.input_schema["properties"]) == 0
        assert len(result.input_schema["required"]) == 0


class TestFunctionToMCPMapType:
    """测试 FunctionToMCP._map_type 方法"""

    def test_map_string_type(self):
        """测试映射字符串类型"""
        assert FunctionToMCP._map_type(str) == "string"

    def test_map_int_type(self):
        """测试映射整数类型"""
        assert FunctionToMCP._map_type(int) == "integer"

    def test_map_float_type(self):
        """测试映射浮点类型"""
        assert FunctionToMCP._map_type(float) == "number"

    def test_map_bool_type(self):
        """测试映射布尔类型"""
        assert FunctionToMCP._map_type(bool) == "boolean"

    def test_map_list_type(self):
        """测试映射列表类型"""
        assert FunctionToMCP._map_type(list) == "array"

    def test_map_dict_type(self):
        """测试映射字典类型"""
        assert FunctionToMCP._map_type(dict) == "object"

    def test_map_unknown_type_defaults_to_string(self):
        """测试未知类型默认映射为字符串"""

        class CustomType:
            pass

        assert FunctionToMCP._map_type(CustomType) == "string"

    def test_map_generic_list(self):
        """测试映射泛型列表类型"""

        assert FunctionToMCP._map_type(list[str]) == "array"

    def test_map_generic_dict(self):
        """测试映射泛型字典类型"""

        assert FunctionToMCP._map_type(dict[str, int]) == "object"


class TestFunctionToMCPIntegration:
    """集成测试"""

    def test_convert_class_instance_method_full_workflow(self):
        """测试完整的类实例方法转换流程"""

        class ToolClass:
            def __init__(self, prefix: str):
                self.prefix = prefix

            def process(self, text: str, repeat: int = 1) -> str:
                """Process text with prefix"""
                return f"{self.prefix}: {text * repeat}"

        instance = ToolClass(prefix="RESULT")
        result = FunctionToMCP.convert(instance.process)

        # 验证 self 被正确跳过
        assert result.name == "process"
        assert "text" in result.input_schema["properties"]
        assert "repeat" in result.input_schema["properties"]
        assert "self" not in result.input_schema["properties"]
        assert result.input_schema["properties"]["text"]["type"] == "string"
        assert result.input_schema["properties"]["repeat"]["type"] == "integer"
        assert "text" in result.input_schema["required"]
        assert "repeat" not in result.input_schema["required"]

    def test_convert_class_method_full_workflow(self):
        """测试完整的类方法转换流程"""

        class ToolClass:
            @classmethod
            def create(cls, name: str, value: int) -> str:
                """Create something"""
                return f"Created {name} with value {value}"

        result = FunctionToMCP.convert(ToolClass.create)

        # 验证 cls 被正确跳过
        assert result.name == "create"
        assert "name" in result.input_schema["properties"]
        assert "value" in result.input_schema["properties"]
        assert "cls" not in result.input_schema["properties"]
        assert len(result.input_schema["required"]) == 2
