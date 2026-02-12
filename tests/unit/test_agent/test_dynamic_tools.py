"""
测试 Agent 动态工具列表 - Phase 3: 12.5.6
验证工具的动态管理和配置过滤
"""

import pytest

from loom.agent.core import Agent
from loom.config.agent import AgentConfig
from loom.providers.llm.mock import MockLLMProvider
from loom.tools.core.registry import ToolRegistry
from loom.tools.core.sandbox import Sandbox
from loom.tools.core.sandbox_manager import SandboxToolManager, ToolScope
from loom.tools.mcp_types import MCPToolDefinition


@pytest.fixture
def mock_llm():
    """创建 Mock LLM Provider"""
    return MockLLMProvider()


@pytest.fixture
def tool_registry():
    """创建 Tool Registry"""
    registry = ToolRegistry()

    # 注册测试工具
    def tool_a():
        """工具 A"""
        return "A"

    def tool_b():
        """工具 B"""
        return "B"

    def tool_c():
        """工具 C"""
        return "C"

    registry.register_function(tool_a, "tool_a")
    registry.register_function(tool_b, "tool_b")
    registry.register_function(tool_c, "tool_c")

    return registry


@pytest.fixture
def sandbox_manager(tmp_path):
    """创建 Sandbox Tool Manager"""
    sandbox = Sandbox(tmp_path)
    manager = SandboxToolManager(sandbox)

    # 注册测试工具
    async def sandbox_tool_1(arg: str) -> str:
        """沙盒工具 1"""
        return f"sandbox_1: {arg}"

    async def sandbox_tool_2(arg: str) -> str:
        """沙盒工具 2"""
        return f"sandbox_2: {arg}"

    # 注册工具到 sandbox_manager
    import asyncio

    async def register_tools():
        await manager.register_tool(
            "sandbox_tool_1",
            sandbox_tool_1,
            MCPToolDefinition(
                name="sandbox_tool_1",
                description="沙盒工具 1",
                inputSchema={"type": "object", "properties": {"arg": {"type": "string"}}},
            ),
            ToolScope.SANDBOXED,
        )
        await manager.register_tool(
            "sandbox_tool_2",
            sandbox_tool_2,
            MCPToolDefinition(
                name="sandbox_tool_2",
                description="沙盒工具 2",
                inputSchema={"type": "object", "properties": {"arg": {"type": "string"}}},
            ),
            ToolScope.SANDBOXED,
        )

    asyncio.run(register_tools())

    return manager


class TestDynamicToolList:
    """测试动态工具列表功能"""

    def test_get_available_tools_base(self, mock_llm, tool_registry):
        """测试获取基础工具"""
        base_tools = [
            {
                "type": "function",
                "function": {
                    "name": "base_tool_1",
                    "description": "基础工具 1",
                    "parameters": {},
                },
            }
        ]

        agent = Agent(
            node_id="test-agent",
            llm_provider=mock_llm,
            tools=base_tools,
            tool_registry=tool_registry,
        )

        available = agent._get_available_tools()

        # 应该包含基础工具
        tool_names = [t.get("function", {}).get("name") for t in available]
        assert "base_tool_1" in tool_names

    def test_get_available_tools_with_extra(self, mock_llm, tool_registry):
        """测试获取额外配置的工具"""
        config = AgentConfig(extra_tools={"tool_a", "tool_b"})

        agent = Agent(
            node_id="test-agent",
            llm_provider=mock_llm,
            tool_registry=tool_registry,
            config=config,
        )

        available = agent._get_available_tools()

        # 应该包含额外配置的工具
        tool_names = [t.get("function", {}).get("name") for t in available]
        assert "tool_a" in tool_names
        assert "tool_b" in tool_names

    def test_get_available_tools_filter_disabled(self, mock_llm, tool_registry):
        """测试过滤禁用的工具"""
        base_tools = [
            {
                "type": "function",
                "function": {
                    "name": "tool_x",
                    "description": "工具 X",
                    "parameters": {},
                },
            }
        ]

        config = AgentConfig(
            extra_tools={"tool_a", "tool_b"},
            disabled_tools={"tool_a"},  # 禁用 tool_a
        )

        agent = Agent(
            node_id="test-agent",
            llm_provider=mock_llm,
            tools=base_tools,
            tool_registry=tool_registry,
            config=config,
        )

        available = agent._get_available_tools()

        # 应该包含 tool_x 和 tool_b，但不包含 tool_a
        tool_names = [t.get("function", {}).get("name") for t in available]
        assert "tool_x" in tool_names
        assert "tool_b" in tool_names
        assert "tool_a" not in tool_names

    def test_get_available_tools_with_sandbox_manager(self, mock_llm, sandbox_manager):
        """测试获取 sandbox_manager 中的工具（P0 验证）"""
        # 仅传入 sandbox_manager，不传 tool_registry
        agent = Agent(
            node_id="test-agent",
            llm_provider=mock_llm,
            sandbox_manager=sandbox_manager,
        )

        available = agent._get_available_tools()

        # 应该包含 sandbox_manager 中注册的工具
        tool_names = [t.get("function", {}).get("name") for t in available]
        assert "sandbox_tool_1" in tool_names
        assert "sandbox_tool_2" in tool_names

        # 验证工具定义格式正确
        sandbox_tool_1_def = next(
            (t for t in available if t.get("function", {}).get("name") == "sandbox_tool_1"),
            None,
        )
        assert sandbox_tool_1_def is not None
        assert sandbox_tool_1_def["type"] == "function"
        assert sandbox_tool_1_def["function"]["description"] == "沙盒工具 1"

    def test_get_available_tools_with_both_managers(self, mock_llm, tool_registry, sandbox_manager):
        """测试同时提供 sandbox_manager 和 tool_registry 时的工具合并（P2 验证）"""
        # 同时提供 sandbox_manager 和 tool_registry
        agent = Agent(
            node_id="test-agent",
            llm_provider=mock_llm,
            tool_registry=tool_registry,
            sandbox_manager=sandbox_manager,
        )

        available = agent._get_available_tools()
        tool_names = [t.get("function", {}).get("name") for t in available]

        # 应该包含来自 sandbox_manager 的工具
        assert "sandbox_tool_1" in tool_names
        assert "sandbox_tool_2" in tool_names

        # 验证工具不重复（去重逻辑）
        assert len(tool_names) == len(set(tool_names))
