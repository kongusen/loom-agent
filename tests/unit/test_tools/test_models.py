"""
Skill Models Unit Tests

测试技能模型的核心功能
"""

from loom.tools.models import SkillDefinition


class TestSkillDefinition:
    """测试SkillDefinition数据类"""

    def test_skill_definition_init_minimal(self):
        """测试最小化初始化"""
        skill = SkillDefinition(
            skill_id="test-skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something",
        )

        assert skill.skill_id == "test-skill"
        assert skill.name == "Test Skill"
        assert skill.description == "A test skill"
        assert skill.instructions == "Do something"
        assert skill.references == {}
        assert skill.required_tools == []
        assert skill.metadata == {}
        assert skill.source == "unknown"

    def test_skill_definition_init_full(self):
        """测试完整初始化"""
        skill = SkillDefinition(
            skill_id="test-skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something",
            references={"ref.md": "# Reference"},
            required_tools=["tool1", "tool2"],
            metadata={"version": "1.0"},
            source="database",
        )

        assert skill.references == {"ref.md": "# Reference"}
        assert skill.required_tools == ["tool1", "tool2"]
        assert skill.metadata == {"version": "1.0"}
        assert skill.source == "database"

    def test_get_full_instructions_minimal(self):
        """测试获取最小化完整指令"""
        skill = SkillDefinition(
            skill_id="test-skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something",
        )

        result = skill.get_full_instructions()

        assert "# Skill: Test Skill" in result
        assert "**Description:** A test skill" in result
        assert "## Instructions" in result
        assert "Do something" in result
        # 不应该包含可选部分
        assert "Available References" not in result
        assert "Required Tools" not in result

    def test_get_full_instructions_full(self):
        """测试获取完整指令（包含所有可选部分）"""
        skill = SkillDefinition(
            skill_id="test-skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something",
            references={"ref.md": "# Reference"},
            required_tools=["tool1", "tool2"],
        )

        result = skill.get_full_instructions()

        assert "# Skill: Test Skill" in result
        assert "## Available References" in result
        assert "`ref.md`" in result
        assert "## Required Tools" in result
        assert "`tool1`" in result
        assert "`tool2`" in result

    def test_get_metadata_summary(self):
        """测试获取元数据摘要"""
        skill = SkillDefinition(
            skill_id="test-skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something",
            source="database",
        )

        result = skill.get_metadata_summary()

        assert result["skill_id"] == "test-skill"
        assert result["name"] == "Test Skill"
        assert result["description"] == "A test skill"

        assert result["source"] == "database"
        # 不应该包含完整指令
        assert "instructions" not in result
