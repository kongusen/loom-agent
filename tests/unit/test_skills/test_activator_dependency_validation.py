"""测试 Skill 依赖验证机制"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.protocol.mcp import MCPToolDefinition
from loom.skills.activator import SkillActivator
from loom.skills.models import SkillActivationMode, SkillDefinition
from loom.tools.registry import ToolRegistry
from loom.tools.sandbox import Sandbox
from loom.tools.sandbox_manager import SandboxToolManager, ToolScope


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

    @pytest.fixture
    def tool_manager(self, tmp_path):
        """创建 SandboxToolManager（P1 验证）"""
        sandbox = Sandbox(tmp_path)
        manager = SandboxToolManager(sandbox)

        # 注册测试工具
        async def tool_x(arg: str) -> str:
            return f"x: {arg}"

        async def tool_y(arg: str) -> str:
            return f"y: {arg}"

        # 同步注册工具
        import asyncio

        async def register_tools():
            await manager.register_tool(
                "tool_x",
                tool_x,
                MCPToolDefinition(
                    name="tool_x",
                    description="Tool X",
                    inputSchema={"type": "object", "properties": {"arg": {"type": "string"}}},
                ),
                ToolScope.SANDBOXED,
            )
            await manager.register_tool(
                "tool_y",
                tool_y,
                MCPToolDefinition(
                    name="tool_y",
                    description="Tool Y",
                    inputSchema={"type": "object", "properties": {"arg": {"type": "string"}}},
                ),
                ToolScope.SANDBOXED,
            )

        asyncio.run(register_tools())
        return manager

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

    def test_validate_dependencies_with_tool_manager_success(
        self, tool_manager, mock_llm_provider
    ):
        """测试使用 tool_manager 的依赖验证成功（P1 验证）"""
        # 仅提供 tool_manager，不提供 tool_registry
        activator = SkillActivator(
            llm_provider=mock_llm_provider,
            tool_manager=tool_manager,
        )

        skill = SkillDefinition(
            skill_id="test",
            name="Test",
            description="Test",
            instructions="Test",
            required_tools=["tool_x", "tool_y"],
        )

        valid, missing = activator.validate_dependencies(skill)
        assert valid is True
        assert missing == []

    def test_validate_dependencies_with_tool_manager_missing(
        self, tool_manager, mock_llm_provider
    ):
        """测试使用 tool_manager 的依赖验证失败（P1 验证）"""
        # 仅提供 tool_manager，不提供 tool_registry
        activator = SkillActivator(
            llm_provider=mock_llm_provider,
            tool_manager=tool_manager,
        )

        skill = SkillDefinition(
            skill_id="test",
            name="Test",
            description="Test",
            instructions="Test",
            required_tools=["tool_x", "tool_missing"],
        )

        valid, missing = activator.validate_dependencies(skill)
        assert valid is False
        assert "tool_missing" in missing
        assert "tool_x" not in missing

    def test_validate_dependencies_tool_manager_priority(
        self, tool_registry, tool_manager, mock_llm_provider
    ):
        """测试 tool_manager 优先于 tool_registry（P1 验证）"""
        # 同时提供 tool_manager 和 tool_registry
        activator = SkillActivator(
            llm_provider=mock_llm_provider,
            tool_registry=tool_registry,
            tool_manager=tool_manager,
        )

        # tool_x 在 tool_manager 中，但不在 tool_registry 中
        skill = SkillDefinition(
            skill_id="test",
            name="Test",
            description="Test",
            instructions="Test",
            required_tools=["tool_x"],
        )

        valid, missing = activator.validate_dependencies(skill)
        # 应该使用 tool_manager，因此 tool_x 应该被找到
        assert valid is True
        assert missing == []
