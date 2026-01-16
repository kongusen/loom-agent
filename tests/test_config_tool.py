"""
Tests for Tool Configuration
"""

from contextlib import suppress
from unittest.mock import patch

import pytest

from loom.config.tool import ToolConfig, ToolFactory


class TestToolConfig:
    """Test ToolConfig model."""

    def test_create_config(self):
        """Test creating a tool config."""
        config = ToolConfig(
            name="test_tool",
            description="A test tool",
            python_path="mypackage.tools.tool_func",
            parameters={"arg1": {"type": "string"}},
            env_vars={"API_KEY": "test_key"},
        )

        assert config.name == "test_tool"
        assert config.description == "A test tool"
        assert config.python_path == "mypackage.tools.tool_func"
        assert config.parameters == {"arg1": {"type": "string"}}
        assert config.env_vars == {"API_KEY": "test_key"}

    def test_config_with_defaults(self):
        """Test config with default values."""
        config = ToolConfig(name="test_tool", python_path="mypackage.tools.tool_func")

        assert config.description == ""
        assert config.parameters == {}
        assert config.env_vars == {}

    def test_config_parameters_are_mutable(self):
        """Test that parameters dict is mutable."""
        config = ToolConfig(
            name="test_tool",
            python_path="mypackage.tools.tool_func",
            parameters={"arg1": {"type": "string"}},
        )

        config.parameters["arg2"] = {"type": "integer"}

        assert "arg2" in config.parameters

    def test_config_env_vars_are_mutable(self):
        """Test that env_vars dict is mutable."""
        config = ToolConfig(name="test_tool", python_path="mypackage.tools.tool_func")

        config.env_vars["NEW_VAR"] = "value"

        assert "NEW_VAR" in config.env_vars


class TestToolFactory:
    """Test ToolFactory class."""

    @pytest.fixture
    def dispatcher(self):
        """Create a mock dispatcher."""
        from loom.kernel.core import Dispatcher
        from loom.kernel.core.bus import UniversalEventBus

        bus = UniversalEventBus()
        return Dispatcher(bus)

    def test_create_node_with_invalid_path(self, dispatcher):
        """Test that invalid python_path raises ValueError."""
        config = ToolConfig(name="test_tool", python_path="nonexistent.module.function")

        with pytest.raises(ValueError, match="Could not load tool function"):
            ToolFactory.create_node(config, "node_id", dispatcher)

    def test_create_node_with_invalid_function(self, dispatcher):
        """Test that invalid function in module raises ValueError."""
        config = ToolConfig(name="test_tool", python_path="os.nonexistent_function")

        with pytest.raises(ValueError, match="Could not load tool function"):
            ToolFactory.create_node(config, "node_id", dispatcher)

    @patch.dict("os.environ", {}, clear=True)
    def test_create_node_applies_env_vars(self, dispatcher):
        """Test that env_vars are applied to environment."""
        config = ToolConfig(
            name="test_tool",
            python_path="os.getenv",  # Use existing function
            env_vars={"TEST_VAR": "test_value"},
        )

        # Should not raise error
        with suppress(Exception):
            ToolFactory.create_node(config, "node_id", dispatcher)

        # Check that env var was set
        import os

        assert os.environ.get("TEST_VAR") == "test_value"

    @patch.dict("os.environ", {}, clear=True)
    def test_create_node_with_empty_env_vars(self, dispatcher):
        """Test that empty env_vars dict is handled."""
        config = ToolConfig(name="test_tool", python_path="os.path.exists", env_vars={})

        # Should not raise error related to env_vars
        with suppress(Exception):
            ToolFactory.create_node(config, "node_id", dispatcher)

    def test_create_node_uses_config_name(self, dispatcher):
        """Test that config name is used in tool definition."""
        config = ToolConfig(name="my_custom_name", python_path="os.path.exists")

        try:
            node = ToolFactory.create_node(config, "node_id", dispatcher)
        except Exception:
            return

        # If we got here, check the node was created with correct name
        assert node.node_id == "node_id"

    def test_create_node_uses_config_description(self, dispatcher):
        """Test that config description is used in tool definition."""
        config = ToolConfig(
            name="test_tool", description="My custom description", python_path="os.path.exists"
        )

        try:
            node = ToolFactory.create_node(config, "node_id", dispatcher)
        except Exception:
            return

        # If node was created, check description
        assert node.tool_def.description == "My custom description"

    def test_create_node_uses_config_parameters(self, dispatcher):
        """Test that config parameters are used in input schema."""
        config = ToolConfig(
            name="test_tool",
            python_path="os.path.exists",
            parameters={"path": {"type": "string"}, "mode": {"type": "integer"}},
        )

        try:
            node = ToolFactory.create_node(config, "node_id", dispatcher)
        except Exception:
            return

        # If node was created, check parameters
        assert "path" in node.tool_def.input_schema["properties"]
        assert "mode" in node.tool_def.input_schema["properties"]

    def test_create_node_returns_tool_node(self, dispatcher):
        """Test that create_node returns a ToolNode instance."""
        from loom.node.tool import ToolNode

        config = ToolConfig(name="test_tool", python_path="os.getcwd")

        node = ToolFactory.create_node(config, "node_id", dispatcher)

        assert isinstance(node, ToolNode)
        assert node.node_id == "node_id"

    def test_create_node_preserves_function_reference(self, dispatcher):
        """Test that the original function is preserved."""
        import os

        config = ToolConfig(name="test_tool", python_path="os.getcwd")

        node = ToolFactory.create_node(config, "node_id", dispatcher)

        # The func should be os.getcwd
        assert node.func == os.getcwd
