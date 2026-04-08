"""Ecosystem integration - 整合 Skill、Plugin、MCP

参考 Claude Code 的集成方式：
1. Plugin 可以提供 Skills、MCP servers、Hooks
2. Skills 可以指定 allowedTools（来自 MCP）
3. MCP instructions 注入到 system prompt
"""

from dataclasses import dataclass, field
from pathlib import Path

from ..ecosystem.mcp import MCPBridge, MCPServerConfig, MCPTransportType
from ..ecosystem.plugin import Plugin, PluginLoader
from ..ecosystem.skill import SkillLoader, SkillRegistry
from .activation import Capability, CapabilityRegistry


@dataclass
class PluginLoadState:
    """Track components loaded from one plugin."""
    skill_names: list[str] = field(default_factory=list)
    mcp_server_names: list[str] = field(default_factory=list)


class EcosystemManager:
    """Manage the entire ecosystem"""

    def __init__(self):
        self.skill_registry = SkillRegistry()
        self.plugin_loader = PluginLoader()
        self.mcp_bridge = MCPBridge()
        self.capability_registry = CapabilityRegistry()
        self._plugin_state: dict[str, PluginLoadState] = {}

    def load_user_skills(self, skills_dir: Path):
        """Load user skills from directory"""
        SkillLoader.load_from_directory(skills_dir, self.skill_registry)

    def load_plugins(self, plugins_dir: Path):
        """Load plugins and their components"""
        self.plugin_loader.load_plugins_from_directory(plugins_dir)

        # Load components from enabled plugins
        for plugin in self.plugin_loader.get_enabled_plugins():
            self._load_plugin_components(plugin)

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin and load its components if needed."""
        plugin = self.plugin_loader.enable_plugin(name)
        if not plugin:
            return False
        self._load_plugin_components(plugin)
        return True

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin and unload its plugin-scoped components."""
        plugin = self.plugin_loader.disable_plugin(name)
        if not plugin:
            return False

        state = self._plugin_state.pop(name, PluginLoadState())
        for skill_name in state.skill_names:
            self.skill_registry.unregister(skill_name)

        for server_name in state.mcp_server_names:
            self.mcp_bridge.servers.pop(server_name, None)
            self.mcp_bridge._instructions_cache.pop(server_name, None)

        self.capability_registry.deactivate(f"plugin:{name}")
        return True

    def _load_plugin_components(self, plugin: Plugin):
        """Load skills, MCP servers from plugin"""
        if not plugin.enabled:
            return

        existing_state = self._plugin_state.get(plugin.name)
        if existing_state:
            for skill_name in existing_state.skill_names:
                self.skill_registry.unregister(skill_name)
            for server_name in existing_state.mcp_server_names:
                self.mcp_bridge.servers.pop(server_name, None)
                self.mcp_bridge._instructions_cache.pop(server_name, None)

        state = PluginLoadState()

        # Load skills
        if plugin.manifest.skills:
            for skill_path in plugin.manifest.skills:
                full_path = plugin.path / skill_path
                if full_path.exists():
                    before = set(self.skill_registry.list_skills())
                    SkillLoader.load_from_directory(full_path, self.skill_registry)
                    after = set(self.skill_registry.list_skills())
                    state.skill_names.extend(sorted(after - before))

        # Load MCP servers
        if plugin.manifest.mcp_servers:
            for server_name, server_config in plugin.manifest.mcp_servers.items():
                scoped_name = f"plugin:{plugin.name}:{server_name}"
                config = self._parse_mcp_config(server_config, plugin.path)
                self.mcp_bridge.register_server(
                    scoped_name,
                    config,
                    scope="plugin",
                    plugin_source=plugin.source,
                )
                state.mcp_server_names.append(scoped_name)

        self._plugin_state[plugin.name] = state
        self.capability_registry.register(
            Capability(
                name=f"plugin:{plugin.name}",
                description=plugin.manifest.description,
                tools=state.mcp_server_names.copy(),
                activation="manual",
                keywords=[plugin.name],
            )
        )
        self.capability_registry.activate(f"plugin:{plugin.name}")

    def _parse_mcp_config(self, config_dict: dict, plugin_path: Path) -> MCPServerConfig:
        """Parse MCP config from dict"""
        transport_type = MCPTransportType(config_dict.get('type', 'stdio'))

        config = MCPServerConfig(type=transport_type)

        if transport_type == MCPTransportType.STDIO:
            config.command = config_dict.get('command')
            config.args = config_dict.get('args', [])
            config.env = config_dict.get('env', {})

            # Resolve environment variables
            if config.command:
                config.command = self.mcp_bridge.resolve_env_vars(
                    config.command, str(plugin_path)
                )
            if config.args:
                config.args = [
                    self.mcp_bridge.resolve_env_vars(arg, str(plugin_path))
                    for arg in config.args
                ]
        else:
            config.url = config_dict.get('url')
            config.headers = config_dict.get('headers', {})

        config.disabled = config_dict.get('disabled', False)
        config.auto_approve = config_dict.get('autoApprove', [])
        config.instructions = config_dict.get('instructions', "")

        return config

    def get_system_prompt_additions(self) -> str:
        """Get MCP instructions for system prompt"""
        additions = []
        for server_name in self.mcp_bridge.servers:
            instructions = self.mcp_bridge.get_instructions(server_name)
            if instructions:
                additions.append(f"# {server_name}\n{instructions}")
        return "\n\n".join(additions)
