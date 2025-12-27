"""
测试 loom.stdlib 标准库
"""

import pytest
import os
import tempfile
from loom.weave import create_agent, reset_app
from loom.stdlib.skills import CalculatorSkill, FileSystemSkill
from loom.stdlib.agents import CoderAgent, AnalystAgent
from loom.stdlib.crews import DebateCrew


@pytest.fixture(autouse=True)
def reset_global_app():
    """每个测试前重置全局 App"""
    reset_app()
    yield
    reset_app()


class TestSkills:
    """测试 Skills"""

    def test_calculator_skill_creation(self):
        """测试创建计算器技能"""
        skill = CalculatorSkill()
        assert skill.name == "calculator"
        assert skill.description == "执行数学计算"

    @pytest.mark.asyncio
    async def test_calculator_skill_get_tools(self):
        """测试计算器技能返回工具"""
        skill = CalculatorSkill()
        tools = skill.get_tools()
        assert len(tools) == 1
        assert tools[0].node_id == "calculator"

    @pytest.mark.asyncio
    async def test_calculator_skill_register(self):
        """测试计算器技能注册到 Agent"""
        agent = create_agent("test-agent")
        skill = CalculatorSkill()
        skill.register(agent)
        assert "calculator" in agent.known_tools
        assert len(agent.known_tools) == 1

    def test_filesystem_skill_creation(self):
        """测试创建文件系统技能"""
        skill = FileSystemSkill(base_dir="/tmp")
        assert skill.name == "filesystem"
        assert skill.base_dir == "/tmp"


class TestPrebuiltAgents:
    """测试预构建的 Agent"""

    @pytest.mark.asyncio
    async def test_coder_agent_creation(self):
        """测试创建编码员 Agent"""
        coder = CoderAgent("test-coder")
        assert coder.node_id == "test-coder"
        assert len(coder.known_tools) == 2  # read_file, write_file
        assert "read_file" in coder.known_tools
        assert "write_file" in coder.known_tools

    @pytest.mark.asyncio
    async def test_analyst_agent_creation(self):
        """测试创建分析师 Agent"""
        analyst = AnalystAgent("test-analyst")
        assert analyst.node_id == "test-analyst"
        assert len(analyst.known_tools) == 1  # calculator
        assert "calculator" in analyst.known_tools


class TestCrews:
    """测试团队模式"""

    @pytest.mark.asyncio
    async def test_debate_crew_creation(self):
        """测试创建辩论团队"""
        crew = DebateCrew("test-debate")
        assert crew.node_id == "test-debate"
        assert len(crew.agents) == 2
