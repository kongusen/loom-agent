"""
Unit tests for SkillActivator extended functionality (Phase 2)
"""

from unittest.mock import Mock

from loom.skills.activator import SkillActivator
from loom.skills.models import SkillActivationMode, SkillDefinition


class TestSkillActivatorPhase2:
    """Tests for Phase 2 SkillActivator extensions"""

    def test_determine_activation_mode_default_injection(self):
        """Test default activation mode is INJECTION"""
        activator = SkillActivator(llm_provider=Mock())

        skill = SkillDefinition(
            skill_id="test_skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something",
        )

        mode = activator.determine_activation_mode(skill)
        assert mode == SkillActivationMode.INJECTION

    def test_determine_activation_mode_with_scripts(self):
        """Test activation mode is COMPILATION when skill has scripts"""
        activator = SkillActivator(llm_provider=Mock())

        skill = SkillDefinition(
            skill_id="test_skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something",
            scripts={"script.py": "print('hello')"},
        )

        mode = activator.determine_activation_mode(skill)
        assert mode == SkillActivationMode.COMPILATION

    def test_determine_activation_mode_multi_turn(self):
        """Test activation mode is INSTANTIATION when multi_turn is True"""
        activator = SkillActivator(llm_provider=Mock())

        skill = SkillDefinition(
            skill_id="test_skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something",
            metadata={"multi_turn": True},
        )

        mode = activator.determine_activation_mode(skill)
        assert mode == SkillActivationMode.INSTANTIATION

    def test_determine_activation_mode_explicit(self):
        """Test explicit activation mode in metadata"""
        activator = SkillActivator(llm_provider=Mock())

        skill = SkillDefinition(
            skill_id="test_skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something",
            metadata={"activation_mode": "compilation"},
        )

        mode = activator.determine_activation_mode(skill)
        assert mode == SkillActivationMode.COMPILATION

    def test_activate_injection(self):
        """Test activate_injection returns full instructions"""
        activator = SkillActivator(llm_provider=Mock())

        skill = SkillDefinition(
            skill_id="test_skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something important",
        )

        result = activator.activate_injection(skill)

        assert isinstance(result, str)
        assert "Test Skill" in result
        assert "Do something important" in result

    def test_activate_instantiation(self):
        """Test activate_instantiation creates SkillAgentNode"""
        mock_llm = Mock()
        activator = SkillActivator(llm_provider=mock_llm)

        skill = SkillDefinition(
            skill_id="test_skill",
            name="Test Skill",
            description="A test skill",
            instructions="Do something",
            metadata={"multi_turn": True},
        )

        # Activate instantiation
        result = activator.activate_instantiation(skill)

        # Verify result is a SkillAgentNode
        from loom.agent.skill_node import SkillAgentNode

        assert isinstance(result, SkillAgentNode)
        assert result.skill_id == "test_skill"
        assert result.node_id == "skill_test_skill"
        assert result.node_type == "skill"
