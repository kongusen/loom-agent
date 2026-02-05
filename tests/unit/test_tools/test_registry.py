"""
Unit tests for CapabilityRegistry
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.tools.registry import (
    CapabilityRegistry,
    CapabilitySet,
    ValidationResult,
)


class TestCapabilitySet:
    """Tests for CapabilitySet dataclass"""

    def test_empty_capability_set(self):
        """Test empty CapabilitySet"""
        cap_set = CapabilitySet()
        assert len(cap_set) == 0
        assert cap_set.is_empty()

    def test_capability_set_with_tools(self):
        """Test CapabilitySet with tools"""
        cap_set = CapabilitySet(tools=[{"name": "tool1"}, {"name": "tool2"}])
        assert len(cap_set) == 2
        assert not cap_set.is_empty()

    def test_capability_set_with_skills(self):
        """Test CapabilitySet with skills"""
        cap_set = CapabilitySet(skill_ids=["skill1", "skill2", "skill3"])
        assert len(cap_set) == 3
        assert not cap_set.is_empty()

    def test_capability_set_with_both(self):
        """Test CapabilitySet with both tools and skills"""
        cap_set = CapabilitySet(tools=[{"name": "tool1"}], skill_ids=["skill1", "skill2"])
        assert len(cap_set) == 3
        assert not cap_set.is_empty()


class TestValidationResult:
    """Tests for ValidationResult dataclass"""

    def test_valid_result(self):
        """Test valid ValidationResult"""
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert bool(result) is True
        assert len(result.missing_tools) == 0

    def test_invalid_result(self):
        """Test invalid ValidationResult"""
        result = ValidationResult(
            is_valid=False, missing_tools=["tool1", "tool2"], error="Missing tools"
        )
        assert not result.is_valid
        assert bool(result) is False
        assert len(result.missing_tools) == 2
        assert result.error == "Missing tools"


class TestCapabilityRegistry:
    """Tests for CapabilityRegistry"""

    def test_init_with_no_components(self):
        """Test initialization with no components"""
        registry = CapabilityRegistry()
        assert registry._tool_manager is None
        assert registry._skill_registry is None
        assert registry._skill_activator is None

    def test_init_with_components(self):
        """Test initialization with components"""
        tool_manager = Mock()
        skill_registry = Mock()
        skill_activator = Mock()

        registry = CapabilityRegistry(
            sandbox_manager=tool_manager,
            skill_registry=skill_registry,
            skill_activator=skill_activator,
        )

        assert registry._tool_manager is tool_manager
        assert registry._skill_registry is skill_registry
        assert registry._skill_activator is skill_activator

    @pytest.mark.asyncio
    async def test_find_relevant_capabilities_no_components(self):
        """Test find_relevant_capabilities with no components"""
        registry = CapabilityRegistry()
        result = await registry.find_relevant_capabilities("test task")

        assert isinstance(result, CapabilitySet)
        assert len(result.tools) == 0
        assert len(result.skill_ids) == 0
        assert result.is_empty()

    @pytest.mark.asyncio
    async def test_find_relevant_capabilities_with_tools(self):
        """Test find_relevant_capabilities with tools"""
        tool_manager = Mock()
        mock_tool_def = Mock()
        mock_tool_def.name = "test_tool"
        mock_tool_def.description = "Test tool description"
        mock_tool_def.input_schema = {"type": "object"}
        tool_manager.list_tools.return_value = [mock_tool_def]

        registry = CapabilityRegistry(sandbox_manager=tool_manager)
        result = await registry.find_relevant_capabilities("test task")

        assert len(result.tools) == 1
        assert result.tools[0]["name"] == "test_tool"
        assert result.tools[0]["description"] == "Test tool description"
        tool_manager.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_relevant_capabilities_with_skills(self):
        """Test find_relevant_capabilities with skills (list_skills_async)"""
        skill_registry = Mock()
        skill_registry.list_skills_async = AsyncMock(return_value=["skill1", "skill2"])

        registry = CapabilityRegistry(skill_registry=skill_registry)
        result = await registry.find_relevant_capabilities("test task")

        assert len(result.skill_ids) == 2
        assert "skill1" in result.skill_ids
        assert "skill2" in result.skill_ids
        skill_registry.list_skills_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_relevant_capabilities_with_both(self):
        """Test find_relevant_capabilities with both tools and skills"""
        tool_manager = Mock()
        mock_tool_def = Mock()
        mock_tool_def.name = "test_tool"
        mock_tool_def.description = "Test tool"
        mock_tool_def.input_schema = {}
        tool_manager.list_tools.return_value = [mock_tool_def]

        skill_registry = Mock()
        skill_registry.list_skills_async = AsyncMock(return_value=["skill1"])

        registry = CapabilityRegistry(
            sandbox_manager=tool_manager,
            skill_registry=skill_registry,
        )
        result = await registry.find_relevant_capabilities("test task")

        assert len(result.tools) == 1
        assert len(result.skill_ids) == 1
        assert not result.is_empty()

    @pytest.mark.asyncio
    async def test_find_relevant_capabilities_tool_manager_exception(self):
        """Test find_relevant_capabilities when tool manager raises exception"""
        tool_manager = Mock()
        tool_manager.list_tools.side_effect = Exception("Tool error")

        registry = CapabilityRegistry(sandbox_manager=tool_manager)
        result = await registry.find_relevant_capabilities("test task")

        assert len(result.tools) == 0

    @pytest.mark.asyncio
    async def test_find_relevant_capabilities_skill_registry_exception(self):
        """Test find_relevant_capabilities when skill registry raises exception"""
        skill_registry = Mock()
        skill_registry.list_skills_async = AsyncMock(side_effect=Exception("Skill error"))

        registry = CapabilityRegistry(skill_registry=skill_registry)
        result = await registry.find_relevant_capabilities("test task")

        assert len(result.skill_ids) == 0

    @pytest.mark.asyncio
    async def test_validate_skill_dependencies_no_skill_registry(self):
        """Test validate_skill_dependencies with no skill registry"""
        registry = CapabilityRegistry()
        result = await registry.validate_skill_dependencies("test_skill")

        assert not result.is_valid
        assert "SkillRegistry not available" in result.error

    @pytest.mark.asyncio
    async def test_validate_skill_dependencies_skill_not_found(self):
        """Test validate_skill_dependencies when skill not found"""
        skill_registry = Mock()
        skill_registry.get_skill = AsyncMock(return_value=None)

        registry = CapabilityRegistry(skill_registry=skill_registry)
        result = await registry.validate_skill_dependencies("test_skill")

        assert not result.is_valid
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_validate_skill_dependencies_no_required_tools(self):
        """Test validate_skill_dependencies when skill has no required tools"""
        skill_registry = Mock()
        skill_registry.get_skill = AsyncMock(
            return_value={
                "function": {"name": "test_skill"},
                "_metadata": {},
            }
        )

        registry = CapabilityRegistry(skill_registry=skill_registry)
        result = await registry.validate_skill_dependencies("test_skill")

        assert result.is_valid

    @pytest.mark.asyncio
    async def test_validate_skill_dependencies_all_tools_available(self):
        """Test validate_skill_dependencies when all tools are available"""
        skill_registry = Mock()
        skill_registry.get_skill = AsyncMock(
            return_value={
                "function": {"name": "test_skill"},
                "_metadata": {"required_tools": ["tool1", "tool2"]},
            }
        )

        tool_manager = Mock()
        mock_tool1 = Mock()
        mock_tool1.name = "tool1"
        mock_tool2 = Mock()
        mock_tool2.name = "tool2"
        tool_manager.list_tools.return_value = [mock_tool1, mock_tool2]

        registry = CapabilityRegistry(
            sandbox_manager=tool_manager,
            skill_registry=skill_registry,
        )
        result = await registry.validate_skill_dependencies("test_skill")

        assert result.is_valid
        assert len(result.missing_tools) == 0

    @pytest.mark.asyncio
    async def test_validate_skill_dependencies_missing_tools(self):
        """Test validate_skill_dependencies when tools are missing"""
        skill_registry = Mock()
        skill_registry.get_skill = AsyncMock(
            return_value={
                "function": {"name": "test_skill"},
                "_metadata": {"required_tools": ["tool1", "tool2", "tool3"]},
            }
        )

        tool_manager = Mock()
        mock_tool1 = Mock()
        mock_tool1.name = "tool1"
        tool_manager.list_tools.return_value = [mock_tool1]

        registry = CapabilityRegistry(
            sandbox_manager=tool_manager,
            skill_registry=skill_registry,
        )
        result = await registry.validate_skill_dependencies("test_skill")

        assert not result.is_valid
        assert len(result.missing_tools) == 2
        assert "tool2" in result.missing_tools
        assert "tool3" in result.missing_tools
        assert "Missing required tools" in result.error

    @pytest.mark.asyncio
    async def test_validate_skill_dependencies_no_tool_manager(self):
        """Test validate_skill_dependencies when tool manager not available"""
        skill_registry = Mock()
        skill_registry.get_skill = AsyncMock(
            return_value={
                "function": {"name": "test_skill"},
                "_metadata": {"required_tools": ["tool1"]},
            }
        )

        registry = CapabilityRegistry(skill_registry=skill_registry)
        result = await registry.validate_skill_dependencies("test_skill")

        assert not result.is_valid
        assert "ToolManager not available" in result.error
        assert "tool1" in result.missing_tools

    @pytest.mark.asyncio
    async def test_validate_skill_dependencies_get_skill_exception(self):
        """Test validate_skill_dependencies when get_skill raises exception"""
        skill_registry = Mock()
        skill_registry.get_skill = AsyncMock(side_effect=Exception("Database error"))

        registry = CapabilityRegistry(skill_registry=skill_registry)
        result = await registry.validate_skill_dependencies("test_skill")

        assert not result.is_valid
        assert "Failed to get skill" in result.error

    @pytest.mark.asyncio
    async def test_validate_skill_dependencies_list_tools_exception(self):
        """Test validate_skill_dependencies when list_tools raises exception"""
        skill_registry = Mock()
        skill_registry.get_skill = AsyncMock(
            return_value={
                "function": {"name": "test_skill"},
                "_metadata": {"required_tools": ["tool1"]},
            }
        )

        tool_manager = Mock()
        tool_manager.list_tools.side_effect = Exception("Tool error")

        registry = CapabilityRegistry(
            sandbox_manager=tool_manager,
            skill_registry=skill_registry,
        )
        result = await registry.validate_skill_dependencies("test_skill")

        assert not result.is_valid
        assert "Failed to get available tools" in result.error
