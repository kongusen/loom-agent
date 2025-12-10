"""
Loom Plugin System - Extensible Plugin Architecture

This module provides a plugin system for extending loom-agent with:
- Tool plugins
- LLM plugins (future)
- Memory plugins (future)

Example:
    ```python
    from loom.plugins import ToolPluginRegistry, ToolPluginLoader

    # Load plugin from file
    loader = ToolPluginLoader()
    plugin = await loader.load_from_file("plugins/my_tool.py")

    # Register plugin
    registry = ToolPluginRegistry()
    registry.register(plugin)

    # Use plugin
    tool = registry.get_tool("my_tool")
    result = await tool.run(param="value")
    ```
"""

from __future__ import annotations

__version__ = "0.1.0"

# Tool plugins
from loom.plugins.tool_plugin import (
    ToolPlugin,
    ToolPluginMetadata,
    ToolPluginRegistry,
    ToolPluginLoader,
    ToolPluginManager,
    PluginStatus,
)

__all__ = [
    # Core version
    "__version__",

    # Tool plugins
    "ToolPlugin",
    "ToolPluginMetadata",
    "ToolPluginRegistry",
    "ToolPluginLoader",
    "ToolPluginManager",
    "PluginStatus",
]
