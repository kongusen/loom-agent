"""
Tests for Database Skill Loader

测试数据库加载器的核心功能：
- CallbackSkillLoader 回调加载
- BundledTool 工具捆绑
- SkillWithTools 带工具加载
"""

import pytest

from loom.tools.skills.database_loader import (
    BundledTool,
    CallbackSkillLoader,
)


class TestBundledTool:
    """测试 BundledTool 数据模型"""

    def test_create_bundled_tool(self):
        """测试创建捆绑工具"""
        tool = BundledTool(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
        )
        assert tool.name == "test_tool"
        assert tool.source == "bundled"

    def test_bundled_tool_with_implementation(self):
        """测试带实现代码的工具"""
        tool = BundledTool(
            name="calc",
            description="Calculator",
            parameters={"type": "object"},
            implementation="result = a + b",
        )
        assert tool.implementation == "result = a + b"


class TestCallbackSkillLoader:
    """测试 CallbackSkillLoader"""

    @pytest.fixture
    def mock_skill_data(self):
        """模拟 Skill 数据"""
        return {
            "skill_id": "test_skill",
            "name": "Test Skill",
            "description": "A test skill",
            "instructions": "Do something",
            "required_tools": ["tool1"],
        }

    @pytest.mark.asyncio
    async def test_load_skill(self, mock_skill_data):
        """测试加载单个 Skill"""
        async def query_fn(skill_id: str):
            if skill_id == "test_skill":
                return mock_skill_data
            return None

        loader = CallbackSkillLoader(query_skill_fn=query_fn)
        skill = await loader.load_skill("test_skill")

        assert skill is not None
        assert skill.skill_id == "test_skill"
        assert skill.source == "database"

    @pytest.mark.asyncio
    async def test_load_skill_not_found(self):
        """测试加载不存在的 Skill"""
        async def query_fn(skill_id: str):
            return None

        loader = CallbackSkillLoader(query_skill_fn=query_fn)
        skill = await loader.load_skill("nonexistent")

        assert skill is None

    @pytest.mark.asyncio
    async def test_list_all_skills(self, mock_skill_data):
        """测试列出所有 Skills"""
        async def query_fn(skill_id: str):
            return mock_skill_data

        async def query_all_fn():
            return [mock_skill_data]

        loader = CallbackSkillLoader(
            query_skill_fn=query_fn,
            query_all_fn=query_all_fn,
        )
        skills = await loader.list_skills()

        assert len(skills) == 1
        assert skills[0].skill_id == "test_skill"
