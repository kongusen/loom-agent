"""
Unit tests for SkillAgentNode
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.agent.skill_node import SkillAgentNode
from loom.events.actions import TaskAction
from loom.protocol.task import Task, TaskStatus
from loom.skills.models import SkillDefinition


class TestSkillAgentNode:
    """Tests for SkillAgentNode"""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider"""
        provider = MagicMock()
        provider.chat = AsyncMock()
        return provider

    @pytest.fixture
    def sample_skill_definition(self):
        """Create a sample skill definition"""
        return SkillDefinition(
            skill_id="test_skill",
            name="Test Skill",
            description="A test skill for unit testing",
            instructions="You are a helpful assistant for testing.",
            metadata={"multi_turn": True},
        )

    def test_init(self, sample_skill_definition, mock_llm_provider):
        """Test SkillAgentNode initialization"""
        node = SkillAgentNode(
            skill_id="test_skill",
            skill_definition=sample_skill_definition,
            llm_provider=mock_llm_provider,
        )

        assert node.node_id == "skill_test_skill"
        assert node.node_type == "skill"
        assert node.skill_id == "test_skill"
        assert node.skill_definition == sample_skill_definition
        assert node.llm_provider == mock_llm_provider
        assert node.system_prompt == sample_skill_definition.get_full_instructions()

    @pytest.mark.asyncio
    async def test_execute_impl_success(self, sample_skill_definition, mock_llm_provider):
        """Test successful execution of _execute_impl"""
        # Setup mock LLM response
        mock_response = MagicMock()
        mock_response.content = "This is the LLM response"
        mock_llm_provider.chat.return_value = mock_response

        # Create node
        node = SkillAgentNode(
            skill_id="test_skill",
            skill_definition=sample_skill_definition,
            llm_provider=mock_llm_provider,
        )

        # Create task
        task = Task(
            task_id="task_1",
            source_agent="agent_1",
            target_agent="skill_test_skill",
            action=TaskAction.EXECUTE,
            parameters={"task": "Solve this problem"},
            session_id="session_1",
        )

        # Execute
        result_task = await node._execute_impl(task)

        # Verify
        assert result_task.status == TaskStatus.COMPLETED
        assert result_task.result["content"] == "This is the LLM response"
        assert result_task.result["skill_id"] == "test_skill"
        assert result_task.result["skill_name"] == "Test Skill"

        # Verify LLM was called with correct messages
        mock_llm_provider.chat.assert_called_once()
        call_args = mock_llm_provider.chat.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["role"] == "system"
        assert call_args[1]["role"] == "user"
        assert call_args[1]["content"] == "Solve this problem"

    @pytest.mark.asyncio
    async def test_execute_impl_missing_task_description(
        self, sample_skill_definition, mock_llm_provider
    ):
        """Test _execute_impl with missing task description"""
        node = SkillAgentNode(
            skill_id="test_skill",
            skill_definition=sample_skill_definition,
            llm_provider=mock_llm_provider,
        )

        # Create task without task description
        task = Task(
            task_id="task_1",
            source_agent="agent_1",
            target_agent="skill_test_skill",
            action=TaskAction.EXECUTE,
            parameters={},  # No "task" parameter
            session_id="session_1",
        )

        # Execute
        result_task = await node._execute_impl(task)

        # Verify
        assert result_task.status == TaskStatus.FAILED
        assert "error" in result_task.result
        assert "No task description" in result_task.result["error"]

    @pytest.mark.asyncio
    async def test_execute_impl_llm_error(self, sample_skill_definition, mock_llm_provider):
        """Test _execute_impl with LLM error"""
        # Setup mock LLM to raise an error
        mock_llm_provider.chat.side_effect = Exception("LLM API error")

        node = SkillAgentNode(
            skill_id="test_skill",
            skill_definition=sample_skill_definition,
            llm_provider=mock_llm_provider,
        )

        # Create task
        task = Task(
            task_id="task_1",
            source_agent="agent_1",
            target_agent="skill_test_skill",
            action=TaskAction.EXECUTE,
            parameters={"task": "Solve this problem"},
            session_id="session_1",
        )

        # Execute
        result_task = await node._execute_impl(task)

        # Verify
        assert result_task.status == TaskStatus.FAILED
        assert "error" in result_task.result
        assert "LLM API error" in result_task.result["error"]
        assert result_task.result["skill_id"] == "test_skill"
