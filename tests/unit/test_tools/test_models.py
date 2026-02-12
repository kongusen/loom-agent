"""
Skill Models Unit Tests

测试技能模型的核心功能
"""

from loom.tools.skills.models import SkillDefinition


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
        assert skill.knowledge_domains == []
        assert skill.search_guidance == ""

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
            knowledge_domains=["product_docs", "faq"],
            search_guidance="使用 query(scope='knowledge') 查找文档。",
        )

        assert skill.references == {"ref.md": "# Reference"}
        assert skill.required_tools == ["tool1", "tool2"]
        assert skill.metadata == {"version": "1.0"}
        assert skill.source == "database"
        assert skill.knowledge_domains == ["product_docs", "faq"]
        assert skill.search_guidance == "使用 query(scope='knowledge') 查找文档。"

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
        assert "Knowledge Domains" not in result
        assert "Search Guidance" not in result

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


class TestSkillDefinitionKnowledge:
    """Skill-Knowledge 绑定字段测试"""

    def _make_skill(self, **kwargs):
        defaults = {
            "skill_id": "support",
            "name": "Customer Support",
            "description": "客户支持技能",
            "instructions": "处理客户问题。",
        }
        defaults.update(kwargs)
        return SkillDefinition(**defaults)

    def test_knowledge_domains_in_instructions(self):
        """knowledge_domains 出现在 get_full_instructions 输出中"""
        skill = self._make_skill(knowledge_domains=["product_docs", "faq"])
        result = skill.get_full_instructions()

        assert "## Knowledge Domains" in result
        assert "`product_docs`" in result
        assert "`faq`" in result

    def test_search_guidance_in_instructions(self):
        """search_guidance 出现在 get_full_instructions 输出中"""
        guidance = "使用 query(query=功能名, scope='knowledge') 查找文档。"
        skill = self._make_skill(search_guidance=guidance)
        result = skill.get_full_instructions()

        assert "## Search Guidance" in result
        assert guidance in result

    def test_both_fields_in_instructions(self):
        """同时设置 knowledge_domains 和 search_guidance"""
        guidance = "当用户询问产品功能时，使用 query(scope='knowledge')。"
        skill = self._make_skill(
            knowledge_domains=["docs"],
            search_guidance=guidance,
        )
        result = skill.get_full_instructions()

        assert "## Knowledge Domains" in result
        assert "`docs`" in result
        assert "## Search Guidance" in result
        assert guidance in result

    def test_empty_fields_not_in_instructions(self):
        """空字段不出现在输出中"""
        skill = self._make_skill()
        result = skill.get_full_instructions()

        assert "Knowledge Domains" not in result
        assert "Search Guidance" not in result

    def test_section_order(self):
        """验证 section 顺序：Tools → Knowledge Domains → Search Guidance"""
        skill = self._make_skill(
            required_tools=["query"],
            knowledge_domains=["docs"],
            search_guidance="搜索指引内容",
        )
        result = skill.get_full_instructions()

        tools_pos = result.index("Required Tools")
        domains_pos = result.index("Knowledge Domains")
        guidance_pos = result.index("Search Guidance")
        assert tools_pos < domains_pos < guidance_pos

    def test_metadata_summary_excludes_knowledge_fields(self):
        """get_metadata_summary 不包含 knowledge 详细字段"""
        skill = self._make_skill(
            knowledge_domains=["docs"],
            search_guidance="搜索指引",
        )
        summary = skill.get_metadata_summary()

        assert "knowledge_domains" not in summary
        assert "search_guidance" not in summary

    def test_multiline_search_guidance(self):
        """多行 search_guidance 正确输出"""
        guidance = (
            "当用户询问产品功能时，使用 query(scope='knowledge')。\n"
            "当用户报告错误时，使用 query(intent='troubleshooting')。\n"
            "当需要回忆对话时，使用 query(scope='memory')。"
        )
        skill = self._make_skill(search_guidance=guidance)
        result = skill.get_full_instructions()

        assert "troubleshooting" in result
        assert "scope='memory'" in result
