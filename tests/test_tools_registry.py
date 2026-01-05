"""
Tests for Tool Registry

Tests the ToolRegistry class which manages tool definitions and callables.
"""

import pytest
from typing import Optional

from loom.tools.registry import ToolRegistry
from loom.protocol.mcp import MCPToolDefinition


class TestToolRegistry:
    """Test ToolRegistry functionality."""

    def test_initialization(self):
        """Test registry initialization."""
        registry = ToolRegistry()
        assert registry._tools == {}
        assert registry._definitions == {}

    def test_register_function_with_name(self):
        """Test registering a function with custom name."""
        def sample_func(x: int) -> str:
            return f"result: {x}"

        registry = ToolRegistry()
        definition = registry.register_function(sample_func, name="custom_name")

        assert definition.name == "custom_name"
        assert "custom_name" in registry._tools
        assert "custom_name" in registry._definitions

    def test_register_function_without_name(self):
        """Test registering a function without custom name."""
        def my_tool(x: int) -> str:
            return f"result: {x}"

        registry = ToolRegistry()
        definition = registry.register_function(my_tool)

        assert definition.name == "my_tool"
        assert "my_tool" in registry._tools

    def test_register_function_stores_callable(self):
        """Test that the callable is stored."""
        def my_tool(x: int) -> str:
            return f"result: {x}"

        registry = ToolRegistry()
        registry.register_function(my_tool)

        callable = registry.get_callable("my_tool")
        assert callable is my_tool

    def test_get_definition(self):
        """Test getting tool definition."""
        def my_tool(x: int) -> str:
            return f"result: {x}"

        registry = ToolRegistry()
        definition = registry.register_function(my_tool)

        retrieved = registry.get_definition("my_tool")
        assert retrieved is definition
        assert retrieved.name == "my_tool"

    def test_get_definition_nonexistent(self):
        """Test getting definition for non-existent tool."""
        registry = ToolRegistry()
        definition = registry.get_definition("nonexistent")
        assert definition is None

    def test_get_callable_nonexistent(self):
        """Test getting callable for non-existent tool."""
        registry = ToolRegistry()
        callable = registry.get_callable("nonexistent")
        assert callable is None

    def test_definitions_property(self):
        """Test getting all definitions."""
        def tool1(x: int) -> str:
            return f"result: {x}"

        def tool2(y: str) -> str:
            return f"result: {y}"

        registry = ToolRegistry()
        registry.register_function(tool1)
        registry.register_function(tool2)

        definitions = registry.definitions
        assert len(definitions) == 2
        assert all(isinstance(d, MCPToolDefinition) for d in definitions)

    def test_register_multiple_functions(self):
        """Test registering multiple functions."""
        def tool_a(x: int) -> int:
            return x * 2

        def tool_b(y: str) -> str:
            return y.upper()

        registry = ToolRegistry()
        registry.register_function(tool_a)
        registry.register_function(tool_b)

        assert len(registry._tools) == 2
        assert len(registry._definitions) == 2

    def test_overwrite_existing_function(self):
        """Test that registering same name overwrites."""
        def tool_v1(x: int) -> int:
            return x

        def tool_v2(x: int) -> int:
            return x * 2

        registry = ToolRegistry()
        registry.register_function(tool_v1, name="tool")
        registry.register_function(tool_v2, name="tool")

        callable = registry.get_callable("tool")
        assert callable is tool_v2

    def test_function_with_no_args(self):
        """Test registering function with no arguments."""
        def no_args_tool() -> str:
            return "done"

        registry = ToolRegistry()
        definition = registry.register_function(no_args_tool)

        assert definition.name == "no_args_tool"
        # Should have no required params
        assert definition.input_schema["required"] == []

    def test_function_with_optional_args(self):
        """Test registering function with optional arguments."""
        def optional_tool(x: int, y: str = "default") -> str:
            return f"{x}: {y}"

        registry = ToolRegistry()
        definition = registry.register_function(optional_tool)

        # Only x should be required
        assert definition.input_schema["required"] == ["x"]
        assert "y" in definition.input_schema["properties"]

    def test_function_with_multiple_types(self):
        """Test registering function with various parameter types."""
        def complex_tool(
            name: str,
            count: int,
            price: float,
            active: bool,
            items: list
        ) -> dict:
            return {"result": "ok"}

        registry = ToolRegistry()
        definition = registry.register_function(complex_tool)

        props = definition.input_schema["properties"]
        assert props["name"]["type"] == "string"
        assert props["count"]["type"] == "integer"
        assert props["price"]["type"] == "number"
        assert props["active"]["type"] == "boolean"
        assert props["items"]["type"] == "array"

    def test_get_callable_and_definition_are_consistent(self):
        """Test that callable and definition match."""
        def my_tool(x: int) -> str:
            return f"result: {x}"

        registry = ToolRegistry()
        registry.register_function(my_tool)

        callable = registry.get_callable("my_tool")
        definition = registry.get_definition("my_tool")

        assert callable is not None
        assert definition is not None
        assert definition.name == "my_tool"
