"""Test ecosystem MCP and plugin integration."""

import json
from pathlib import Path

import pytest

from loom.ecosystem.integration import EcosystemManager
from loom.ecosystem.plugin import PluginLoader
from loom.ecosystem.mcp import (
    MCPBridge,
    MCPServerConfig,
    MCPTransportType,
    get_default_mcp_bridge,
)
from loom.tools.builtin.mcp_operations import (
    mcp_call_tool,
    mcp_list_resources,
    mcp_read_resource,
)


class TestMCPBridge:
    """Test the single MCP bridge implementation."""

    def test_register_connect_and_list(self):
        bridge = MCPBridge()
        bridge.register_server(
            "docs",
            MCPServerConfig(
                type=MCPTransportType.STDIO,
                instructions="Use docs carefully.",
                mock_tools=[{"name": "search_docs", "description": "search"}],
                mock_resources=[{"uri": "file:///docs", "content": "docs body"}],
            ),
        )

        assert bridge.connect("docs") is True
        assert bridge.get_instructions("docs") == "Use docs carefully."
        assert bridge.list_tools("docs")[0]["name"] == "search_docs"
        assert bridge.list_resources("docs")[0]["uri"] == "file:///docs"

    def test_execute_tool_and_read_resource(self):
        bridge = MCPBridge()
        bridge.register_server(
            "docs",
            MCPServerConfig(
                mock_tools=[{"name": "search_docs"}],
                mock_resources=[{"uri": "file:///docs", "content": "docs body"}],
                mock_tool_results={
                    "search_docs": lambda query: {"hits": [query]},
                },
            ),
        )
        bridge.connect("docs")

        result = bridge.execute_tool("docs", "search_docs", query="loom")
        resource = bridge.read_resource("docs", "file:///docs")

        assert result == {"hits": ["loom"]}
        assert resource["content"] == "docs body"

    def test_connect_disabled_server(self):
        bridge = MCPBridge()
        bridge.register_server(
            "disabled",
            MCPServerConfig(disabled=True),
        )
        assert bridge.connect("disabled") is False


class TestEcosystemManager:
    """Test ecosystem manager MCP config parsing."""

    def test_parse_mcp_config_resolves_env_and_instructions(self, tmp_path: Path, monkeypatch):
        manager = EcosystemManager()
        monkeypatch.setenv("TEST_MCP_CMD", "demo-server")

        config = manager._parse_mcp_config(
            {
                "type": "stdio",
                "command": "${TEST_MCP_CMD}",
                "args": ["--root", "${CLAUDE_PLUGIN_ROOT}"],
                "instructions": "Read plugin docs.",
                "autoApprove": ["search_docs"],
            },
            tmp_path,
        )

        assert config.command == "demo-server"
        assert str(tmp_path) in config.args[1]
        assert config.instructions == "Read plugin docs."
        assert config.auto_approve == ["search_docs"]

    def test_load_plugins_and_toggle_plugin_state(self, tmp_path: Path):
        """Test plugin load, enable, disable, and runtime effect."""
        manager = EcosystemManager()

        plugin_dir = tmp_path / "demo-plugin"
        skills_dir = plugin_dir / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "review.md").write_text("# Review Skill\nUse this for review tasks.\n")
        (plugin_dir / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "demo-plugin",
                    "version": "1.0.0",
                    "description": "Demo plugin",
                    "skills": ["skills"],
                    "mcpServers": {
                        "docs": {
                            "type": "stdio",
                            "command": "demo-mcp",
                            "instructions": "Use demo docs.",
                        }
                    },
                }
            )
        )

        manager.load_plugins(tmp_path)
        assert "review" in manager.skill_registry.list_skills()
        assert "plugin:demo-plugin:docs" in manager.mcp_bridge.servers
        assert "Use demo docs." in manager.get_system_prompt_additions()
        assert "plugin:demo-plugin" in manager.capability_registry.active_capabilities

        assert manager.disable_plugin("demo-plugin") is True
        assert "review" not in manager.skill_registry.list_skills()
        assert "plugin:demo-plugin:docs" not in manager.mcp_bridge.servers
        assert manager.get_system_prompt_additions() == ""

        assert manager.enable_plugin("demo-plugin") is True
        assert "review" in manager.skill_registry.list_skills()
        assert "plugin:demo-plugin:docs" in manager.mcp_bridge.servers


class TestPluginLoader:
    """Test plugin loader controls."""

    def test_enable_disable_and_get_plugin(self, tmp_path: Path):
        loader = PluginLoader()
        plugin_dir = tmp_path / "demo-plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.json").write_text(
            json.dumps(
                {
                    "name": "demo-plugin",
                    "version": "1.0.0",
                    "description": "Demo plugin",
                    "enabled": False,
                }
            )
        )

        plugin = loader.load_plugin(plugin_dir)
        assert plugin is not None
        assert loader.get_plugin("demo-plugin") is plugin
        assert plugin.enabled is False

        loader.enable_plugin("demo-plugin")
        assert plugin.enabled is True

        loader.disable_plugin("demo-plugin")
        assert plugin.enabled is False


class TestMCPOperations:
    """Test builtin MCP operations via the default bridge."""

    @pytest.mark.asyncio
    async def test_builtin_mcp_operations(self):
        bridge = get_default_mcp_bridge()
        bridge.servers.clear()
        bridge._instructions_cache.clear()

        bridge.register_server(
            "docs",
            MCPServerConfig(
                mock_tools=[{"name": "search_docs"}],
                mock_resources=[{"uri": "file:///docs", "content": "docs body"}],
                mock_tool_results={"search_docs": {"hits": ["loom"]}},
            ),
        )
        bridge.connect("docs")

        listed = await mcp_list_resources("docs")
        read = await mcp_read_resource("docs", "file:///docs")
        called = await mcp_call_tool("docs", "search_docs", {"query": "loom"})

        assert listed["resources"][0]["uri"] == "file:///docs"
        assert read["content"] == "docs body"
        assert called["result"] == {"hits": ["loom"]}
