"""
测试 Agent Registry 继承 - Phase 3: 12.5.3
验证子节点正确继承父节点的 Registry
"""

import pytest

from loom.agent.core import Agent
from loom.config.agent import AgentConfig
from loom.runtime import Task
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
    return ToolRegistry()


class TestRegistryInheritance:
    """测试 Registry 继承功能"""

    @pytest.mark.asyncio
    async def test_child_inherits_skill_registry(self, mock_llm, skill_registry, tool_registry):
        """测试子节点继承 skill_registry"""
        # 创建父 Agent
        parent = Agent(
            node_id="parent",
            llm_provider=mock_llm,
            skill_registry=skill_registry,
            tool_registry=tool_registry,
        )

        # 创建子任务
        subtask = Task(
            task_id="child-task",
            action="execute",
            parameters={"content": "test task"},
        )

        # 创建子节点
        child = await parent._create_child_node(
            subtask=subtask,
            context_hints=[],
        )

        # 验证子节点继承了 skill_registry
        assert child.skill_registry is parent.skill_registry
        assert child.skill_registry is skill_registry

    @pytest.mark.asyncio
    async def test_child_inherits_tool_registry(self, mock_llm, skill_registry, tool_registry):
        """测试子节点继承 tool_registry"""
        parent = Agent(
            node_id="parent",
            llm_provider=mock_llm,
            skill_registry=skill_registry,
            tool_registry=tool_registry,
        )

        subtask = Task(
            task_id="child-task",
            action="execute",
            parameters={"content": "test task"},
        )

        child = await parent._create_child_node(
            subtask=subtask,
            context_hints=[],
        )

        # 验证子节点继承了 tool_registry
        assert child.tool_registry is parent.tool_registry
        assert child.tool_registry is tool_registry

    @pytest.mark.asyncio
    async def test_child_inherits_config(self, mock_llm, skill_registry, tool_registry):
        """测试子节点继承配置"""
        parent_config = AgentConfig(
            enabled_skills={"pdf", "docx"},
            extra_tools={"read_file"},
        )

        parent = Agent(
            node_id="parent",
            llm_provider=mock_llm,
            skill_registry=skill_registry,
            tool_registry=tool_registry,
            config=parent_config,
        )

        subtask = Task(
            task_id="child-task",
            action="execute",
            parameters={"content": "test task"},
        )

        child = await parent._create_child_node(
            subtask=subtask,
            context_hints=[],
        )

        # 验证子节点继承了配置
        assert child.config.enabled_skills == {"pdf", "docx"}
        assert child.config.extra_tools == {"read_file"}

    @pytest.mark.asyncio
    async def test_child_config_modification(self, mock_llm, skill_registry, tool_registry):
        """测试子节点配置的增量修改"""
        parent_config = AgentConfig(
            enabled_skills={"pdf", "docx"},
            extra_tools={"read_file"},
        )

        parent = Agent(
            node_id="parent",
            llm_provider=mock_llm,
            skill_registry=skill_registry,
            tool_registry=tool_registry,
            config=parent_config,
        )

        subtask = Task(
            task_id="child-task",
            action="execute",
            parameters={"content": "test task"},
        )

        # 创建子节点，添加和移除 Skills
        child = await parent._create_child_node(
            subtask=subtask,
            context_hints=[],
            add_skills={"excel"},
            remove_skills={"docx"},
        )

        # 验证子节点的配置被正确修改
        assert child.config.enabled_skills == {"pdf", "excel"}
        assert "docx" not in child.config.enabled_skills
        assert child.config.extra_tools == {"read_file"}
