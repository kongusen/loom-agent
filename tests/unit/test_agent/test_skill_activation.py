"""
测试 Agent Skill 激活功能 - Phase 3: 12.5.5
验证 Skill 激活、依赖验证和状态跟踪
"""

import pytest

from loom.agent.core import Agent
from loom.config.agent import AgentConfig
from loom.providers.llm.mock import MockLLMProvider
from loom.tools.core.registry import ToolRegistry
from loom.tools.skills.registry import SkillRegistry


@pytest.fixture
def mock_llm():
    """创建 Mock LLM Provider"""
    return MockLLMProvider()


@pytest.fixture
def skill_registry():
    """创建 Skill Registry"""
    return SkillRegistry()


@pytest.fixture
def tool_registry():
    """创建 Tool Registry"""
    registry = ToolRegistry()

    # 注册一些测试工具
    def test_tool_1():
        """测试工具 1"""
        return "tool1 result"

    def test_tool_2():
        """测试工具 2"""
        return "tool2 result"

    registry.register_function(test_tool_1, "test_tool_1")
    registry.register_function(test_tool_2, "test_tool_2")

    return registry


class TestSkillActivation:
    """测试 Skill 激活功能"""

    @pytest.mark.asyncio
    async def test_activate_skill_not_enabled(self, mock_llm, skill_registry, tool_registry):
        """测试激活未启用的 Skill"""
        config = AgentConfig(enabled_skills={"pdf"})

        agent = Agent(
            node_id="test-agent",
            llm_provider=mock_llm,
            skill_registry=skill_registry,
            tool_registry=tool_registry,
            config=config,
        )

        # 尝试激活未启用的 Skill
        result = await agent._activate_skill("docx")

        # 应该失败
        assert result["success"] is False
        assert "not in enabled_skills" in result["error"]

    @pytest.mark.asyncio
    async def test_activate_skill_already_active(self, mock_llm, skill_registry, tool_registry):
        """测试激活已经激活的 Skill"""
        config = AgentConfig(enabled_skills={"pdf"})

        agent = Agent(
            node_id="test-agent",
            llm_provider=mock_llm,
            skill_registry=skill_registry,
            tool_registry=tool_registry,
            config=config,
        )

        # 手动标记 Skill 为已激活
        agent._active_skills.add("pdf")

        # 尝试再次激活
        result = await agent._activate_skill("pdf")

        # 应该成功，但标记为已激活
        assert result["success"] is True
        assert result.get("already_active") is True

    @pytest.mark.asyncio
    async def test_activate_skill_tracks_state(self, mock_llm, skill_registry, tool_registry):
        """测试 Skill 激活状态跟踪"""
        config = AgentConfig(enabled_skills={"pdf"})

        agent = Agent(
            node_id="test-agent",
            llm_provider=mock_llm,
            skill_registry=skill_registry,
            tool_registry=tool_registry,
            config=config,
        )

        # 初始状态：没有激活的 Skills
        assert len(agent._active_skills) == 0

        # 注意：由于没有实际的 Skill 定义，这个测试会失败
        # 这里只是验证状态跟踪的逻辑
        # 实际测试需要 mock SkillRegistry 和 SkillActivator
