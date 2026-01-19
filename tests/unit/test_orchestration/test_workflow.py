"""
Tests for Workflow Base Class
"""

import pytest

from loom.orchestration.workflow import Workflow
from loom.protocol import Task


class TestWorkflow:
    """Test suite for Workflow base class"""

    def test_workflow_is_abstract(self):
        """Test Workflow cannot be instantiated directly"""
        with pytest.raises(TypeError):
            Workflow("test_id")

    def test_workflow_init_subclass(self):
        """Test Workflow initialization through subclass"""

        class TestWorkflow(Workflow):
            async def execute(self, task: Task) -> Task:
                return task

            def get_description(self) -> str:
                return "Test workflow"

        workflow = TestWorkflow("test_id")

        assert workflow.workflow_id == "test_id"

    def test_workflow_get_description(self):
        """Test get_description method"""

        class TestWorkflow(Workflow):
            async def execute(self, task: Task) -> Task:
                return task

            def get_description(self) -> str:
                return "Test description"

        workflow = TestWorkflow("test_id")

        assert workflow.get_description() == "Test description"

    @pytest.mark.asyncio
    async def test_workflow_execute(self):
        """Test execute method"""

        class TestWorkflow(Workflow):
            async def execute(self, task: Task) -> Task:
                task.status = "completed"
                return task

            def get_description(self) -> str:
                return "Test workflow"

        workflow = TestWorkflow("test_id")
        task = Task(task_id="test", action="test")

        result = await workflow.execute(task)

        assert result.status == "completed"

    def test_workflow_with_empty_description(self):
        """Test workflow with empty description"""

        class TestWorkflow(Workflow):
            async def execute(self, task: Task) -> Task:
                return task

            def get_description(self) -> str:
                return ""

        workflow = TestWorkflow("test_id")

        assert workflow.get_description() == ""

    def test_workflow_with_long_id(self):
        """Test workflow with long ID"""

        class TestWorkflow(Workflow):
            async def execute(self, task: Task) -> Task:
                return task

            def get_description(self) -> str:
                return "Test"

        long_id = "x" * 100
        workflow = TestWorkflow(long_id)

        assert workflow.workflow_id == long_id

    def test_workflow_with_special_characters_in_id(self):
        """Test workflow with special characters in ID"""

        class TestWorkflow(Workflow):
            async def execute(self, task: Task) -> Task:
                return task

            def get_description(self) -> str:
                return "Test"

        workflow = TestWorkflow("test-workflow_123")

        assert workflow.workflow_id == "test-workflow_123"
