"""
Tests for Skill Activator
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.skills.activator import SkillActivator


class TestSkillActivator:
    """Test suite for SkillActivator"""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider"""
        provider = AsyncMock()
        return provider

    @pytest.fixture
    def activator(self, mock_llm_provider):
        """Create a SkillActivator instance"""
        return SkillActivator(mock_llm_provider)

    @pytest.fixture
    def sample_skill_metadata(self):
        """Create sample skill metadata"""
        return [
            {"skill_id": "skill1", "name": "Code Writer", "description": "Writes code"},
            {"skill_id": "skill2", "name": "Data Analyzer", "description": "Analyzes data"},
            {"skill_id": "skill3", "name": "File Manager", "description": "Manages files"},
            {"skill_id": "skill4", "name": "API Caller", "description": "Calls APIs"},
            {"skill_id": "skill5", "name": "Debugger", "description": "Debugs code"},
        ]

    def test_init(self, activator, mock_llm_provider):
        """Test initialization"""
        assert activator.llm_provider is mock_llm_provider

    @pytest.mark.asyncio
    async def test_find_relevant_skills_empty_metadata(self, activator):
        """Test with empty skill metadata"""
        result = await activator.find_relevant_skills("test task", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_find_relevant_skills_none_response(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test when LLM returns NONE"""
        mock_response = MagicMock()
        mock_response.content = "NONE"
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "test task", sample_skill_metadata
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_find_relevant_skills_single_skill(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test finding a single relevant skill"""
        mock_response = MagicMock()
        mock_response.content = "1"
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "write code", sample_skill_metadata
        )

        assert result == ["skill1"]

    @pytest.mark.asyncio
    async def test_find_relevant_skills_multiple_skills(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test finding multiple relevant skills"""
        mock_response = MagicMock()
        mock_response.content = "1, 3, 5"
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "complex task", sample_skill_metadata
        )

        assert result == ["skill1", "skill3", "skill5"]

    @pytest.mark.asyncio
    async def test_find_relevant_skills_custom_max(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test with custom max_skills limit"""
        mock_response = MagicMock()
        mock_response.content = "1, 2, 3"
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "test task", sample_skill_metadata, max_skills=2
        )

        # The activator doesn't enforce the max_skills limit on LLM response,
        # it just passes it to the prompt
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_find_relevant_skills_with_spaces(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test parsing with extra spaces in response"""
        mock_response = MagicMock()
        mock_response.content = " 1 ,  3  , 5 "
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "test task", sample_skill_metadata
        )

        assert result == ["skill1", "skill3", "skill5"]

    @pytest.mark.asyncio
    async def test_find_relevant_skills_invalid_indices(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test handling invalid indices in response"""
        mock_response = MagicMock()
        mock_response.content = "1, invalid, 3, 999"
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "test task", sample_skill_metadata
        )

        # Should only include valid indices
        assert result == ["skill1", "skill3"]

    @pytest.mark.asyncio
    async def test_find_relevant_skills_out_of_range_indices(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test handling out of range indices"""
        mock_response = MagicMock()
        mock_response.content = "0, 1, 10"  # 0 is invalid (1-based), 10 is out of range
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "test task", sample_skill_metadata
        )

        # Only valid index should be included
        assert result == ["skill1"]

    @pytest.mark.asyncio
    async def test_find_relevant_skills_error_fallback(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test fallback behavior when LLM fails"""
        mock_llm_provider.chat = AsyncMock(side_effect=Exception("LLM error"))

        result = await activator.find_relevant_skills(
            "test task", sample_skill_metadata, max_skills=3
        )

        # Should return first 3 skills as fallback
        assert result == ["skill1", "skill2", "skill3"]

    @pytest.mark.asyncio
    async def test_find_relevant_skills_none_metadata(
        self, activator, mock_llm_provider
    ):
        """Test with None as skill metadata"""
        result = await activator.find_relevant_skills("test task", None)
        assert result == []

    @pytest.mark.asyncio
    async def test_find_relevant_skills_duplicate_indices(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test handling duplicate indices in response"""
        mock_response = MagicMock()
        mock_response.content = "1, 1, 3, 3"
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "test task", sample_skill_metadata
        )

        # Should return unique skills
        assert result == ["skill1", "skill1", "skill3", "skill3"]

    @pytest.mark.asyncio
    async def test_find_relevant_skills_prompt_formatting(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test that prompt is formatted correctly"""
        mock_response = MagicMock()
        mock_response.content = "1"
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        await activator.find_relevant_skills("write code", sample_skill_metadata)

        # Check that chat was called
        assert mock_llm_provider.chat.called

        # Get the call arguments
        call_args = mock_llm_provider.chat.call_args
        messages = call_args[0][0]

        # Verify message structure
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "write code" in messages[0]["content"]
        assert "Code Writer" in messages[0]["content"]
        assert "Data Analyzer" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_find_relevant_skills_all_skills(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test when all skills are selected"""
        mock_response = MagicMock()
        mock_response.content = "1, 2, 3, 4, 5"
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "test task", sample_skill_metadata
        )

        assert result == ["skill1", "skill2", "skill3", "skill4", "skill5"]

    @pytest.mark.asyncio
    async def test_find_relevant_skills_case_insensitive_none(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test that NONE check is case insensitive"""
        mock_response = MagicMock()
        mock_response.content = "none"
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "test task", sample_skill_metadata
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_find_relevant_skills_with_newlines(
        self, activator, mock_llm_provider, sample_skill_metadata
    ):
        """Test handling newlines in response"""
        mock_response = MagicMock()
        mock_response.content = "1\n,\n3"
        mock_llm_provider.chat = AsyncMock(return_value=mock_response)

        result = await activator.find_relevant_skills(
            "test task", sample_skill_metadata
        )

        # Should parse correctly despite newlines
        assert result == ["skill1", "skill3"]
