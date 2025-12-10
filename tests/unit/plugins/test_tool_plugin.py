"""
Unit tests for Tool Plugin System

Tests cover:
- ToolPluginMetadata creation and validation
- ToolPlugin creation and lifecycle
- ToolPluginRegistry operations
- ToolPluginLoader file loading
- ToolPluginManager high-level API
"""

import pytest
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool
from loom.plugins import (
    ToolPluginMetadata,
    ToolPlugin,
    ToolPluginRegistry,
    ToolPluginLoader,
    ToolPluginManager,
    PluginStatus,
)


# Test fixtures
class DummyToolInput(BaseModel):
    """Dummy tool input for testing"""
    value: str = Field(..., description="Test value")


class DummyTool(BaseTool):
    """Dummy tool for testing"""
    name = "dummy_tool"
    description = "A dummy tool for testing"
    args_schema = DummyToolInput

    async def run(self, value: str, **kwargs) -> str:
        return f"Result: {value}"


class AnotherDummyTool(BaseTool):
    """Another dummy tool for testing"""
    name = "another_tool"
    description = "Another dummy tool"
    args_schema = DummyToolInput

    async def run(self, value: str, **kwargs) -> str:
        return f"Another result: {value}"


# ============================================================================
# Test ToolPluginMetadata
# ============================================================================

class TestToolPluginMetadata:
    """Tests for ToolPluginMetadata"""

    def test_metadata_creation_minimal(self):
        """Test creating metadata with minimal fields"""
        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test Author",
            description="Test description"
        )

        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"
        assert metadata.description == "Test description"
        assert metadata.license == "MIT"  # default
        assert metadata.dependencies == []
        assert metadata.tags == []

    def test_metadata_creation_full(self):
        """Test creating metadata with all fields"""
        metadata = ToolPluginMetadata(
            name="full-plugin",
            version="2.1.3",
            author="Full Author <full@example.com>",
            description="Full description",
            homepage="https://example.com/plugin",
            license="Apache-2.0",
            dependencies=["requests>=2.28.0"],
            loom_min_version="0.2.0",
            tags=["test", "demo"],
            tool_names=["tool1", "tool2"]
        )

        assert metadata.name == "full-plugin"
        assert metadata.version == "2.1.3"
        assert metadata.homepage == "https://example.com/plugin"
        assert metadata.license == "Apache-2.0"
        assert len(metadata.dependencies) == 1
        assert len(metadata.tags) == 2
        assert len(metadata.tool_names) == 2

    def test_metadata_invalid_name_raises(self):
        """Test that invalid name format raises ValueError"""
        with pytest.raises(ValueError, match="Invalid plugin name"):
            ToolPluginMetadata(
                name="Invalid_Name",  # Underscore not allowed
                version="1.0.0",
                author="Test",
                description="Test"
            )

        with pytest.raises(ValueError, match="Invalid plugin name"):
            ToolPluginMetadata(
                name="InvalidName",  # Must be lowercase-with-dashes
                version="1.0.0",
                author="Test",
                description="Test"
            )

    def test_metadata_invalid_version_raises(self):
        """Test that invalid version format raises ValueError"""
        with pytest.raises(ValueError, match="Invalid version"):
            ToolPluginMetadata(
                name="test-plugin",
                version="1.0",  # Missing patch version
                author="Test",
                description="Test"
            )

    def test_metadata_to_dict(self):
        """Test conversion to dictionary"""
        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test",
            tags=["test"]
        )

        data = metadata.to_dict()

        assert isinstance(data, dict)
        assert data["name"] == "test-plugin"
        assert data["version"] == "1.0.0"
        assert "tags" in data

    def test_metadata_from_dict(self):
        """Test creation from dictionary"""
        data = {
            "name": "test-plugin",
            "version": "1.0.0",
            "author": "Test",
            "description": "Test"
        }

        metadata = ToolPluginMetadata.from_dict(data)

        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"

    def test_metadata_json_serialization(self):
        """Test JSON serialization/deserialization"""
        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )

        # Serialize
        json_str = metadata.to_json()
        assert isinstance(json_str, str)
        assert "test-plugin" in json_str

        # Deserialize
        metadata2 = ToolPluginMetadata.from_json(json_str)
        assert metadata2.name == metadata.name
        assert metadata2.version == metadata.version


# ============================================================================
# Test ToolPlugin
# ============================================================================

class TestToolPlugin:
    """Tests for ToolPlugin"""

    def test_plugin_creation(self):
        """Test creating plugin"""
        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )

        plugin = ToolPlugin(
            tool_class=DummyTool,
            metadata=metadata
        )

        assert plugin.tool_class == DummyTool
        assert plugin.metadata == metadata
        assert plugin.status == PluginStatus.LOADED
        assert "dummy_tool" in plugin.metadata.tool_names

    def test_plugin_invalid_tool_class_raises(self):
        """Test that invalid tool class raises ValueError"""
        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )

        # Not a BaseTool subclass
        with pytest.raises(ValueError, match="must inherit from BaseTool"):
            ToolPlugin(
                tool_class=str,  # type: ignore
                metadata=metadata
            )

    @pytest.mark.asyncio
    async def test_plugin_create_tool(self):
        """Test creating tool instance from plugin"""
        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )

        plugin = ToolPlugin(
            tool_class=DummyTool,
            metadata=metadata
        )

        # Enable plugin
        plugin.enable()

        # Create tool
        tool = plugin.create_tool()
        assert isinstance(tool, DummyTool)

        # Use tool
        result = await tool.run(value="test")
        assert "test" in result

    def test_plugin_create_tool_when_disabled_raises(self):
        """Test that creating tool from disabled plugin raises error"""
        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )

        plugin = ToolPlugin(
            tool_class=DummyTool,
            metadata=metadata
        )

        # Don't enable - status is LOADED
        with pytest.raises(RuntimeError, match="Plugin status is"):
            plugin.create_tool()

    def test_plugin_enable_disable(self):
        """Test plugin enable/disable"""
        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )

        plugin = ToolPlugin(
            tool_class=DummyTool,
            metadata=metadata
        )

        # Initially loaded
        assert plugin.status == PluginStatus.LOADED

        # Enable
        plugin.enable()
        assert plugin.status == PluginStatus.ENABLED

        # Disable
        plugin.disable()
        assert plugin.status == PluginStatus.DISABLED

    def test_plugin_set_error(self):
        """Test setting plugin error status"""
        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )

        plugin = ToolPlugin(
            tool_class=DummyTool,
            metadata=metadata
        )

        # Set error
        plugin.set_error("Something went wrong")

        assert plugin.status == PluginStatus.ERROR
        assert plugin.error_message == "Something went wrong"

        # Cannot enable plugin with error
        with pytest.raises(RuntimeError, match="Cannot enable"):
            plugin.enable()


# ============================================================================
# Test ToolPluginRegistry
# ============================================================================

class TestToolPluginRegistry:
    """Tests for ToolPluginRegistry"""

    def test_registry_creation(self):
        """Test creating registry"""
        registry = ToolPluginRegistry()
        assert len(registry.list_plugins()) == 0

    def test_registry_register_plugin(self):
        """Test registering plugin"""
        registry = ToolPluginRegistry()

        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin = ToolPlugin(tool_class=DummyTool, metadata=metadata)

        registry.register(plugin)

        assert len(registry.list_plugins()) == 1
        assert registry.get_plugin("test-plugin") == plugin

    def test_registry_register_duplicate_raises(self):
        """Test that registering duplicate plugin raises error"""
        registry = ToolPluginRegistry()

        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin1 = ToolPlugin(tool_class=DummyTool, metadata=metadata)
        plugin2 = ToolPlugin(tool_class=DummyTool, metadata=metadata)

        registry.register(plugin1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(plugin2)

    def test_registry_tool_name_conflict_raises(self):
        """Test that tool name conflict raises error"""
        registry = ToolPluginRegistry()

        # Register first plugin with dummy_tool
        metadata1 = ToolPluginMetadata(
            name="plugin1",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin1 = ToolPlugin(tool_class=DummyTool, metadata=metadata1)
        registry.register(plugin1)

        # Try to register second plugin with same tool name
        metadata2 = ToolPluginMetadata(
            name="plugin2",
            version="1.0.0",
            author="Test",
            description="Test",
            tool_names=["dummy_tool"]  # Conflict!
        )
        plugin2 = ToolPlugin(tool_class=DummyTool, metadata=metadata2)

        with pytest.raises(ValueError, match="conflicts"):
            registry.register(plugin2)

    def test_registry_unregister(self):
        """Test unregistering plugin"""
        registry = ToolPluginRegistry()

        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin = ToolPlugin(tool_class=DummyTool, metadata=metadata)

        registry.register(plugin)
        assert len(registry.list_plugins()) == 1

        registry.unregister("test-plugin")
        assert len(registry.list_plugins()) == 0

    def test_registry_unregister_not_found_raises(self):
        """Test that unregistering non-existent plugin raises error"""
        registry = ToolPluginRegistry()

        with pytest.raises(KeyError, match="not found"):
            registry.unregister("nonexistent")

    @pytest.mark.asyncio
    async def test_registry_get_tool(self):
        """Test getting tool by name"""
        registry = ToolPluginRegistry()

        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin = ToolPlugin(tool_class=DummyTool, metadata=metadata)

        registry.register(plugin)
        plugin.enable()

        # Get tool
        tool = registry.get_tool("dummy_tool")
        assert tool is not None
        assert isinstance(tool, DummyTool)

        # Use tool
        result = await tool.run(value="test")
        assert "test" in result

    def test_registry_get_tool_disabled_returns_none(self):
        """Test that getting tool from disabled plugin returns None"""
        registry = ToolPluginRegistry()

        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin = ToolPlugin(tool_class=DummyTool, metadata=metadata)

        registry.register(plugin)
        # Don't enable

        # Should return None
        tool = registry.get_tool("dummy_tool")
        assert tool is None

    def test_registry_list_plugins(self):
        """Test listing plugins"""
        registry = ToolPluginRegistry()

        # Create different tool classes to avoid name conflicts
        class TestTool1(BaseTool):
            name = "test_tool_1"
            description = "Test tool 1"
            args_schema = DummyToolInput
            async def run(self, value: str, **kwargs) -> str:
                return f"Test 1: {value}"

        class TestTool2(BaseTool):
            name = "test_tool_2"
            description = "Test tool 2"
            args_schema = DummyToolInput
            async def run(self, value: str, **kwargs) -> str:
                return f"Test 2: {value}"

        class TestTool3(BaseTool):
            name = "test_tool_3"
            description = "Test tool 3"
            args_schema = DummyToolInput
            async def run(self, value: str, **kwargs) -> str:
                return f"Test 3: {value}"

        tools = [TestTool1, TestTool2, TestTool3]

        # Register multiple plugins
        for i, tool_class in enumerate(tools):
            metadata = ToolPluginMetadata(
                name=f"plugin-{i}",
                version="1.0.0",
                author="Test",
                description="Test"
            )
            plugin = ToolPlugin(tool_class=tool_class, metadata=metadata)
            registry.register(plugin)

        plugins = registry.list_plugins()
        assert len(plugins) == 3

    def test_registry_list_plugins_with_filter(self):
        """Test listing plugins with status filter"""
        registry = ToolPluginRegistry()

        # Register plugins with different statuses
        metadata1 = ToolPluginMetadata(
            name="enabled-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin1 = ToolPlugin(tool_class=DummyTool, metadata=metadata1)
        registry.register(plugin1)
        plugin1.enable()

        metadata2 = ToolPluginMetadata(
            name="disabled-plugin",
            version="1.0.0",
            author="Test",
            description="Test",
            tool_names=["another_tool"]
        )
        plugin2 = ToolPlugin(tool_class=AnotherDummyTool, metadata=metadata2)
        registry.register(plugin2)
        plugin2.disable()

        # Filter enabled
        enabled = registry.list_plugins(status_filter=PluginStatus.ENABLED)
        assert len(enabled) == 1
        assert enabled[0].metadata.name == "enabled-plugin"

        # Filter disabled
        disabled = registry.list_plugins(status_filter=PluginStatus.DISABLED)
        assert len(disabled) == 1
        assert disabled[0].metadata.name == "disabled-plugin"

    def test_registry_search_by_tag(self):
        """Test searching plugins by tag"""
        registry = ToolPluginRegistry()

        # Register plugins with different tags
        metadata1 = ToolPluginMetadata(
            name="plugin1",
            version="1.0.0",
            author="Test",
            description="Test",
            tags=["tag1", "tag2"]
        )
        plugin1 = ToolPlugin(tool_class=DummyTool, metadata=metadata1)
        registry.register(plugin1)

        metadata2 = ToolPluginMetadata(
            name="plugin2",
            version="1.0.0",
            author="Test",
            description="Test",
            tags=["tag2", "tag3"],
            tool_names=["another_tool"]
        )
        plugin2 = ToolPlugin(tool_class=AnotherDummyTool, metadata=metadata2)
        registry.register(plugin2)

        # Search tag1 (only plugin1)
        results = registry.search_by_tag("tag1")
        assert len(results) == 1
        assert results[0].metadata.name == "plugin1"

        # Search tag2 (both plugins)
        results = registry.search_by_tag("tag2")
        assert len(results) == 2

    def test_registry_search_by_author(self):
        """Test searching plugins by author"""
        registry = ToolPluginRegistry()

        # Register plugins with different authors
        metadata1 = ToolPluginMetadata(
            name="plugin1",
            version="1.0.0",
            author="Alice",
            description="Test"
        )
        plugin1 = ToolPlugin(tool_class=DummyTool, metadata=metadata1)
        registry.register(plugin1)

        metadata2 = ToolPluginMetadata(
            name="plugin2",
            version="1.0.0",
            author="Bob",
            description="Test",
            tool_names=["another_tool"]
        )
        plugin2 = ToolPlugin(tool_class=AnotherDummyTool, metadata=metadata2)
        registry.register(plugin2)

        # Search Alice
        results = registry.search_by_author("alice")  # Case-insensitive
        assert len(results) == 1
        assert results[0].metadata.name == "plugin1"

    def test_registry_get_stats(self):
        """Test getting registry statistics"""
        registry = ToolPluginRegistry()

        # Register plugins
        metadata1 = ToolPluginMetadata(
            name="plugin1",
            version="1.0.0",
            author="Test",
            description="Test",
            tags=["tag1"]
        )
        plugin1 = ToolPlugin(tool_class=DummyTool, metadata=metadata1)
        registry.register(plugin1)
        plugin1.enable()

        metadata2 = ToolPluginMetadata(
            name="plugin2",
            version="1.0.0",
            author="Test",
            description="Test",
            tags=["tag2"],
            tool_names=["another_tool"]
        )
        plugin2 = ToolPlugin(tool_class=AnotherDummyTool, metadata=metadata2)
        registry.register(plugin2)

        stats = registry.get_stats()

        assert stats["total_plugins"] == 2
        assert stats["enabled"] == 1
        assert stats["disabled"] == 0
        assert stats["total_tools"] == 2
        assert len(stats["tags"]) == 2

    def test_registry_enable_disable_plugin(self):
        """Test enabling/disabling plugin via registry"""
        registry = ToolPluginRegistry()

        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin = ToolPlugin(tool_class=DummyTool, metadata=metadata)
        registry.register(plugin)

        # Enable
        registry.enable_plugin("test-plugin")
        assert plugin.status == PluginStatus.ENABLED

        # Disable
        registry.disable_plugin("test-plugin")
        assert plugin.status == PluginStatus.DISABLED


# ============================================================================
# Test ToolPluginLoader
# ============================================================================

class TestToolPluginLoader:
    """Tests for ToolPluginLoader"""

    @pytest.mark.asyncio
    async def test_loader_load_from_file(self):
        """Test loading plugin from file"""
        # Create temporary plugin file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

PLUGIN_METADATA = ToolPluginMetadata(
    name="temp-plugin",
    version="1.0.0",
    author="Test",
    description="Temp plugin"
)

class TempToolInput(BaseModel):
    value: str = Field(..., description="Value")

class TempTool(BaseTool):
    name = "temp_tool"
    description = "Temp tool"
    args_schema = TempToolInput

    async def run(self, value: str, **kwargs) -> str:
        return f"Temp: {value}"
''')
            temp_file = f.name

        try:
            loader = ToolPluginLoader()
            plugin = await loader.load_from_file(temp_file, auto_register=False)

            assert plugin.metadata.name == "temp-plugin"
            assert plugin.metadata.version == "1.0.0"
            assert "temp_tool" in plugin.metadata.tool_names
        finally:
            # Clean up
            Path(temp_file).unlink()

    @pytest.mark.asyncio
    async def test_loader_load_from_file_not_found_raises(self):
        """Test loading from non-existent file raises error"""
        loader = ToolPluginLoader()

        with pytest.raises(FileNotFoundError):
            await loader.load_from_file("/nonexistent/path.py")

    @pytest.mark.asyncio
    async def test_loader_auto_register(self):
        """Test auto-registration when loading"""
        registry = ToolPluginRegistry()
        loader = ToolPluginLoader(registry=registry)

        # Create temporary plugin file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

PLUGIN_METADATA = ToolPluginMetadata(
    name="auto-register-plugin",
    version="1.0.0",
    author="Test",
    description="Auto register test"
)

class AutoToolInput(BaseModel):
    value: str = Field(..., description="Value")

class AutoTool(BaseTool):
    name = "auto_tool"
    description = "Auto tool"
    args_schema = AutoToolInput

    async def run(self, value: str, **kwargs) -> str:
        return f"Auto: {value}"
''')
            temp_file = f.name

        try:
            plugin = await loader.load_from_file(temp_file, auto_register=True)

            # Should be registered and enabled
            assert registry.get_plugin("auto-register-plugin") is not None
            assert plugin.status == PluginStatus.ENABLED

            # Tool should be available
            tool = registry.get_tool("auto_tool")
            assert tool is not None
        finally:
            Path(temp_file).unlink()


# ============================================================================
# Test ToolPluginManager
# ============================================================================

class TestToolPluginManager:
    """Tests for ToolPluginManager"""

    def test_manager_creation(self):
        """Test creating plugin manager"""
        manager = ToolPluginManager()

        assert manager.registry is not None
        assert manager.loader is not None
        assert len(manager.list_installed()) == 0

    @pytest.mark.asyncio
    async def test_manager_install_from_file(self):
        """Test installing plugin from file"""
        manager = ToolPluginManager()

        # Create temporary plugin file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

PLUGIN_METADATA = ToolPluginMetadata(
    name="install-test-plugin",
    version="1.0.0",
    author="Test",
    description="Install test"
)

class InstallToolInput(BaseModel):
    value: str = Field(..., description="Value")

class InstallTool(BaseTool):
    name = "install_tool"
    description = "Install tool"
    args_schema = InstallToolInput

    async def run(self, value: str, **kwargs) -> str:
        return f"Install: {value}"
''')
            temp_file = f.name

        try:
            plugin = await manager.install_from_file(temp_file, enable=True)

            assert plugin.metadata.name == "install-test-plugin"
            assert plugin.status == PluginStatus.ENABLED

            # Should be in installed list
            installed = manager.list_installed()
            assert len(installed) == 1

            # Tool should be available
            tool = manager.get_tool("install_tool")
            assert tool is not None
        finally:
            Path(temp_file).unlink()

    def test_manager_enable_disable(self):
        """Test enabling/disabling plugins via manager"""
        manager = ToolPluginManager()

        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin = ToolPlugin(tool_class=DummyTool, metadata=metadata)
        manager.registry.register(plugin)

        # Enable
        manager.enable("test-plugin")
        assert plugin.status == PluginStatus.ENABLED

        # Disable
        manager.disable("test-plugin")
        assert plugin.status == PluginStatus.DISABLED

    def test_manager_uninstall(self):
        """Test uninstalling plugin"""
        manager = ToolPluginManager()

        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin = ToolPlugin(tool_class=DummyTool, metadata=metadata)
        manager.registry.register(plugin)

        assert len(manager.list_installed()) == 1

        manager.uninstall("test-plugin")

        assert len(manager.list_installed()) == 0

    def test_manager_get_stats(self):
        """Test getting manager statistics"""
        manager = ToolPluginManager()

        metadata = ToolPluginMetadata(
            name="test-plugin",
            version="1.0.0",
            author="Test",
            description="Test"
        )
        plugin = ToolPlugin(tool_class=DummyTool, metadata=metadata)
        manager.registry.register(plugin)
        plugin.enable()

        stats = manager.get_stats()

        assert stats["total_plugins"] == 1
        assert stats["enabled"] == 1
        assert stats["total_tools"] == 1
