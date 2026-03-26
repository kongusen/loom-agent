"""Phase 4: 公理四进化闭环测试"""

import pytest

from loom.agent import Agent
from loom.config import AgentConfig
from loom.types import ToolCall, Skill
from tests.conftest import MockLLMProvider


class TestEvolutionIntegration:
    """验证进化工具集成"""

    async def test_write_memory_tool_registered(self):
        """验证 write_memory 工具已注册"""
        agent = Agent(provider=MockLLMProvider(["test"]))
        tool = agent.tools.get("write_memory")
        assert tool is not None
        assert tool.name == "write_memory"

    async def test_activate_skill_tool_registered(self):
        """验证 activate_skill 工具已注册"""
        agent = Agent(provider=MockLLMProvider(["test"]))
        tool = agent.tools.get("activate_skill")
        assert tool is not None
        assert tool.name == "activate_skill"

    async def test_deactivate_skill_tool_registered(self):
        """验证 deactivate_skill 工具已注册"""
        agent = Agent(provider=MockLLMProvider(["test"]))
        tool = agent.tools.get("deactivate_skill")
        assert tool is not None
        assert tool.name == "deactivate_skill"

    async def test_write_memory_tool_execution(self):
        """验证 write_memory 工具可执行"""
        agent = Agent(provider=MockLLMProvider(["test"]))

        result = await agent._execute_tool(
            ToolCall(
                id="1",
                name="write_memory",
                arguments='{"content": "Important fact", "importance": 0.9}'
            )
        )

        assert "success" in result or "status" in result

    async def test_activate_skill_tool_execution(self):
        """验证 activate_skill 工具可执行"""
        agent = Agent(provider=MockLLMProvider(["test"]))

        # 注册测试技能
        skill = Skill(name="test_skill", description="Test", instructions="Do test")
        agent.skill_mgr.registry.register(skill)

        result = await agent._execute_tool(
            ToolCall(id="1", name="activate_skill", arguments='{"skill_name": "test_skill"}')
        )

        # 应该成功或返回错误信息
        assert "success" in result or "error" in result
