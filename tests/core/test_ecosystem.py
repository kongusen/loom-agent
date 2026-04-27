"""Test ecosystem MCP and plugin integration."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from loom.agent import Agent
from loom.config import AgentConfig, ModelRef
from loom.ecosystem.integration import EcosystemManager
from loom.ecosystem.mcp import (
    MCPBridge,
    MCPServerConfig,
    MCPTransportType,
    get_default_mcp_bridge,
)
from loom.ecosystem.plugin import PluginLoader
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


# ── Agent integration: M3/M4/M5 ──

def _make_agent(**kwargs):
    return Agent(config=AgentConfig(
        model=ModelRef(provider="anthropic", name="claude-3-5-sonnet-20241022"),
        **kwargs,
    ))


class TestAgentEcosystemIntegration:
    """M3: EcosystemManager and MCPBridge wired into Agent + Engine."""

    def test_ecosystem_property_lazy(self):
        agent = _make_agent()
        assert agent._ecosystem is None
        eco = agent.ecosystem
        assert eco is not None
        assert eco is agent.ecosystem  # singleton

    def test_mcp_bridge_delegates_to_ecosystem(self):
        agent = _make_agent()
        assert agent.mcp_bridge is agent.ecosystem.mcp_bridge

    def test_configure_ecosystem_noop_when_untouched(self):
        agent = _make_agent()
        engine = agent._build_engine(MagicMock())
        # ecosystem was never accessed → engine must not have it
        assert engine.ecosystem_manager is None

    def test_configure_ecosystem_wires_when_touched(self):
        agent = _make_agent()
        _ = agent.ecosystem  # touch to initialise
        engine = agent._build_engine(MagicMock())
        assert engine.ecosystem_manager is agent._ecosystem

    def test_mcp_instructions_registered_in_engine(self):
        agent = _make_agent()
        agent.ecosystem.mcp_bridge.register_server(
            "myserver",
            MCPServerConfig(instructions="Use myserver for queries."),
        )
        engine = agent._build_engine(MagicMock())
        # instructions will be injected in execute(); check bridge is wired
        assert engine.ecosystem_manager is agent._ecosystem

    def test_mcp_tools_registered_in_tool_registry(self):
        agent = _make_agent()
        # Register a mock connected server with tools
        bridge = agent.ecosystem.mcp_bridge
        bridge.register_server(
            "myserver",
            MCPServerConfig(
                mock_tools=[{
                    "name": "search",
                    "description": "Search tool",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "Query"}},
                        "required": ["query"],
                    },
                }],
            ),
        )
        bridge.connect("myserver")
        engine = agent._build_engine(MagicMock())
        tool_names = [t.definition.name for t in engine.tool_registry.list()]
        assert any("search" in n for n in tool_names)


class TestAgentEvolutionIntegration:
    """M4: EvolutionEngine auto-subscribed in _build_engine."""

    def test_evolution_property_lazy(self):
        agent = _make_agent()
        assert agent._evolution_engine is None
        from loom.evolution.engine import EvolutionEngine
        evo = agent.evolution
        assert isinstance(evo, EvolutionEngine)
        assert evo is agent.evolution  # singleton

    def test_configure_evolution_noop_when_untouched(self):
        agent = _make_agent()
        engine = agent._build_engine(MagicMock())
        handlers = engine._event_handlers.get("tool_result", [])
        assert len(handlers) == 0

    def test_configure_evolution_subscribes_when_touched(self):
        agent = _make_agent()
        _ = agent.evolution  # touch to initialise
        engine = agent._build_engine(MagicMock())
        handlers = engine._event_handlers.get("tool_result", [])
        assert len(handlers) == 1


class TestAgentCoordinatorIntegration:
    """M5: Coordinator exposed on Agent."""

    def test_coordinator_property_lazy(self):
        agent = _make_agent()
        assert agent._coordinator is None
        from loom.orchestration.coordinator import Coordinator
        coord = agent.coordinator
        assert isinstance(coord, Coordinator)
        assert coord is agent.coordinator  # singleton

    def test_coordinator_registers_self(self):
        agent = _make_agent()
        coord = agent.coordinator
        assert str(id(agent)) in coord.agents

    def test_coordinator_has_subagent_manager(self):
        from loom.orchestration.subagent import SubAgentManager
        agent = _make_agent()
        coord = agent.coordinator
        mgr = coord.agents[str(id(agent))]
        assert isinstance(mgr, SubAgentManager)
        assert mgr.parent is agent
