"""测试 Skill 依赖验证机制"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.skills.activator import SkillActivator
from loom.skills.models import SkillActivationMode, SkillDefinition
from loom.tools.registry import ToolRegistry


class TestDependencyValidation:
    """测试依赖验证"""

    @pytest.fixture
    def tool_registry(self):
        """创建 ToolRegistry"""
        registry = ToolRegistry()
        # 注册一些测试工具
        registry.register_function(lambda x: x, name="tool_a")
        registry.register_function(lambda x: x, name="tool_b")
        return registry

    @pytest.fixture
    def mock_llm_provider(self):
        """创建 Mock LLM Provider"""
        mock = Mock()
        mock.chat = AsyncMock(return_value=Mock(content="Test response"))
        return mock

    @pytest.fixture
    def activator(self, tool_registry, mock_llm_provider):
        """创建 SkillActivator"""
        return SkillActivator(
            llm_provider=mock_llm_provider,
            tool_registry=tool_registry,
        )

    def test_validate_dependencies_success(self, activator):
        """测试依赖验证成功"""
        skill = SkillDefinition(
            skill_id="test",
            name="Test",
            description="Test",
            instructions="Test",
            required_tools=["tool_a", "tool_b"],
        )

        valid, missing = activator.validate_dependencies(skill)
        assert valid is True
        assert missing == []

    def test_validate_dependencies_missing(self, activator):
        """测试依赖验证失败"""
        skill = SkillDefinition(
            skill_id="test",
            name="Test",
            description="Test",
            instructions="Test",
            required_tools=["tool_a", "tool_c"],  # tool_c 不存在
        )

        valid, missing = activator.validate_dependencies(skill)
        assert valid is False
        assert "tool_c" in missing

    def test_validate_dependencies_no_registry(self, mock_llm_provider):
        """测试无 tool_registry 时跳过验证"""
        activator = SkillActivator(llm_provider=mock_llm_provider, tool_registry=None)

        skill = SkillDefinition(
            skill_id="test",
            name="Test",
            description="Test",
            instructions="Test",
            required_tools=["tool_missing"],
        )

        valid, missing = activator.validate_dependencies(skill)
        assert valid is True  # 无 registry 时跳过验证
        assert missing == []

    @pytest.mark.asyncio
    async def test_activate_with_validation_success(self, activator):
        """测试带验证的激活成功"""
        skill = SkillDefinition(
            skill_id="test",
            name="Test",
            description="Test",
            instructions="Test instructions",
            required_tools=["tool_a"],
        )

        result = await activator.activate(skill)
        assert result.success is True
        assert result.skill_id == "test"
        assert result.mode == SkillActivationMode.INJECTION
        assert result.content is not None
        assert "Test instructions" in result.content

    @pytest.mark.asyncio
    async def test_activate_with_missing_tools(self, activator):
        """测试缺少工具时的激活失败"""
        skill = SkillDefinition(
            skill_id="test",
            name="Test",
            description="Test",
            instructions="Test",
            required_tools=["tool_missing"],
        )

        result = await activator.activate(skill)
        assert result.success is False
        assert result.error is not None
        assert "tool_missing" in result.error
        assert result.missing_tools == ["tool_missing"]
