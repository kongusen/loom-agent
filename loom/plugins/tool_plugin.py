"""
Tool Plugin System

This module provides a plugin architecture for extending loom-agent with custom tools.

Key Components:
- ToolPluginMetadata: Plugin metadata (name, version, author, etc.)
- ToolPlugin: Plugin wrapper containing tool + metadata
- ToolPluginRegistry: Central registry for managing plugins
- ToolPluginLoader: Load plugins from files/packages
- ToolPluginManager: High-level plugin lifecycle management

Example:
    ```python
    # Create a plugin
    from loom.plugins import ToolPlugin, ToolPluginMetadata
    from loom.interfaces.tool import BaseTool

    class MyTool(BaseTool):
        name = "my_tool"
        description = "My custom tool"
        args_schema = MyToolInput

        async def run(self, **kwargs):
            return "result"

    metadata = ToolPluginMetadata(
        name="my-tool-plugin",
        version="1.0.0",
        author="John Doe",
        description="A custom tool plugin"
    )

    plugin = ToolPlugin(
        tool_class=MyTool,
        metadata=metadata
    )

    # Register plugin
    from loom.plugins import ToolPluginRegistry

    registry = ToolPluginRegistry()
    registry.register(plugin)

    # Use plugin
    tool = registry.get_tool("my_tool")
    result = await tool.run()
    ```
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Set
from enum import Enum

from loom.interfaces.tool import BaseTool


class PluginStatus(Enum):
    """Plugin status"""
    LOADED = "loaded"          # Plugin loaded but not enabled
    ENABLED = "enabled"        # Plugin enabled and active
    DISABLED = "disabled"      # Plugin disabled
    ERROR = "error"           # Plugin has errors


@dataclass
class ToolPluginMetadata:
    """
    Tool plugin metadata.

    Attributes:
        name: Plugin name (unique identifier, lowercase-with-dashes)
        version: Semantic version string (e.g., "1.0.0")
        author: Author name/email
        description: Brief plugin description
        homepage: Plugin homepage URL (optional)
        license: License identifier (e.g., "MIT", "Apache-2.0")
        dependencies: List of required Python packages
        loom_min_version: Minimum loom-agent version required
        tags: Tags for categorization
        tool_names: Names of tools provided by this plugin
    """

    name: str
    version: str
    author: str
    description: str
    homepage: Optional[str] = None
    license: str = "MIT"
    dependencies: List[str] = field(default_factory=list)
    loom_min_version: str = "0.1.0"
    tags: List[str] = field(default_factory=list)
    tool_names: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate metadata"""
        # Validate name format (lowercase-with-dashes)
        if not re.match(r'^[a-z][a-z0-9-]*$', self.name):
            raise ValueError(
                f"Invalid plugin name '{self.name}'. "
                "Must be lowercase-with-dashes (e.g., 'my-tool-plugin')"
            )

        # Validate version format (semantic versioning)
        if not re.match(r'^\d+\.\d+\.\d+', self.version):
            raise ValueError(
                f"Invalid version '{self.version}'. "
                "Must follow semantic versioning (e.g., '1.0.0')"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolPluginMetadata":
        """Create from dictionary"""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ToolPluginMetadata":
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class ToolPlugin:
    """
    Tool plugin wrapper.

    Attributes:
        tool_class: Tool class (must inherit from BaseTool)
        metadata: Plugin metadata
        status: Plugin status (loaded/enabled/disabled/error)
        error_message: Error message if status is ERROR
    """

    tool_class: Type[BaseTool]
    metadata: ToolPluginMetadata
    status: PluginStatus = PluginStatus.LOADED
    error_message: Optional[str] = None

    def __post_init__(self):
        """Validate plugin"""
        # Validate tool_class inherits from BaseTool
        if not issubclass(self.tool_class, BaseTool):
            raise ValueError(
                f"Tool class {self.tool_class.__name__} must inherit from BaseTool"
            )

        # Add tool name to metadata if not present
        tool_name = self.tool_class.name
        if tool_name not in self.metadata.tool_names:
            self.metadata.tool_names.append(tool_name)

    def create_tool(self, **kwargs) -> BaseTool:
        """
        Create tool instance.

        Args:
            **kwargs: Tool initialization arguments

        Returns:
            BaseTool: Tool instance

        Raises:
            RuntimeError: If plugin is not enabled
        """
        if self.status != PluginStatus.ENABLED:
            raise RuntimeError(
                f"Cannot create tool from plugin '{self.metadata.name}': "
                f"Plugin status is {self.status.value}"
            )

        return self.tool_class(**kwargs)

    def enable(self) -> None:
        """Enable plugin"""
        if self.status == PluginStatus.ERROR:
            raise RuntimeError(
                f"Cannot enable plugin '{self.metadata.name}': {self.error_message}"
            )
        self.status = PluginStatus.ENABLED

    def disable(self) -> None:
        """Disable plugin"""
        self.status = PluginStatus.DISABLED

    def set_error(self, error_message: str) -> None:
        """Mark plugin as error"""
        self.status = PluginStatus.ERROR
        self.error_message = error_message


class ToolPluginRegistry:
    """
    Central registry for tool plugins.

    Example:
        ```python
        registry = ToolPluginRegistry()

        # Register plugin
        registry.register(plugin)

        # Get tool by name
        tool = registry.get_tool("my_tool")

        # List all plugins
        plugins = registry.list_plugins()

        # Search by tag
        data_plugins = registry.search_by_tag("data")
        ```
    """

    def __init__(self):
        # Plugin storage: plugin_name -> ToolPlugin
        self._plugins: Dict[str, ToolPlugin] = {}

        # Tool name index: tool_name -> plugin_name
        self._tool_index: Dict[str, str] = {}

    def register(self, plugin: ToolPlugin) -> None:
        """
        Register a plugin.

        Args:
            plugin: Plugin to register

        Raises:
            ValueError: If plugin name already registered or tool name conflicts
        """
        # Check plugin name conflict
        if plugin.metadata.name in self._plugins:
            raise ValueError(
                f"Plugin '{plugin.metadata.name}' is already registered"
            )

        # Check tool name conflicts
        for tool_name in plugin.metadata.tool_names:
            if tool_name in self._tool_index:
                existing_plugin = self._tool_index[tool_name]
                raise ValueError(
                    f"Tool name '{tool_name}' conflicts with plugin '{existing_plugin}'"
                )

        # Register plugin
        self._plugins[plugin.metadata.name] = plugin

        # Update tool index
        for tool_name in plugin.metadata.tool_names:
            self._tool_index[tool_name] = plugin.metadata.name

    def unregister(self, plugin_name: str) -> None:
        """
        Unregister a plugin.

        Args:
            plugin_name: Name of plugin to unregister

        Raises:
            KeyError: If plugin not found
        """
        if plugin_name not in self._plugins:
            raise KeyError(f"Plugin '{plugin_name}' not found")

        plugin = self._plugins[plugin_name]

        # Remove from tool index
        for tool_name in plugin.metadata.tool_names:
            del self._tool_index[tool_name]

        # Remove plugin
        del self._plugins[plugin_name]

    def get_plugin(self, plugin_name: str) -> Optional[ToolPlugin]:
        """
        Get plugin by name.

        Args:
            plugin_name: Plugin name

        Returns:
            Optional[ToolPlugin]: Plugin if found, None otherwise
        """
        return self._plugins.get(plugin_name)

    def get_tool(self, tool_name: str, **kwargs) -> Optional[BaseTool]:
        """
        Get tool instance by tool name.

        Args:
            tool_name: Tool name
            **kwargs: Tool initialization arguments

        Returns:
            Optional[BaseTool]: Tool instance if found and enabled, None otherwise
        """
        plugin_name = self._tool_index.get(tool_name)
        if not plugin_name:
            return None

        plugin = self._plugins.get(plugin_name)
        if not plugin or plugin.status != PluginStatus.ENABLED:
            return None

        return plugin.create_tool(**kwargs)

    def list_plugins(
        self,
        status_filter: Optional[PluginStatus] = None
    ) -> List[ToolPlugin]:
        """
        List all plugins.

        Args:
            status_filter: Optional status filter

        Returns:
            List[ToolPlugin]: List of plugins
        """
        plugins = list(self._plugins.values())

        if status_filter:
            plugins = [p for p in plugins if p.status == status_filter]

        return plugins

    def search_by_tag(self, tag: str) -> List[ToolPlugin]:
        """
        Search plugins by tag.

        Args:
            tag: Tag to search for

        Returns:
            List[ToolPlugin]: Matching plugins
        """
        return [
            plugin
            for plugin in self._plugins.values()
            if tag in plugin.metadata.tags
        ]

    def search_by_author(self, author: str) -> List[ToolPlugin]:
        """
        Search plugins by author.

        Args:
            author: Author name (case-insensitive partial match)

        Returns:
            List[ToolPlugin]: Matching plugins
        """
        author_lower = author.lower()
        return [
            plugin
            for plugin in self._plugins.values()
            if author_lower in plugin.metadata.author.lower()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dict: Statistics including total plugins, enabled/disabled counts, etc.
        """
        plugins = list(self._plugins.values())

        return {
            "total_plugins": len(plugins),
            "enabled": len([p for p in plugins if p.status == PluginStatus.ENABLED]),
            "disabled": len([p for p in plugins if p.status == PluginStatus.DISABLED]),
            "error": len([p for p in plugins if p.status == PluginStatus.ERROR]),
            "total_tools": len(self._tool_index),
            "tags": self._get_all_tags(),
        }

    def _get_all_tags(self) -> List[str]:
        """Get all unique tags"""
        tags: Set[str] = set()
        for plugin in self._plugins.values():
            tags.update(plugin.metadata.tags)
        return sorted(tags)

    def enable_plugin(self, plugin_name: str) -> None:
        """
        Enable a plugin.

        Args:
            plugin_name: Plugin name

        Raises:
            KeyError: If plugin not found
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise KeyError(f"Plugin '{plugin_name}' not found")

        plugin.enable()

    def disable_plugin(self, plugin_name: str) -> None:
        """
        Disable a plugin.

        Args:
            plugin_name: Plugin name

        Raises:
            KeyError: If plugin not found
        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise KeyError(f"Plugin '{plugin_name}' not found")

        plugin.disable()


class ToolPluginLoader:
    """
    Load tool plugins from various sources.

    Example:
        ```python
        loader = ToolPluginLoader()

        # Load from Python file
        plugin = await loader.load_from_file("plugins/my_tool.py")

        # Load from Python module
        plugin = await loader.load_from_module("my_package.my_tool")

        # Discover plugins in directory
        plugins = await loader.discover_plugins("plugins/")
        ```
    """

    def __init__(self, registry: Optional[ToolPluginRegistry] = None):
        """
        Initialize loader.

        Args:
            registry: Plugin registry (optional, for auto-registration)
        """
        self.registry = registry

    async def load_from_file(
        self,
        file_path: str | Path,
        auto_register: bool = True
    ) -> ToolPlugin:
        """
        Load plugin from Python file.

        Args:
            file_path: Path to Python file
            auto_register: Auto-register to registry if available

        Returns:
            ToolPlugin: Loaded plugin

        Raises:
            FileNotFoundError: If file not found
            ValueError: If plugin definition invalid
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Plugin file not found: {file_path}")

        # Load module from file
        spec = importlib.util.spec_from_file_location(
            file_path.stem,
            file_path
        )
        if not spec or not spec.loader:
            raise ValueError(f"Cannot load module from {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Extract plugin from module
        plugin = self._extract_plugin_from_module(module)

        # Auto-register
        if auto_register and self.registry:
            self.registry.register(plugin)
            plugin.enable()

        return plugin

    async def load_from_module(
        self,
        module_name: str,
        auto_register: bool = True
    ) -> ToolPlugin:
        """
        Load plugin from Python module.

        Args:
            module_name: Module name (e.g., "my_package.my_tool")
            auto_register: Auto-register to registry if available

        Returns:
            ToolPlugin: Loaded plugin

        Raises:
            ImportError: If module not found
            ValueError: If plugin definition invalid
        """
        # Import module
        module = importlib.import_module(module_name)

        # Extract plugin
        plugin = self._extract_plugin_from_module(module)

        # Auto-register
        if auto_register and self.registry:
            self.registry.register(plugin)
            plugin.enable()

        return plugin

    async def discover_plugins(
        self,
        directory: str | Path,
        auto_register: bool = True
    ) -> List[ToolPlugin]:
        """
        Discover and load all plugins in directory.

        Args:
            directory: Directory to search
            auto_register: Auto-register plugins to registry

        Returns:
            List[ToolPlugin]: Discovered plugins
        """
        directory = Path(directory)

        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Invalid directory: {directory}")

        plugins = []

        # Find all .py files
        for file_path in directory.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            try:
                plugin = await self.load_from_file(file_path, auto_register=auto_register)
                plugins.append(plugin)
            except Exception as e:
                # Log error but continue
                print(f"Warning: Failed to load plugin from {file_path}: {e}")

        return plugins

    def _extract_plugin_from_module(self, module) -> ToolPlugin:
        """
        Extract ToolPlugin from module.

        Expected module structure:
        ```python
        # plugin.py
        from loom.interfaces.tool import BaseTool
        from loom.plugins import ToolPluginMetadata

        PLUGIN_METADATA = ToolPluginMetadata(
            name="my-plugin",
            version="1.0.0",
            author="John Doe",
            description="My plugin"
        )

        class MyTool(BaseTool):
            name = "my_tool"
            ...
        ```

        Args:
            module: Python module

        Returns:
            ToolPlugin: Extracted plugin

        Raises:
            ValueError: If module structure invalid
        """
        # Find PLUGIN_METADATA
        if not hasattr(module, "PLUGIN_METADATA"):
            raise ValueError("Module must define PLUGIN_METADATA")

        metadata = module.PLUGIN_METADATA
        if not isinstance(metadata, ToolPluginMetadata):
            raise ValueError("PLUGIN_METADATA must be ToolPluginMetadata instance")

        # Find tool class
        tool_class = None
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                obj != BaseTool
                and issubclass(obj, BaseTool)
                and obj.__module__ == module.__name__
            ):
                tool_class = obj
                break

        if not tool_class:
            raise ValueError("Module must define a tool class (inheriting from BaseTool)")

        # Create plugin
        return ToolPlugin(
            tool_class=tool_class,
            metadata=metadata
        )


class ToolPluginManager:
    """
    High-level plugin lifecycle management.

    Combines registry and loader for convenient plugin management.

    Example:
        ```python
        manager = ToolPluginManager()

        # Install plugin from file
        await manager.install_from_file("plugins/my_tool.py")

        # List installed plugins
        plugins = manager.list_installed()

        # Get tool
        tool = manager.get_tool("my_tool")

        # Uninstall plugin
        manager.uninstall("my-plugin")
        ```
    """

    def __init__(
        self,
        plugin_dir: Optional[str | Path] = None
    ):
        """
        Initialize manager.

        Args:
            plugin_dir: Directory for storing installed plugins (optional)
        """
        self.registry = ToolPluginRegistry()
        self.loader = ToolPluginLoader(registry=self.registry)
        self.plugin_dir = Path(plugin_dir) if plugin_dir else None

        if self.plugin_dir:
            self.plugin_dir.mkdir(parents=True, exist_ok=True)

    async def install_from_file(
        self,
        file_path: str | Path,
        enable: bool = True
    ) -> ToolPlugin:
        """
        Install plugin from file.

        Args:
            file_path: Path to plugin file
            enable: Enable plugin after installation

        Returns:
            ToolPlugin: Installed plugin
        """
        plugin = await self.loader.load_from_file(file_path, auto_register=True)

        if enable:
            plugin.enable()

        return plugin

    async def install_from_module(
        self,
        module_name: str,
        enable: bool = True
    ) -> ToolPlugin:
        """
        Install plugin from module.

        Args:
            module_name: Module name
            enable: Enable plugin after installation

        Returns:
            ToolPlugin: Installed plugin
        """
        plugin = await self.loader.load_from_module(module_name, auto_register=True)

        if enable:
            plugin.enable()

        return plugin

    async def discover_and_install(
        self,
        directory: Optional[str | Path] = None,
        enable: bool = True
    ) -> List[ToolPlugin]:
        """
        Discover and install all plugins in directory.

        Args:
            directory: Directory to search (defaults to plugin_dir)
            enable: Enable plugins after installation

        Returns:
            List[ToolPlugin]: Installed plugins
        """
        if directory is None:
            if self.plugin_dir is None:
                raise ValueError("No plugin directory specified")
            directory = self.plugin_dir

        plugins = await self.loader.discover_plugins(directory, auto_register=True)

        if enable:
            for plugin in plugins:
                plugin.enable()

        return plugins

    def uninstall(self, plugin_name: str) -> None:
        """
        Uninstall plugin.

        Args:
            plugin_name: Plugin name
        """
        self.registry.unregister(plugin_name)

    def enable(self, plugin_name: str) -> None:
        """Enable plugin"""
        self.registry.enable_plugin(plugin_name)

    def disable(self, plugin_name: str) -> None:
        """Disable plugin"""
        self.registry.disable_plugin(plugin_name)

    def list_installed(
        self,
        status_filter: Optional[PluginStatus] = None
    ) -> List[ToolPlugin]:
        """
        List installed plugins.

        Args:
            status_filter: Optional status filter

        Returns:
            List[ToolPlugin]: Installed plugins
        """
        return self.registry.list_plugins(status_filter=status_filter)

    def get_tool(self, tool_name: str, **kwargs) -> Optional[BaseTool]:
        """
        Get tool by name.

        Args:
            tool_name: Tool name
            **kwargs: Tool initialization arguments

        Returns:
            Optional[BaseTool]: Tool instance if found
        """
        return self.registry.get_tool(tool_name, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        return self.registry.get_stats()
