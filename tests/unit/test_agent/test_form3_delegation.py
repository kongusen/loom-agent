"""
Unit tests for Form 3 Delegation (SkillAgentNode delegation)

Tests the fix for Form 3 delegation path where _active_skill_nodes
should be checked when target_agent_id is not in available_agents.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.agent.core import Agent
from loom.agent.skill_node import SkillAgentNode
from loom.protocol.task import Task, TaskStatus
from loom.skills.models import SkillDefinition


class TestForm3Delegation:
    """Tests for Form 3 delegation to SkillAgentNode"""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider"""
        provider = MagicMock()
        provider.chat = AsyncMock()
        provider.stream_chat = AsyncMock()
        return provider

    @pytest.fixture
    def sample_skill_definition(self):
        """Create a sample skill definition for Form 3"""
        return SkillDefinition(
            skill_id="code_reviewer",
            name="Code Reviewer",
            description="Multi-turn code review assistant",
            instructions="You are a code review expert. Provide detailed feedback.",
            activation_criteria="code review with discussion",
            scripts={},
            required_tools=["read_file"],
            metadata={"multi_turn": True}
        )

    @pytest.fixture
    def mock_skill_node(self, sample_skill_definition, mock_llm_provider):
        """Create a mock SkillAgentNode"""
        node = SkillAgentNode(
            skill_id="code_reviewer",
            skill_definition=sample_skill_definition,
            llm_provider=mock_llm_provider
        )

        # Mock execute_task to return a successful result
        async def mock_execute(task):
            task.status = TaskStatus.COMPLETED
            task.result = {"content": "Code review completed successfully"}
            return task

        node.execute_task = AsyncMock(side_effect=mock_execute)
        return node

    @pytest.fixture
    def agent_with_skill_node(self, mock_llm_provider, mock_skill_node):
        """Create an Agent with a SkillAgentNode in _active_skill_nodes"""
        agent = Agent(
            node_id="test_agent",
            llm_provider=mock_llm_provider,
            system_prompt="Test agent",
            require_done_tool=False
        )

        # Add the skill node to _active_skill_nodes (simulating Form 3 activation)
        agent._active_skill_nodes = [mock_skill_node]

        return agent

    @pytest.mark.asyncio
    async def test_delegate_to_skill_node_by_node_id(
        self, agent_with_skill_node, mock_skill_node
    ):
        """Test delegation to SkillAgentNode using node_id"""
        agent = agent_with_skill_node

        # Execute delegation to the skill node
        result = await agent._execute_delegate_task(
            target_agent_id="skill_code_reviewer",  # node_id format
            subtask="Review this authentication code",
            parent_task_id="parent_task_123",
            session_id="session_456"
        )

        # Verify delegation succeeded
        assert "Code review completed successfully" in result
        assert mock_skill_node.execute_task.called

        # Verify the delegated task was created correctly
        call_args = mock_skill_node.execute_task.call_args
        delegated_task = call_args[0][0]
        assert delegated_task.parameters["content"] == "Review this authentication code"
        assert delegated_task.parent_task_id == "parent_task_123"
        assert delegated_task.session_id == "session_456"

    @pytest.mark.asyncio
    async def test_delegate_to_skill_node_by_skill_id(
        self, agent_with_skill_node, mock_skill_node
    ):
        """Test delegation to SkillAgentNode using skill_id"""
        agent = agent_with_skill_node

        # Execute delegation using skill_id
        result = await agent._execute_delegate_task(
            target_agent_id="code_reviewer",  # skill_id
            subtask="Review error handling",
            parent_task_id="parent_task_789"
        )

        # Verify delegation succeeded
        assert "Code review completed successfully" in result
        assert mock_skill_node.execute_task.called

    @pytest.mark.asyncio
    async def test_delegate_skill_node_not_found(
        self, agent_with_skill_node
    ):
        """Test delegation fails gracefully when skill node not found"""
        agent = agent_with_skill_node

        # Try to delegate to non-existent skill node
        result = await agent._execute_delegate_task(
            target_agent_id="non_existent_skill",
            subtask="Some task",
            parent_task_id="parent_task_999"
        )

        # Verify error message
        assert "not found in available_agents or active_skill_nodes" in result

    @pytest.mark.asyncio
    async def test_delegate_skill_node_execution_error(
        self, agent_with_skill_node, mock_skill_node
    ):
        """Test delegation handles skill node execution errors"""
        agent = agent_with_skill_node

        # Mock skill node to raise an error
        mock_skill_node.execute_task = AsyncMock(
            side_effect=Exception("Skill execution failed")
        )

        # Execute delegation
        result = await agent._execute_delegate_task(
            target_agent_id="skill_code_reviewer",
            subtask="Review code",
            parent_task_id="parent_task_error"
        )

        # Verify error is handled
        assert "Skill node delegation error" in result
        assert "Skill execution failed" in result

    @pytest.mark.asyncio
    async def test_delegate_prefers_available_agents_over_skill_nodes(
        self, mock_llm_provider, mock_skill_node
    ):
        """Test that available_agents takes precedence over skill nodes"""
        # Create a mock agent for available_agents
        mock_available_agent = MagicMock()
        async def mock_execute(task):
            task.status = TaskStatus.COMPLETED
            task.result = {"content": "Available agent result"}
            return task
        mock_available_agent.execute_task = AsyncMock(side_effect=mock_execute)

        # Create agent with both available_agents and skill nodes
        agent = Agent(
            node_id="test_agent",
            llm_provider=mock_llm_provider,
            system_prompt="Test agent",
            available_agents={"code_reviewer": mock_available_agent},
            require_done_tool=False
        )
        agent._active_skill_nodes = [mock_skill_node]

        # Delegate using an ID that exists in both
        result = await agent._execute_delegate_task(
            target_agent_id="code_reviewer",
            subtask="Review code",
            parent_task_id="parent_task_precedence"
        )

        # Verify available_agents was used (Tier 1), not skill nodes (Tier 2)
        assert "Available agent result" in result
        assert mock_available_agent.execute_task.called
        assert not mock_skill_node.execute_task.called
