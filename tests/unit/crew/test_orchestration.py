"""
Unit tests for loom.crew.orchestration module

Tests cover:
- Task dataclass creation and validation
- OrchestrationPlan creation and validation
- OrchestrationMode enum
- Orchestrator execution modes (sequential, parallel)
- Topological sorting and dependency resolution
- Task grouping for parallel execution
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from loom.crew.orchestration import (
    Task,
    OrchestrationPlan,
    OrchestrationMode,
    Orchestrator,
)


class TestTask:
    """Tests for Task dataclass"""

    def test_task_creation_minimal(self):
        """Test creating task with minimal fields"""
        task = Task(
            id="test_task",
            description="Test task",
            prompt="Do something",
            assigned_role="developer"
        )

        assert task.id == "test_task"
        assert task.description == "Test task"
        assert task.prompt == "Do something"
        assert task.assigned_role == "developer"
        assert task.dependencies == []
        assert task.condition is None
        assert task.output_key is None
        assert task.context == {}
        assert task.metadata == {}

    def test_task_creation_full(self):
        """Test creating task with all fields"""
        condition = lambda ctx: ctx.get("flag", False)

        task = Task(
            id="full_task",
            description="Full task",
            prompt="Do complex thing",
            assigned_role="researcher",
            dependencies=["task1", "task2"],
            condition=condition,
            output_key="result_key",
            context={"key": "value"},
            metadata={"priority": "high"}
        )

        assert task.id == "full_task"
        assert task.dependencies == ["task1", "task2"]
        assert task.condition is condition
        assert task.output_key == "result_key"
        assert task.context == {"key": "value"}
        assert task.metadata == {"priority": "high"}

    def test_task_creation_empty_id_raises(self):
        """Test that empty ID raises ValueError"""
        with pytest.raises(ValueError, match="ID cannot be empty"):
            Task(
                id="",
                description="Test",
                prompt="Test",
                assigned_role="developer"
            )

    def test_task_creation_empty_assigned_role_raises(self):
        """Test that empty assigned_role raises ValueError"""
        with pytest.raises(ValueError, match="must have an assigned_role"):
            Task(
                id="test",
                description="Test",
                prompt="Test",
                assigned_role=""
            )

    def test_task_creation_empty_prompt_raises(self):
        """Test that empty prompt raises ValueError"""
        with pytest.raises(ValueError, match="must have a prompt"):
            Task(
                id="test",
                description="Test",
                prompt="",
                assigned_role="developer"
            )

    def test_should_execute_no_condition(self):
        """Test should_execute with no condition"""
        task = Task(
            id="test",
            description="Test",
            prompt="Test",
            assigned_role="developer"
        )

        assert task.should_execute({}) is True
        assert task.should_execute({"any": "context"}) is True

    def test_should_execute_with_condition_true(self):
        """Test should_execute with condition returning True"""
        task = Task(
            id="test",
            description="Test",
            prompt="Test",
            assigned_role="developer",
            condition=lambda ctx: ctx.get("execute", False)
        )

        assert task.should_execute({"execute": True}) is True

    def test_should_execute_with_condition_false(self):
        """Test should_execute with condition returning False"""
        task = Task(
            id="test",
            description="Test",
            prompt="Test",
            assigned_role="developer",
            condition=lambda ctx: ctx.get("execute", False)
        )

        assert task.should_execute({"execute": False}) is False
        assert task.should_execute({}) is False

    def test_to_dict(self):
        """Test serialization to dict"""
        task = Task(
            id="test",
            description="Test task",
            prompt="Do something",
            assigned_role="developer",
            dependencies=["dep1"],
            output_key="result",
            context={"key": "value"},
            metadata={"priority": "high"}
        )

        data = task.to_dict()

        assert data["id"] == "test"
        assert data["description"] == "Test task"
        assert data["prompt"] == "Do something"
        assert data["assigned_role"] == "developer"
        assert data["dependencies"] == ["dep1"]
        assert data["output_key"] == "result"
        assert data["context"] == {"key": "value"}
        assert data["metadata"] == {"priority": "high"}

    def test_repr(self):
        """Test __repr__ method"""
        task = Task(
            id="test",
            description="Test",
            prompt="Test",
            assigned_role="developer",
            dependencies=["dep1", "dep2"]
        )

        repr_str = repr(task)

        assert "Task" in repr_str
        assert "test" in repr_str
        assert "developer" in repr_str
        assert "deps=2" in repr_str


class TestOrchestrationPlan:
    """Tests for OrchestrationPlan dataclass"""

    def test_plan_creation_minimal(self):
        """Test creating plan with minimal fields"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="dev")

        plan = OrchestrationPlan(tasks=[task1])

        assert len(plan.tasks) == 1
        assert plan.mode == OrchestrationMode.SEQUENTIAL
        assert plan.shared_context == {}
        assert plan.max_parallel == 5
        assert plan.metadata == {}

    def test_plan_creation_full(self):
        """Test creating plan with all fields"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="dev")
        task2 = Task(id="t2", description="T2", prompt="P2", assigned_role="dev")

        plan = OrchestrationPlan(
            tasks=[task1, task2],
            mode=OrchestrationMode.PARALLEL,
            shared_context={"key": "value"},
            max_parallel=10,
            metadata={"plan_id": "123"}
        )

        assert len(plan.tasks) == 2
        assert plan.mode == OrchestrationMode.PARALLEL
        assert plan.shared_context == {"key": "value"}
        assert plan.max_parallel == 10
        assert plan.metadata == {"plan_id": "123"}

    def test_plan_creation_empty_tasks_raises(self):
        """Test that empty tasks list raises ValueError"""
        with pytest.raises(ValueError, match="at least one task"):
            OrchestrationPlan(tasks=[])

    def test_plan_creation_duplicate_task_ids_raises(self):
        """Test that duplicate task IDs raise ValueError"""
        task1 = Task(id="dup", description="T1", prompt="P1", assigned_role="dev")
        task2 = Task(id="dup", description="T2", prompt="P2", assigned_role="dev")

        with pytest.raises(ValueError, match="Duplicate task IDs"):
            OrchestrationPlan(tasks=[task1, task2])

    def test_plan_creation_invalid_dependency_raises(self):
        """Test that invalid dependency raises ValueError"""
        task1 = Task(
            id="t1",
            description="T1",
            prompt="P1",
            assigned_role="dev",
            dependencies=["nonexistent"]
        )

        with pytest.raises(ValueError, match="invalid dependencies"):
            OrchestrationPlan(tasks=[task1])

    def test_get_task(self):
        """Test get_task method"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="dev")
        task2 = Task(id="t2", description="T2", prompt="P2", assigned_role="dev")

        plan = OrchestrationPlan(tasks=[task1, task2])

        assert plan.get_task("t1") == task1
        assert plan.get_task("t2") == task2
        assert plan.get_task("nonexistent") is None

    def test_get_task_dependencies(self):
        """Test get_task_dependencies method"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="dev")
        task2 = Task(id="t2", description="T2", prompt="P2", assigned_role="dev")
        task3 = Task(
            id="t3",
            description="T3",
            prompt="P3",
            assigned_role="dev",
            dependencies=["t1", "t2"]
        )

        plan = OrchestrationPlan(tasks=[task1, task2, task3])

        deps = plan.get_task_dependencies("t3")
        assert len(deps) == 2
        assert task1 in deps
        assert task2 in deps

        # Task with no dependencies
        assert plan.get_task_dependencies("t1") == []

    def test_repr(self):
        """Test __repr__ method"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="dev")

        plan = OrchestrationPlan(
            tasks=[task1],
            mode=OrchestrationMode.PARALLEL
        )

        repr_str = repr(plan)

        assert "OrchestrationPlan" in repr_str
        assert "tasks=1" in repr_str
        assert "parallel" in repr_str


class TestOrchestrator:
    """Tests for Orchestrator class"""

    @pytest.fixture
    def mock_crew(self):
        """Create a mock crew for testing"""
        crew = AsyncMock()
        crew.execute_task = AsyncMock(return_value="task_result")
        crew.members = {"developer": MagicMock(), "manager": MagicMock()}
        return crew

    @pytest.mark.asyncio
    async def test_execute_sequential(self, mock_crew):
        """Test sequential execution"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="developer")
        task2 = Task(
            id="t2",
            description="T2",
            prompt="P2",
            assigned_role="developer",
            dependencies=["t1"]
        )

        plan = OrchestrationPlan(
            tasks=[task1, task2],
            mode=OrchestrationMode.SEQUENTIAL
        )

        orchestrator = Orchestrator()
        results = await orchestrator.execute(plan, mock_crew)

        assert "t1" in results
        assert "t2" in results
        assert mock_crew.execute_task.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_parallel(self, mock_crew):
        """Test parallel execution"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="developer")
        task2 = Task(id="t2", description="T2", prompt="P2", assigned_role="developer")

        plan = OrchestrationPlan(
            tasks=[task1, task2],
            mode=OrchestrationMode.PARALLEL
        )

        orchestrator = Orchestrator()
        results = await orchestrator.execute(plan, mock_crew)

        assert "t1" in results
        assert "t2" in results
        assert mock_crew.execute_task.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_conditional(self, mock_crew):
        """Test conditional execution"""
        task1 = Task(
            id="t1",
            description="T1",
            prompt="P1",
            assigned_role="developer",
            condition=lambda ctx: True
        )
        task2 = Task(
            id="t2",
            description="T2",
            prompt="P2",
            assigned_role="developer",
            condition=lambda ctx: False
        )

        plan = OrchestrationPlan(
            tasks=[task1, task2],
            mode=OrchestrationMode.CONDITIONAL
        )

        orchestrator = Orchestrator()
        results = await orchestrator.execute(plan, mock_crew)

        # Task 1 should be completed
        assert "t1" in results
        assert results["t1"]["status"] == "completed"

        # Task 2 should be skipped (now appears in results with status='skipped')
        assert "t2" in results
        assert results["t2"]["status"] == "skipped"

        # Only task1 should have been executed
        assert mock_crew.execute_task.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_hierarchical(self, mock_crew):
        """Test hierarchical execution"""
        # Add manager to members
        mock_crew.members = {
            "manager": MagicMock(),
            "developer": MagicMock()
        }

        # Mock list_roles and _get_or_create_agent
        mock_crew.list_roles = MagicMock(return_value=["manager", "developer"])

        # Mock manager agent
        mock_manager_agent = MagicMock()
        mock_manager_agent.run = AsyncMock(return_value="Manager coordinated all tasks")
        mock_crew._get_or_create_agent = MagicMock(return_value=mock_manager_agent)

        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="developer")

        plan = OrchestrationPlan(
            tasks=[task1],
            mode=OrchestrationMode.HIERARCHICAL
        )

        orchestrator = Orchestrator()
        results = await orchestrator.execute(plan, mock_crew)

        # Should have manager coordination result
        assert "_manager_coordination" in results
        assert results["_manager_coordination"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_hierarchical_no_manager_raises(self, mock_crew):
        """Test hierarchical execution without manager raises error"""
        mock_crew.members = {"developer": MagicMock()}  # No manager

        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="developer")

        plan = OrchestrationPlan(
            tasks=[task1],
            mode=OrchestrationMode.HIERARCHICAL
        )

        orchestrator = Orchestrator()

        with pytest.raises(ValueError, match="requires a 'manager' role"):
            await orchestrator.execute(plan, mock_crew)

    @pytest.mark.asyncio
    async def test_execute_with_output_keys(self, mock_crew):
        """Test execution with output keys updates shared context"""
        mock_crew.execute_task = AsyncMock(side_effect=["result1", "result2"])

        task1 = Task(
            id="t1",
            description="T1",
            prompt="P1",
            assigned_role="developer",
            output_key="first_result"
        )
        task2 = Task(
            id="t2",
            description="T2",
            prompt="P2",
            assigned_role="developer",
            dependencies=["t1"]
        )

        plan = OrchestrationPlan(tasks=[task1, task2])

        orchestrator = Orchestrator()
        results = await orchestrator.execute(plan, mock_crew)

        assert results["t1"] == "result1"
        assert results["t2"] == "result2"
        assert plan.shared_context["first_result"] == "result1"

    def test_topological_sort_simple(self):
        """Test topological sort with simple dependencies"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="dev")
        task2 = Task(
            id="t2",
            description="T2",
            prompt="P2",
            assigned_role="dev",
            dependencies=["t1"]
        )
        task3 = Task(
            id="t3",
            description="T3",
            prompt="P3",
            assigned_role="dev",
            dependencies=["t2"]
        )

        orchestrator = Orchestrator()
        sorted_tasks = orchestrator._topological_sort([task3, task1, task2])

        ids = [t.id for t in sorted_tasks]
        assert ids == ["t1", "t2", "t3"]

    def test_topological_sort_complex(self):
        """Test topological sort with complex dependencies"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="dev")
        task2 = Task(id="t2", description="T2", prompt="P2", assigned_role="dev")
        task3 = Task(
            id="t3",
            description="T3",
            prompt="P3",
            assigned_role="dev",
            dependencies=["t1", "t2"]
        )
        task4 = Task(
            id="t4",
            description="T4",
            prompt="P4",
            assigned_role="dev",
            dependencies=["t2"]
        )

        orchestrator = Orchestrator()
        sorted_tasks = orchestrator._topological_sort([task4, task3, task2, task1])

        ids = [t.id for t in sorted_tasks]

        # t1 and t2 can be in any order (no dependency)
        # t3 must come after both t1 and t2
        # t4 must come after t2
        assert ids.index("t1") < ids.index("t3")
        assert ids.index("t2") < ids.index("t3")
        assert ids.index("t2") < ids.index("t4")

    def test_topological_sort_circular_dependency_raises(self):
        """Test that circular dependencies raise ValueError"""
        task1 = Task(
            id="t1",
            description="T1",
            prompt="P1",
            assigned_role="dev",
            dependencies=["t2"]
        )
        task2 = Task(
            id="t2",
            description="T2",
            prompt="P2",
            assigned_role="dev",
            dependencies=["t1"]
        )

        # Need to bypass OrchestrationPlan validation which checks this
        orchestrator = Orchestrator()

        with pytest.raises(ValueError, match="Circular dependencies"):
            orchestrator._topological_sort([task1, task2])

    def test_group_by_dependencies_simple(self):
        """Test grouping tasks by dependencies"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="dev")
        task2 = Task(id="t2", description="T2", prompt="P2", assigned_role="dev")
        task3 = Task(
            id="t3",
            description="T3",
            prompt="P3",
            assigned_role="dev",
            dependencies=["t1", "t2"]
        )

        orchestrator = Orchestrator()
        groups = orchestrator._group_by_dependencies([task1, task2, task3])

        assert len(groups) == 2
        # First group: t1 and t2 (no dependencies)
        assert len(groups[0]) == 2
        assert task1 in groups[0]
        assert task2 in groups[0]
        # Second group: t3 (depends on t1 and t2)
        assert len(groups[1]) == 1
        assert task3 in groups[1]

    def test_group_by_dependencies_complex(self):
        """Test grouping with complex dependencies"""
        task1 = Task(id="t1", description="T1", prompt="P1", assigned_role="dev")
        task2 = Task(
            id="t2",
            description="T2",
            prompt="P2",
            assigned_role="dev",
            dependencies=["t1"]
        )
        task3 = Task(
            id="t3",
            description="T3",
            prompt="P3",
            assigned_role="dev",
            dependencies=["t1"]
        )
        task4 = Task(
            id="t4",
            description="T4",
            prompt="P4",
            assigned_role="dev",
            dependencies=["t2", "t3"]
        )

        orchestrator = Orchestrator()
        groups = orchestrator._group_by_dependencies([task1, task2, task3, task4])

        assert len(groups) == 3
        # Group 0: t1
        assert len(groups[0]) == 1
        assert task1 in groups[0]
        # Group 1: t2 and t3 (both depend only on t1)
        assert len(groups[1]) == 2
        assert task2 in groups[1]
        assert task3 in groups[1]
        # Group 2: t4 (depends on t2 and t3)
        assert len(groups[2]) == 1
        assert task4 in groups[2]

    def test_build_task_context(self):
        """Test building task context"""
        task = Task(
            id="test",
            description="Test",
            prompt="Test",
            assigned_role="dev",
            dependencies=["dep1", "dep2"],
            context={"task_key": "task_value"}
        )

        results = {
            "dep1": "result1",
            "dep2": "result2",
            "other": "other_result"
        }

        shared_context = {
            "shared_key": "shared_value"
        }

        orchestrator = Orchestrator()
        context = orchestrator._build_task_context(task, results, shared_context)

        # Should include shared context
        assert context["shared_key"] == "shared_value"
        # Should include task context
        assert context["task_key"] == "task_value"
        # Should include dependency results
        assert "dependency_results" in context
        assert context["dependency_results"]["dep1"] == "result1"
        assert context["dependency_results"]["dep2"] == "result2"
        # Should not include unrelated results
        assert "other" not in context["dependency_results"]


class TestOrchestrationIntegration:
    """Integration tests for orchestration components"""

    @pytest.mark.asyncio
    async def test_full_sequential_workflow(self):
        """Test complete sequential workflow"""
        # Create mock crew
        crew = AsyncMock()
        results_sequence = ["result1", "result2", "result3"]
        crew.execute_task = AsyncMock(side_effect=results_sequence)
        crew.members = {"dev": MagicMock()}

        # Create tasks
        task1 = Task(
            id="gather",
            description="Gather data",
            prompt="Gather data",
            assigned_role="dev",
            output_key="data"
        )
        task2 = Task(
            id="process",
            description="Process data",
            prompt="Process data",
            assigned_role="dev",
            dependencies=["gather"],
            output_key="processed_data"
        )
        task3 = Task(
            id="report",
            description="Generate report",
            prompt="Generate report",
            assigned_role="dev",
            dependencies=["process"]
        )

        # Create plan and execute
        plan = OrchestrationPlan(
            tasks=[task1, task2, task3],
            mode=OrchestrationMode.SEQUENTIAL
        )

        orchestrator = Orchestrator()
        results = await orchestrator.execute(plan, crew)

        # Verify results
        assert results["gather"] == "result1"
        assert results["process"] == "result2"
        assert results["report"] == "result3"

        # Verify shared context updated
        assert plan.shared_context["data"] == "result1"
        assert plan.shared_context["processed_data"] == "result2"

        # Verify execution order
        assert crew.execute_task.call_count == 3

    @pytest.mark.asyncio
    async def test_full_parallel_workflow(self):
        """Test complete parallel workflow"""
        # Create mock crew
        crew = AsyncMock()
        crew.execute_task = AsyncMock(return_value="result")
        crew.members = {"dev": MagicMock()}

        # Create independent tasks
        tasks = [
            Task(id=f"task{i}", description=f"T{i}", prompt=f"P{i}", assigned_role="dev")
            for i in range(1, 6)
        ]

        # Create plan and execute
        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.PARALLEL
        )

        orchestrator = Orchestrator()
        results = await orchestrator.execute(plan, crew)

        # All tasks should complete
        assert len(results) == 5
        for i in range(1, 6):
            assert f"task{i}" in results

        # All should execute
        assert crew.execute_task.call_count == 5
