"""
测试 AgentConfig - 配置继承和增量修改
"""

from loom.config.agent import AgentConfig


class TestAgentConfig:
    """测试 AgentConfig 基本功能"""

    def test_default_config(self):
        """测试默认配置"""
        config = AgentConfig()
        assert config.enabled_skills == set()
        assert config.disabled_skills == set()
        assert config.extra_tools == set()
        assert config.disabled_tools == set()
        assert config.skill_activation_mode == "hybrid"

    def test_custom_config(self):
        """测试自定义配置"""
        config = AgentConfig(
            enabled_skills={"pdf", "docx"},
            extra_tools={"read_file", "write_file"},
            skill_activation_mode="explicit",
        )
        assert config.enabled_skills == {"pdf", "docx"}
        assert config.extra_tools == {"read_file", "write_file"}
        assert config.skill_activation_mode == "explicit"


class TestAgentConfigInheritance:
    """测试 AgentConfig 继承功能"""

    def test_inherit_basic(self):
        """测试基本继承"""
        parent = AgentConfig(
            enabled_skills={"pdf", "docx"},
            extra_tools={"read_file"},
        )
        child = AgentConfig.inherit(parent)

        # 子配置应该继承父配置
        assert child.enabled_skills == {"pdf", "docx"}
        assert child.extra_tools == {"read_file"}

    def test_inherit_add_skills(self):
        """测试添加 Skills"""
        parent = AgentConfig(enabled_skills={"pdf", "docx"})
        child = AgentConfig.inherit(parent, add_skills={"excel"})

        # 子配置应该包含父的 + 新增的
        assert child.enabled_skills == {"pdf", "docx", "excel"}

    def test_inherit_remove_skills(self):
        """测试移除 Skills"""
        parent = AgentConfig(enabled_skills={"pdf", "docx", "excel"})
        child = AgentConfig.inherit(parent, remove_skills={"docx"})

        # 子配置应该移除指定的 Skill
        assert child.enabled_skills == {"pdf", "excel"}
        assert "docx" not in child.enabled_skills

    def test_inherit_add_and_remove_skills(self):
        """测试同时添加和移除 Skills"""
        parent = AgentConfig(enabled_skills={"pdf", "docx"})
        child = AgentConfig.inherit(parent, add_skills={"excel", "ppt"}, remove_skills={"docx"})

        # 应该先添加再移除
        assert child.enabled_skills == {"pdf", "excel", "ppt"}
        assert "docx" not in child.enabled_skills
