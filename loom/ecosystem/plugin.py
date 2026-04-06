"""Plugin system - 参考 Claude Code plugins

Plugin 特性：
1. plugin.json manifest 定义元数据
2. 可包含 skills/、commands/、hooks/、mcp servers
3. 支持依赖管理
4. 支持启用/禁用
5. 支持版本管理
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PluginManifest:
    """Plugin manifest (plugin.json)"""
    name: str
    version: str
    description: str
    author: str | None = None

    # Components
    skills: list[str] | None = None  # paths to skill dirs
    commands: list[str] | None = None
    hooks: dict[str, Any] | None = None
    mcp_servers: dict[str, Any] | None = None

    # Dependencies
    dependencies: list[str] = field(default_factory=list)

    # Metadata
    repository: str | None = None
    enabled: bool = True


@dataclass
class Plugin:
    """Loaded plugin"""
    name: str
    manifest: PluginManifest
    path: Path
    source: str  # marketplace name or path

    enabled: bool = True
    is_builtin: bool = False


class PluginLoader:
    """Load plugins from filesystem"""

    def __init__(self):
        self.plugins: dict[str, Plugin] = {}
        self.errors: list[str] = []

    def load_manifest(self, plugin_dir: Path) -> PluginManifest | None:
        """Load plugin.json manifest"""
        manifest_path = plugin_dir / 'plugin.json'
        if not manifest_path.exists():
            return None

        import json
        try:
            data = json.loads(manifest_path.read_text())
            return PluginManifest(
                name=data['name'],
                version=data['version'],
                description=data['description'],
                author=data.get('author'),
                skills=data.get('skills'),
                commands=data.get('commands'),
                hooks=data.get('hooks'),
                mcp_servers=data.get('mcpServers'),
                dependencies=data.get('dependencies', []),
                repository=data.get('repository'),
                enabled=data.get('enabled', True),
            )
        except Exception as e:
            self.errors.append(f"Failed to load manifest from {plugin_dir}: {e}")
            return None

    def load_plugin(self, plugin_dir: Path, source: str = 'local') -> Plugin | None:
        """Load plugin from directory"""
        manifest = self.load_manifest(plugin_dir)
        if not manifest:
            return None

        plugin = Plugin(
            name=manifest.name,
            manifest=manifest,
            path=plugin_dir,
            source=source,
            enabled=manifest.enabled,
        )

        self.plugins[plugin.name] = plugin
        return plugin

    def get_plugin(self, name: str) -> Plugin | None:
        """Get plugin by name."""
        return self.plugins.get(name)

    def enable_plugin(self, name: str) -> Plugin | None:
        """Enable a loaded plugin."""
        plugin = self.plugins.get(name)
        if plugin:
            plugin.enabled = True
        return plugin

    def disable_plugin(self, name: str) -> Plugin | None:
        """Disable a loaded plugin."""
        plugin = self.plugins.get(name)
        if plugin:
            plugin.enabled = False
        return plugin

    def load_plugins_from_directory(self, plugins_dir: Path):
        """Load all plugins from directory"""
        if not plugins_dir.exists():
            return

        for plugin_dir in plugins_dir.iterdir():
            if plugin_dir.is_dir():
                self.load_plugin(plugin_dir)

    def get_enabled_plugins(self) -> list[Plugin]:
        """Get all enabled plugins"""
        return [p for p in self.plugins.values() if p.enabled]

    def apply_to_agent(self, plugin_name: str, agent) -> bool:
        """Connect plugin's MCP servers and hooks to an agent."""
        plugin = self.plugins.get(plugin_name)
        if not plugin or not plugin.enabled:
            return False

        manifest = plugin.manifest

        # Register MCP servers
        if manifest.mcp_servers:
            mcp_bridge = getattr(agent, "mcp_bridge", None)
            if mcp_bridge is not None:
                from .mcp import MCPServerConfig, MCPTransportType
                for name, cfg in manifest.mcp_servers.items():
                    transport = MCPTransportType(cfg.get("type", "stdio"))
                    server_cfg = MCPServerConfig(
                        type=transport,
                        command=cfg.get("command"),
                        args=cfg.get("args"),
                        env=cfg.get("env"),
                        url=cfg.get("url"),
                        instructions=cfg.get("instructions", ""),
                    )
                    scoped_name = f"plugin:{plugin_name}:{name}"
                    mcp_bridge.register_server(scoped_name, server_cfg,
                                               scope="plugin", plugin_source=plugin_name)

        # Register hooks
        if manifest.hooks:
            hook_mgr = getattr(agent, "hook_manager", None)
            if hook_mgr is not None:
                for event, handler_path in manifest.hooks.items():
                    if callable(handler_path):
                        hook_mgr.register(event, handler_path)

        return True
