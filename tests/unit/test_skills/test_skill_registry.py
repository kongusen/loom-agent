"""
Skill Registry Unit Tests

测试技能注册表功能
"""

import pytest

from loom.skills.skill_registry import SkillRegistry


class TestSkillRegistryInit:
    """测试SkillRegistry初始化"""

    def test_skill_registry_init(self):
        """测试基本初始化"""
        registry = SkillRegistry()

        assert registry._skills == {}
        assert isinstance(registry._skills, dict)


class TestRegisterSkill:
    """测试注册技能"""

    def test_register_skill_basic(self):
        """测试基本技能注册"""
        registry = SkillRegistry()

        def test_handler(arg: str) -> str:
            return f"Result: {arg}"

        skill_def = registry.register_skill(
            name="test_skill",
            description="A test skill",
            parameters={"type": "object", "properties": {"arg": {"type": "string"}}},
            handler=test_handler,
        )

        assert skill_def["type"] == "function"
        assert skill_def["function"]["name"] == "test_skill"
        assert skill_def["function"]["description"] == "A test skill"
        assert skill_def["_handler"] == test_handler
        assert skill_def["_source"] == "python"
        assert skill_def["_ephemeral"] == 0

    def test_register_skill_with_source(self):
        """测试注册带来源的技能"""
        registry = SkillRegistry()

        skill_def = registry.register_skill(
            name="mcp_skill",
            description="An MCP skill",
            parameters={},
            handler=lambda: None,
            source="mcp",
        )

        assert skill_def["_source"] == "mcp"


class TestGetSkill:
    """测试获取技能"""

    def test_get_skill_exists(self):
        """测试获取存在的技能"""
        registry = SkillRegistry()
        registry.register_skill(
            name="test_skill",
            description="A test skill",
            parameters={},
            handler=lambda: None,
        )

        skill = registry.get_skill("test_skill")

        assert skill is not None
        assert skill["function"]["name"] == "test_skill"

    def test_get_skill_not_exists(self):
        """测试获取不存在的技能"""
        registry = SkillRegistry()

        skill = registry.get_skill("non_existent")

        assert skill is None


class TestListSkills:
    """测试列出技能"""

    def test_list_skills_empty(self):
        """测试列出空技能列表"""
        registry = SkillRegistry()

        skills = registry.list_skills()

        assert skills == []

    def test_list_skills_multiple(self):
        """测试列出多个技能"""
        registry = SkillRegistry()
        registry.register_skill("skill1", "Skill 1", {}, lambda: None)
        registry.register_skill("skill2", "Skill 2", {}, lambda: None)

        skills = registry.list_skills()

        assert len(skills) == 2
        assert "skill1" in skills
        assert "skill2" in skills


class TestGetSkillsBySource:
    """测试按来源获取技能"""

    def test_get_skills_by_source_python(self):
        """测试获取Python技能"""
        registry = SkillRegistry()
        registry.register_skill("py_skill", "Python skill", {}, lambda: None, source="python")
        registry.register_skill("mcp_skill", "MCP skill", {}, lambda: None, source="mcp")

        python_skills = registry.get_skills_by_source("python")

        assert len(python_skills) == 1
        assert python_skills[0]["function"]["name"] == "py_skill"

    def test_get_skills_by_source_empty(self):
        """测试获取不存在来源的技能"""
        registry = SkillRegistry()
        registry.register_skill("py_skill", "Python skill", {}, lambda: None, source="python")

        http_skills = registry.get_skills_by_source("http")

        assert http_skills == []
