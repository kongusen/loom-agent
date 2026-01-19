"""
Tests for Agent Workflow
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.orchestration.agent import Agent
from loom.orchestration.agent_workflow import AgentWorkflow
from loom.protocol import Task, TaskStatus
from loom.providers.llm.interface import LLMProvider


class TestAgentWorkflow:
    """Test suite for AgentWorkflow"""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider"""
        provider = MagicMock(spec=LLMProvider)
        provider.stream_chat = AsyncMock()
        return provider

    @pytest.fixture
    def mock_coordinator(self, mock_llm_provider):
        """Create a mock coordinator agent"""
        coordinator = MagicMock(spec=Agent)
        coordinator.node_id = "coordinator_1"
        coordinator.execute_task = AsyncMock()
        return coordinator

    @pytest.fixture
    def workflow(self, mock_coordinator):
        """Create a sample workflow"""
        return AgentWorkflow(
            workflow_id="test_workflow",
            coordinator_agent=mock_coordinator,
            description="Test agent workflow",
        )

    @pytest.fixture
    def task(self):
        """Create a sample task"""
        return Task(
            task_id="test_task",
            action="test_action",
            parameters={"key": "value"},
        )

    def test_init(self, mock_coordinator):
        """Test initialization"""
        workflow = AgentWorkflow(
            workflow_id="test_id",
            coordinator_agent=mock_coordinator,
            description="Test description",
        )

        assert workflow.workflow_id == "test_id"
        assert workflow.coordinator is mock_coordinator
        assert workflow.description == "Test description"

    def test_init_empty_description(self, mock_coordinator):
        """Test initialization with empty description"""
        workflow = AgentWorkflow(
            workflow_id="test_id",
            coordinator_agent=mock_coordinator,
        )

        assert workflow.description == ""

    def test_get_description(self, workflow):
        """Test getting workflow description"""
        assert workflow.get_description() == "Test agent workflow"

    def test_get_description_empty(self, mock_coordinator):
        """Test getting description when empty"""
        workflow = AgentWorkflow(
            workflow_id="test_id",
            coordinator_agent=mock_coordinator,
        )

        expected = "Agent-driven workflow coordinated by coordinator_1"
        assert workflow.get_description() == expected

    @pytest.mark.asyncio
    async def test_execute_delegates_to_coordinator(self, workflow, task, mock_coordinator):
        """Test that execution delegates to coordinator agent"""
        result_task = Task(
            task_id="test_task",
            action="test_action",
            parameters={"key": "value"},
            status=TaskStatus.COMPLETED,
            result={"content": "Task completed"},
        )
        mock_coordinator.execute_task = AsyncMock(return_value=result_task)

        result = await workflow.execute(task)

        mock_coordinator.execute_task.assert_called_once_with(task)
        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"content": "Task completed"}

    @pytest.mark.asyncio
    async def test_execute_with_failed_task(self, workflow, task, mock_coordinator):
        """Test execution when coordinator returns failed task"""
        result_task = Task(
            task_id="test_task",
            action="test_action",
            parameters={},
            status=TaskStatus.FAILED,
            error="Task failed",
        )
        mock_coordinator.execute_task = AsyncMock(return_value=result_task)

        result = await workflow.execute(task)

        assert result.status == TaskStatus.FAILED
        assert result.error == "Task failed"

    @pytest.mark.asyncio
    async def test_execute_with_pending_task(self, workflow, task, mock_coordinator):
        """Test execution when coordinator returns pending task"""
        result_task = Task(
            task_id="test_task",
            action="test_action",
            parameters={},
            status=TaskStatus.PENDING,
        )
        mock_coordinator.execute_task = AsyncMock(return_value=result_task)

        result = await workflow.execute(task)

        assert result.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_execute_preserves_task_attributes(self, workflow, mock_coordinator):
        """Test that execution preserves task attributes"""
        original_task = Task(
            task_id="my_task",
            action="my_action",
            parameters={"key": "value"},
            source_agent="agent1",
            target_agent="agent2",
        )

        result_task = Task(
            task_id="my_task",
            action="my_action",
            parameters={"key": "value"},
            source_agent="agent1",
            target_agent="agent2",
            status=TaskStatus.COMPLETED,
            result={"done": True},
        )
        mock_coordinator.execute_task = AsyncMock(return_value=result_task)

        result = await workflow.execute(original_task)

        assert result.task_id == "my_task"
        assert result.action == "my_action"
        assert result.source_agent == "agent1"
        assert result.target_agent == "agent2"

    @pytest.mark.asyncio
    async def test_execute_with_coordinator_exception(self, workflow, task, mock_coordinator):
        """Test execution when coordinator raises exception"""
        mock_coordinator.execute_task = AsyncMock(side_effect=RuntimeError("Coordinator error"))

        with pytest.raises(RuntimeError, match="Coordinator error"):
            await workflow.execute(task)

    @pytest.mark.asyncio
    async def test_execute_with_complex_result(self, workflow, task, mock_coordinator):
        """Test execution with complex result"""
        result_task = Task(
            task_id="test_task",
            action="test_action",
            parameters={},
            status=TaskStatus.COMPLETED,
            result={
                "content": "Done",
                "steps": ["step1", "step2"],
                "metadata": {"key": "value"},
            },
        )
        mock_coordinator.execute_task = AsyncMock(return_value=result_task)

        result = await workflow.execute(task)

        assert result.result == {
            "content": "Done",
            "steps": ["step1", "step2"],
            "metadata": {"key": "value"},
        }

    @pytest.mark.asyncio
    async def test_execute_multiple_tasks(self, workflow, mock_coordinator):
        """Test executing multiple tasks sequentially"""
        task1 = Task(task_id="task1", action="action1", parameters={})
        task2 = Task(task_id="task2", action="action2", parameters={})

        result1 = Task(task_id="task1", action="action1", parameters={}, status=TaskStatus.COMPLETED)
        result2 = Task(task_id="task2", action="action2", parameters={}, status=TaskStatus.COMPLETED)

        mock_coordinator.execute_task = AsyncMock(side_effect=[result1, result2])

        await workflow.execute(task1)
        await workflow.execute(task2)

        assert mock_coordinator.execute_task.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_coordinator_returning_none(self, workflow, task, mock_coordinator):
        """Test execution when coordinator returns None"""
        mock_coordinator.execute_task = AsyncMock(return_value=None)

        result = await workflow.execute(task)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_description_updates_with_coordinator_change(self, mock_coordinator):
        """Test that description updates when coordinator changes"""
        workflow = AgentWorkflow(
            workflow_id="test_id",
            coordinator_agent=mock_coordinator,
        )

        # Get initial description
        initial_desc = workflow.get_description()
        assert "coordinator_1" in initial_desc

        # Change coordinator
        new_coordinator = MagicMock(spec=Agent)
        new_coordinator.node_id = "coordinator_2"
        workflow.coordinator = new_coordinator

        # Get updated description
        new_desc = workflow.get_description()
        assert "coordinator_2" in new_desc

    @pytest.mark.asyncio
    async def test_execute_calls_execute_task_not_execute(self, workflow, task, mock_coordinator):
        """Test that execute calls execute_task, not _execute_impl"""
        # AgentWorkflow.execute should call coordinator.execute_task
        result_task = Task(
            task_id="test_task",
            action="test_action",
            parameters={},
            status=TaskStatus.COMPLETED,
        )
        mock_coordinator.execute_task = AsyncMock(return_value=result_task)

        await workflow.execute(task)

        # Verify execute_task was called
        mock_coordinator.execute_task.assert_called_once()
        # _execute_impl should not be called on Agent directly
        # (it would be called internally by execute_task)
