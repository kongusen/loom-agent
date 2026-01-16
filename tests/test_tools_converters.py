"""
Tests for Tool Converters

Tests the FunctionToMCP class which converts Python functions to MCP definitions.
"""

from loom.protocol.mcp import MCPToolDefinition
from loom.tools.converters import FunctionToMCP


class TestFunctionToMCP:
    """Test FunctionToMCP functionality."""

    def test_convert_basic_function(self):
        """Test converting a basic function."""

        def my_tool(x: int) -> str:
            return f"result: {x}"

        definition = FunctionToMCP.convert(my_tool)

        assert isinstance(definition, MCPToolDefinition)
        assert definition.name == "my_tool"
        assert definition.input_schema["type"] == "object"

    def test_convert_with_custom_name(self):
        """Test converting with custom name."""

        def my_tool(x: int) -> str:
            return f"result: {x}"

        definition = FunctionToMCP.convert(my_tool, name="custom_name")

        assert definition.name == "custom_name"

    def test_convert_with_docstring(self):
        """Test that docstring is captured."""

        def documented_tool(x: int) -> str:
            """This is a test tool."""
            return f"result: {x}"

        definition = FunctionToMCP.convert(documented_tool)

        assert definition.description == "This is a test tool."

    def test_convert_without_docstring(self):
        """Test function without docstring."""

        def undocumented_tool(x: int) -> str:
            return f"result: {x}"

        definition = FunctionToMCP.convert(undocumented_tool)

        assert definition.description == "No description provided."

    def test_convert_string_param(self):
        """Test string parameter type mapping."""

        def string_tool(name: str) -> str:
            return f"Hello {name}"

        definition = FunctionToMCP.convert(string_tool)

        props = definition.input_schema["properties"]
        assert props["name"]["type"] == "string"
        assert "name" in definition.input_schema["required"]

    def test_convert_int_param(self):
        """Test integer parameter type mapping."""

        def int_tool(count: int) -> int:
            return count * 2

        definition = FunctionToMCP.convert(int_tool)

        props = definition.input_schema["properties"]
        assert props["count"]["type"] == "integer"

    def test_convert_float_param(self):
        """Test float parameter type mapping."""

        def float_tool(price: float) -> float:
            return price * 1.1

        definition = FunctionToMCP.convert(float_tool)

        props = definition.input_schema["properties"]
        assert props["price"]["type"] == "number"

    def test_convert_bool_param(self):
        """Test boolean parameter type mapping."""

        def bool_tool(active: bool) -> bool:
            return not active

        definition = FunctionToMCP.convert(bool_tool)

        props = definition.input_schema["properties"]
        assert props["active"]["type"] == "boolean"

    def test_convert_list_param(self):
        """Test list parameter type mapping."""

        def list_tool(items: list) -> int:
            return len(items)

        definition = FunctionToMCP.convert(list_tool)

        props = definition.input_schema["properties"]
        assert props["items"]["type"] == "array"

    def test_convert_dict_param(self):
        """Test dict parameter type mapping."""

        def dict_tool(data: dict) -> int:
            return len(data)

        definition = FunctionToMCP.convert(dict_tool)

        props = definition.input_schema["properties"]
        assert props["data"]["type"] == "object"

    def test_convert_optional_param(self):
        """Test optional parameter is not required."""

        def optional_tool(x: int, y: str = "default") -> str:
            return f"{x}: {y}"

        definition = FunctionToMCP.convert(optional_tool)

        assert "x" in definition.input_schema["required"]
        assert "y" not in definition.input_schema["required"]
        assert "y" in definition.input_schema["properties"]

    def test_convert_multiple_params(self):
        """Test function with multiple parameters."""

        def multi_tool(name: str, count: int, active: bool) -> dict:
            return {"name": name, "count": count, "active": active}

        definition = FunctionToMCP.convert(multi_tool)

        required = definition.input_schema["required"]
        assert len(required) == 3
        assert set(required) == {"name", "count", "active"}

    def test_convert_with_no_params(self):
        """Test function with no parameters."""

        def no_params_tool() -> str:
            return "done"

        definition = FunctionToMCP.convert(no_params_tool)

        assert len(definition.input_schema["properties"]) == 0
        assert len(definition.input_schema["required"]) == 0

    def test_skips_self_param(self):
        """Test that 'self' parameter is skipped."""

        class MyClass:
            def method_tool(self, x: int) -> int:
                return x * 2

        obj = MyClass()
        definition = FunctionToMCP.convert(obj.method_tool)

        # 'self' should not be in properties
        assert "self" not in definition.input_schema["properties"]
        assert "x" in definition.input_schema["properties"]

    def test_skips_cls_param(self):
        """Test that 'cls' parameter is skipped."""

        class MyClass:
            @classmethod
            def classmethod_tool(cls, x: int) -> int:
                return x * 3

        definition = FunctionToMCP.convert(MyClass.classmethod_tool)

        # 'cls' should not be in properties
        assert "cls" not in definition.input_schema["properties"]
        assert "x" in definition.input_schema["properties"]

    def test_unknown_type_defaults_to_string(self):
        """Test that unknown types default to string."""
        from typing import Any

        def any_tool(x: Any) -> str:
            return str(x)

        definition = FunctionToMCP.convert(any_tool)

        props = definition.input_schema["properties"]
        assert props["x"]["type"] == "string"

    def test_map_type_string(self):
        """Test _map_type for string."""
        assert FunctionToMCP._map_type(str) == "string"

    def test_map_type_int(self):
        """Test _map_type for int."""
        assert FunctionToMCP._map_type(int) == "integer"

    def test_map_type_float(self):
        """Test _map_type for float."""
        assert FunctionToMCP._map_type(float) == "number"

    def test_map_type_bool(self):
        """Test _map_type for bool."""
        assert FunctionToMCP._map_type(bool) == "boolean"

    def test_map_type_list(self):
        """Test _map_type for list."""
        assert FunctionToMCP._map_type(list) == "array"

    def test_map_type_dict(self):
        """Test _map_type for dict."""
        assert FunctionToMCP._map_type(dict) == "object"

    def test_map_type_unknown(self):
        """Test _map_type for unknown type."""

        class CustomType:
            pass

        assert FunctionToMCP._map_type(CustomType) == "string"

    def test_input_schema_structure(self):
        """Test that input_schema has correct structure."""

        def schema_tool(name: str, count: int = 0) -> str:
            return f"{name}: {count}"

        definition = FunctionToMCP.convert(schema_tool)

        schema = definition.input_schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert isinstance(schema["properties"], dict)
        assert isinstance(schema["required"], list)
