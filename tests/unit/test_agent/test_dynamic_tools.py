"""
测试 Agent 动态工具列表 - Phase 3: 12.5.6
验证工具的动态管理和配置过滤
"""

import pytest

from loom.agent.core import Agent
from loom.config.agent import AgentConfig
from loom.providers.llm.mock import MockLLMProvider
from loom.skills.registry import SkillRegistry
from loom.tools.registry import ToolRegistry


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
