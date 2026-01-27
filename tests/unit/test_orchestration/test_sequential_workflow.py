"""
Tests for Sequential Workflow
"""

import pytest

from loom.orchestration.sequential_workflow import SequentialWorkflow
from loom.protocol import Task, TaskStatus


class TestSequentialWorkflow:
    """Test suite for SequentialWorkflow"""

    @pytest.fixture
    def workflow(self):
        """Create a sample workflow"""

        async def step1(task, results):
            return "step1_result"

        async def step2(task, results):
            return "step2_result"

        async def step3(task, results):
            return "step3_result"

        return SequentialWorkflow(
            workflow_id="test_workflow",
            steps=[step1, step2, step3],
            description="Test workflow",
        )

    @pytest.fixture
    def task(self):
        """Create a sample task"""
        return Task(
            task_id="test_task",
            action="test_action",
            parameters={"key": "value"},
        )

    def test_init(self):
        """Test initialization"""

        async def dummy_step(task, results):
            return "result"

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[dummy_step],
            description="Test description",
        )

        assert workflow.workflow_id == "test_id"
        assert workflow.steps == [dummy_step]
        assert workflow.description == "Test description"

    def test_init_empty_description(self):
        """Test initialization with empty description"""

        async def dummy_step(task, results):
            return "result"

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[dummy_step],
        )

        assert workflow.description == ""

    def test_get_description(self, workflow):
        """Test getting workflow description"""
        assert workflow.get_description() == "Test workflow"

    def test_get_description_empty(self):
        """Test getting description when empty"""

        async def dummy_step(task, results):
            return "result"

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[dummy_step],
        )

        expected = "Sequential workflow with 1 steps"
        assert workflow.get_description() == expected

    def test_get_description_multiple_steps(self):
        """Test getting description with multiple steps"""

        async def step1(task, results):
            return "result"

        async def step2(task, results):
            return "result"

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[step1, step2],
        )

        expected = "Sequential workflow with 2 steps"
        assert workflow.get_description() == expected

    @pytest.mark.asyncio
    async def test_execute_success(self, workflow, task):
        """Test successful execution"""
        result = await workflow.execute(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"steps_results": ["step1_result", "step2_result", "step3_result"]}

    @pytest.mark.asyncio
    async def test_execute_with_results_accumulation(self):
        """Test that results are accumulated correctly"""

        async def step1(task, results):
            return len(results)

        async def step2(task, results):
            return len(results)

        async def step3(task, results):
            return len(results)

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[step1, step2, step3],
        )

        task = Task(task_id="test", action="test", parameters={})
        result = await workflow.execute(task)

        assert result.result == {"steps_results": [0, 1, 2]}

    @pytest.mark.asyncio
    async def test_execute_step_failure(self):
        """Test execution when a step fails"""

        async def step1(task, results):
            return "step1"

        async def failing_step(task, results):
            raise ValueError("Step failed!")

        async def step3(task, results):
            return "step3"  # Should not execute

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[step1, failing_step, step3],
        )

        task = Task(task_id="test", action="test", parameters={})
        result = await workflow.execute(task)

        assert result.status == TaskStatus.FAILED
        assert "Step 2 failed" in result.error
        assert "Step failed!" in result.error

    @pytest.mark.asyncio
    async def test_execute_first_step_failure(self):
        """Test execution when first step fails"""

        async def failing_step(task, results):
            raise RuntimeError("First step error")

        async def step2(task, results):
            return "step2"  # Should not execute

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[failing_step, step2],
        )

        task = Task(task_id="test", action="test", parameters={})
        result = await workflow.execute(task)

        assert result.status == TaskStatus.FAILED
        assert "Step 1 failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_last_step_failure(self):
        """Test execution when last step fails"""

        async def step1(task, results):
            return "step1"

        async def step2(task, results):
            return "step2"

        async def failing_step(task, results):
            raise Exception("Last step failed")

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[step1, step2, failing_step],
        )

        task = Task(task_id="test", action="test", parameters={})
        result = await workflow.execute(task)

        assert result.status == TaskStatus.FAILED
        assert "Step 3 failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_empty_steps(self):
        """Test execution with no steps"""
        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[],
        )

        task = Task(task_id="test", action="test", parameters={})
        result = await workflow.execute(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"steps_results": []}

    @pytest.mark.asyncio
    async def test_execute_single_step(self):
        """Test execution with single step"""

        async def step1(task, results):
            return "only result"

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[step1],
        )

        task = Task(task_id="test", action="test", parameters={})
        result = await workflow.execute(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"steps_results": ["only result"]}

    @pytest.mark.asyncio
    async def test_execute_with_task_access(self):
        """Test that steps can access the task"""

        async def step1(task, results):
            return task.task_id

        async def step2(task, results):
            return task.action

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[step1, step2],
        )

        task = Task(
            task_id="my_task",
            action="my_action",
            parameters={},
        )
        result = await workflow.execute(task)

        assert result.result == {"steps_results": ["my_task", "my_action"]}

    @pytest.mark.asyncio
    async def test_execute_exception_in_step(self):
        """Test handling of generic exceptions in steps"""

        async def step1(task, results):
            return "step1"

        async def exception_step(task, results):
            raise RuntimeError("Unexpected error")

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[step1, exception_step],
        )

        task = Task(task_id="test", action="test", parameters={})
        result = await workflow.execute(task)

        assert result.status == TaskStatus.FAILED
        assert "Step 2 failed" in result.error

    @pytest.mark.asyncio
    async def test_execute_preserves_task_attributes(self, workflow, task):
        """Test that execution preserves task attributes"""
        original_task_id = task.task_id
        original_action = task.action

        result = await workflow.execute(task)

        assert result.task_id == original_task_id
        assert result.action == original_action
        assert result.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_with_none_results(self):
        """Test execution when steps return None"""

        async def step1(task, results):
            return None

        async def step2(task, results):
            return None

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[step1, step2],
        )

        task = Task(task_id="test", action="test", parameters={})
        result = await workflow.execute(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"steps_results": [None, None]}

    @pytest.mark.asyncio
    async def test_execute_with_complex_results(self):
        """Test execution with complex result types"""

        async def step1(task, results):
            return {"key": "value", "number": 42}

        async def step2(task, results):
            return [1, 2, 3, 4, 5]

        workflow = SequentialWorkflow(
            workflow_id="test_id",
            steps=[step1, step2],
        )

        task = Task(task_id="test", action="test", parameters={})
        result = await workflow.execute(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"steps_results": [{"key": "value", "number": 42}, [1, 2, 3, 4, 5]]}
