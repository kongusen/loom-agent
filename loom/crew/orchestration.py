"""
Task Orchestration System - Multi-Task Execution Coordination

This module provides task orchestration capabilities for coordinating
multiple agents working on related tasks with dependencies.

Design Philosophy:
- Tasks are atomic units of work assigned to roles
- Dependencies create execution order constraints
- Multiple orchestration modes support different coordination patterns
- Inspired by workflow engines (Airflow, Prefect) with agent focus

Example:
    ```python
    from loom.crew.orchestration import (
        Task,
        OrchestrationPlan,
        OrchestrationMode,
        Orchestrator
    )

    # Define tasks with dependencies
    tasks = [
        Task(
            id="gather_data",
            description="Gather project data",
            prompt="Analyze the project structure",
            assigned_role="researcher",
            output_key="research_data"
        ),
        Task(
            id="implement_feature",
            description="Implement feature",
            prompt="Implement feature based on research",
            assigned_role="developer",
            dependencies=["gather_data"],  # Depends on research
            output_key="implementation_result"
        ),
        Task(
            id="write_tests",
            description="Write tests",
            prompt="Write tests for the implementation",
            assigned_role="qa_engineer",
            dependencies=["implement_feature"]  # Depends on implementation
        )
    ]

    # Create plan
    plan = OrchestrationPlan(
        tasks=tasks,
        mode=OrchestrationMode.SEQUENTIAL
    )

    # Execute with orchestrator
    orchestrator = Orchestrator()
    results = await orchestrator.execute(plan, crew)
    ```
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from loom.crew.crew import Crew


# ============================================================================
# Condition Helpers for Advanced Conditional Orchestration
# ============================================================================


class ConditionBuilder:
    """
    Builder for creating complex conditional logic.

    Provides helper methods for creating AND, OR, NOT conditions
    for task execution.

    Example:
        ```python
        # Simple condition
        has_research = lambda ctx: "research_data" in ctx

        # Complex condition: AND
        has_both = ConditionBuilder.and_all([
            lambda ctx: "research_data" in ctx,
            lambda ctx: ctx.get("quality_score", 0) > 0.8
        ])

        # Complex condition: OR
        has_either = ConditionBuilder.or_any([
            lambda ctx: "plan_a" in ctx,
            lambda ctx: "plan_b" in ctx
        ])

        # Complex condition: NOT
        no_errors = ConditionBuilder.not_(
            lambda ctx: ctx.get("has_errors", False)
        )
        ```
    """

    @staticmethod
    def and_all(conditions: List[Callable[[Dict[str, Any]], bool]]) -> Callable:
        """
        Create AND condition (all must be true).

        Args:
            conditions: List of condition functions

        Returns:
            Callable: Combined condition function
        """
        def combined(context: Dict[str, Any]) -> bool:
            return all(cond(context) for cond in conditions)
        return combined

    @staticmethod
    def or_any(conditions: List[Callable[[Dict[str, Any]], bool]]) -> Callable:
        """
        Create OR condition (at least one must be true).

        Args:
            conditions: List of condition functions

        Returns:
            Callable: Combined condition function
        """
        def combined(context: Dict[str, Any]) -> bool:
            return any(cond(context) for cond in conditions)
        return combined

    @staticmethod
    def not_(condition: Callable[[Dict[str, Any]], bool]) -> Callable:
        """
        Create NOT condition (negate).

        Args:
            condition: Condition function to negate

        Returns:
            Callable: Negated condition function
        """
        def combined(context: Dict[str, Any]) -> bool:
            return not condition(context)
        return combined

    @staticmethod
    def key_exists(key: str) -> Callable:
        """
        Create condition checking if key exists in context.

        Args:
            key: Context key to check

        Returns:
            Callable: Condition function
        """
        return lambda ctx: key in ctx

    @staticmethod
    def key_equals(key: str, value: Any) -> Callable:
        """
        Create condition checking if key equals value.

        Args:
            key: Context key to check
            value: Expected value

        Returns:
            Callable: Condition function
        """
        return lambda ctx: ctx.get(key) == value

    @staticmethod
    def key_in_list(key: str, values: List[Any]) -> Callable:
        """
        Create condition checking if key value is in list.

        Args:
            key: Context key to check
            values: List of allowed values

        Returns:
            Callable: Condition function
        """
        return lambda ctx: ctx.get(key) in values


class OrchestrationMode(Enum):
    """
    Orchestration execution modes.

    Attributes:
        SEQUENTIAL: Execute tasks one by one in dependency order
        PARALLEL: Execute independent tasks in parallel, respecting dependencies
        CONDITIONAL: Execute tasks based on runtime conditions
        HIERARCHICAL: Manager delegates tasks to team members
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    HIERARCHICAL = "hierarchical"


@dataclass
class Task:
    """
    Task definition with dependencies and context.

    A Task represents a unit of work to be assigned to an agent role.
    Tasks can depend on other tasks, creating execution order constraints.

    Attributes:
        id: Unique task identifier
        description: Short task description (for logging/display)
        prompt: Detailed task instructions for the agent
        assigned_role: Name of the role to execute this task
        dependencies: List of task IDs that must complete first
        condition: Optional callable that determines if task should run
        output_key: Key to store result in shared context
        context: Additional task-specific context data
        metadata: Task metadata (priority, tags, etc.)
    """

    id: str
    description: str
    prompt: str
    assigned_role: str
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    output_key: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate task configuration"""
        if not self.id:
            raise ValueError("Task ID cannot be empty")
        if not self.assigned_role:
            raise ValueError(f"Task '{self.id}' must have an assigned_role")
        if not self.prompt:
            raise ValueError(f"Task '{self.id}' must have a prompt")

    def should_execute(self, shared_context: Dict[str, Any]) -> bool:
        """
        Determine if task should execute based on condition.

        Args:
            shared_context: Shared context dictionary

        Returns:
            bool: True if task should execute, False otherwise
        """
        if self.condition is None:
            return True
        return self.condition(shared_context)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize task to dictionary.

        Returns:
            Dict: Task data as dictionary
        """
        return {
            "id": self.id,
            "description": self.description,
            "prompt": self.prompt,
            "assigned_role": self.assigned_role,
            "dependencies": self.dependencies,
            "output_key": self.output_key,
            "context": self.context,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"Task(id={self.id!r}, "
            f"role={self.assigned_role!r}, "
            f"deps={len(self.dependencies)})"
        )


@dataclass
class OrchestrationPlan:
    """
    Multi-task execution plan.

    An OrchestrationPlan defines how a set of tasks should be executed,
    including execution mode, shared context, and parallelism settings.

    Attributes:
        tasks: List of tasks to execute
        mode: Orchestration mode (sequential, parallel, etc.)
        shared_context: Shared data accessible to all tasks
        max_parallel: Maximum number of tasks to run concurrently (parallel mode)
        metadata: Plan-level metadata
    """

    tasks: List[Task]
    mode: OrchestrationMode = OrchestrationMode.SEQUENTIAL
    shared_context: Dict[str, Any] = field(default_factory=dict)
    max_parallel: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate plan configuration"""
        if not self.tasks:
            raise ValueError("OrchestrationPlan must have at least one task")

        # Validate task IDs are unique
        task_ids = [t.id for t in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            duplicates = [tid for tid in task_ids if task_ids.count(tid) > 1]
            raise ValueError(f"Duplicate task IDs found: {duplicates}")

        # Validate all dependencies exist
        valid_ids = set(task_ids)
        for task in self.tasks:
            invalid_deps = [d for d in task.dependencies if d not in valid_ids]
            if invalid_deps:
                raise ValueError(
                    f"Task '{task.id}' has invalid dependencies: {invalid_deps}"
                )

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get task by ID.

        Args:
            task_id: Task ID to lookup

        Returns:
            Optional[Task]: Task if found, None otherwise
        """
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def get_task_dependencies(self, task_id: str) -> List[Task]:
        """
        Get list of task objects that a task depends on.

        Args:
            task_id: Task ID

        Returns:
            List[Task]: List of dependency tasks
        """
        task = self.get_task(task_id)
        if not task:
            return []

        return [self.get_task(dep_id) for dep_id in task.dependencies if self.get_task(dep_id)]

    def __repr__(self) -> str:
        return (
            f"OrchestrationPlan(tasks={len(self.tasks)}, "
            f"mode={self.mode.value})"
        )


class Orchestrator:
    """
    Task orchestrator for coordinating multi-agent execution.

    The Orchestrator manages task execution according to the orchestration plan,
    handling dependencies, parallelism, and result aggregation.

    Example:
        ```python
        orchestrator = Orchestrator()

        plan = OrchestrationPlan(
            tasks=[task1, task2, task3],
            mode=OrchestrationMode.PARALLEL
        )

        results = await orchestrator.execute(plan, crew)
        ```
    """

    async def execute(
        self,
        plan: OrchestrationPlan,
        crew: "Crew",
    ) -> Dict[str, Any]:
        """
        Execute orchestration plan.

        Args:
            plan: OrchestrationPlan to execute
            crew: Crew instance with team members

        Returns:
            Dict[str, Any]: Task results keyed by task ID

        Raises:
            ValueError: If orchestration mode is not supported
        """
        if plan.mode == OrchestrationMode.SEQUENTIAL:
            return await self._execute_sequential(plan, crew)
        elif plan.mode == OrchestrationMode.PARALLEL:
            return await self._execute_parallel(plan, crew)
        elif plan.mode == OrchestrationMode.CONDITIONAL:
            return await self._execute_conditional(plan, crew)
        elif plan.mode == OrchestrationMode.HIERARCHICAL:
            return await self._execute_hierarchical(plan, crew)
        else:
            raise ValueError(f"Unsupported orchestration mode: {plan.mode}")

    async def _execute_sequential(
        self,
        plan: OrchestrationPlan,
        crew: "Crew",
    ) -> Dict[str, Any]:
        """
        Execute tasks sequentially in dependency order.

        Uses topological sort to determine execution order that respects dependencies.

        Args:
            plan: Orchestration plan
            crew: Crew instance

        Returns:
            Dict[str, Any]: Task results
        """
        results: Dict[str, Any] = {}
        sorted_tasks = self._topological_sort(plan.tasks)

        for task in sorted_tasks:
            # Check condition
            if not task.should_execute(plan.shared_context):
                continue

            # Build task context with dependency results
            task_context = self._build_task_context(task, results, plan.shared_context)

            # Execute task
            result = await crew.execute_task(task, context=task_context)
            results[task.id] = result

            # Update shared context
            if task.output_key:
                plan.shared_context[task.output_key] = result

        return results

    async def _execute_parallel(
        self,
        plan: OrchestrationPlan,
        crew: "Crew",
    ) -> Dict[str, Any]:
        """
        Execute tasks in parallel, respecting dependencies.

        Groups tasks into levels where tasks in the same level have no dependencies
        on each other. Each level is executed in parallel.

        Args:
            plan: Orchestration plan
            crew: Crew instance

        Returns:
            Dict[str, Any]: Task results
        """
        results: Dict[str, Any] = {}
        task_groups = self._group_by_dependencies(plan.tasks)

        for group in task_groups:
            # Filter by condition
            executable_tasks = [
                task for task in group
                if task.should_execute(plan.shared_context)
            ]

            # Execute group in parallel (up to max_parallel)
            semaphore = asyncio.Semaphore(plan.max_parallel)

            async def execute_with_semaphore(task: Task) -> tuple[str, Any]:
                async with semaphore:
                    task_context = self._build_task_context(
                        task, results, plan.shared_context
                    )
                    result = await crew.execute_task(task, context=task_context)
                    return task.id, result

            # Gather results
            group_results = await asyncio.gather(
                *[execute_with_semaphore(task) for task in executable_tasks]
            )

            # Update results and shared context
            for task_id, result in group_results:
                results[task_id] = result

                # Find task and update shared context if needed
                task = plan.get_task(task_id)
                if task and task.output_key:
                    plan.shared_context[task.output_key] = result

        return results

    async def _execute_conditional(
        self,
        plan: OrchestrationPlan,
        crew: "Crew",
    ) -> Dict[str, Any]:
        """
        Execute tasks based on runtime conditions with detailed tracking.

        In CONDITIONAL mode, tasks are executed sequentially but with
        detailed condition evaluation and skip tracking. This mode is
        useful for workflows where task execution depends on previous results.

        Enhancements:
        - Detailed condition evaluation logging
        - Skip reason tracking
        - Conditional statistics

        Args:
            plan: Orchestration plan
            crew: Crew instance

        Returns:
            Dict[str, Any]: Task results including skip information

        Example:
            ```python
            # Define conditional task
            task = Task(
                id="analyze_if_errors",
                description="Analyze errors",
                prompt="Analyze error logs",
                assigned_role="researcher",
                condition=lambda ctx: ctx.get("has_errors", False)
            )
            ```
        """
        results: Dict[str, Any] = {}
        skipped_tasks: List[str] = []
        executed_tasks: List[str] = []

        sorted_tasks = self._topological_sort(plan.tasks)

        for task in sorted_tasks:
            # Evaluate condition
            should_execute = task.should_execute(plan.shared_context)

            if not should_execute:
                # Track skipped task
                skipped_tasks.append(task.id)
                results[task.id] = {
                    "status": "skipped",
                    "reason": "condition_not_met",
                    "task_description": task.description,
                }
                continue

            # Track executed task
            executed_tasks.append(task.id)

            # Build task context with dependency results
            task_context = self._build_task_context(task, results, plan.shared_context)

            # Execute task
            result = await crew.execute_task(task, context=task_context)
            results[task.id] = {
                "status": "completed",
                "result": result,
                "task_description": task.description,
            }

            # Update shared context
            if task.output_key:
                plan.shared_context[task.output_key] = result

        # Add execution statistics to shared context
        plan.shared_context["_conditional_stats"] = {
            "total_tasks": len(sorted_tasks),
            "executed": len(executed_tasks),
            "skipped": len(skipped_tasks),
            "executed_task_ids": executed_tasks,
            "skipped_task_ids": skipped_tasks,
        }

        return results

    async def _execute_hierarchical(
        self,
        plan: OrchestrationPlan,
        crew: "Crew",
    ) -> Dict[str, Any]:
        """
        Execute tasks in hierarchical mode with manager coordination.

        In HIERARCHICAL mode, a manager agent coordinates the workflow by:
        1. Reviewing the orchestration plan
        2. Delegating tasks to appropriate team members using the delegate tool
        3. Monitoring progress and collecting results
        4. Producing a final summary

        This mode requires a "manager" role in the crew with delegation enabled.

        Enhancements:
        - Manager creates coordination plan
        - Uses DelegateTool for team coordination
        - Collects and synthesizes team outputs

        Args:
            plan: Orchestration plan
            crew: Crew instance

        Returns:
            Dict[str, Any]: Task results

        Raises:
            ValueError: If no manager role found in crew

        Example:
            ```python
            # Manager coordinates the team
            plan = OrchestrationPlan(
                tasks=[research_task, develop_task, qa_task],
                mode=OrchestrationMode.HIERARCHICAL
            )
            results = await orchestrator.execute(plan, crew)
            ```
        """
        # Check if crew has a manager role
        if "manager" not in crew.members:
            raise ValueError(
                "Hierarchical mode requires a 'manager' role in the crew. "
                "Add a manager role with delegation=True to use this mode."
            )

        # Build delegation plan for manager
        task_summaries = []
        for task in plan.tasks:
            summary = {
                "task_id": task.id,
                "description": task.description,
                "assigned_role": task.assigned_role,
                "dependencies": task.dependencies,
                "has_condition": task.condition is not None,
            }
            task_summaries.append(summary)

        # Create manager coordination prompt
        import json
        tasks_json = json.dumps(task_summaries, indent=2)

        manager_prompt = f"""You are the team manager coordinating a multi-agent workflow.

**Orchestration Plan**:
{tasks_json}

**Your Tasks**:
1. Review the task list and dependencies
2. Coordinate task execution by delegating to appropriate team members
3. Ensure dependencies are respected (delegate dependent tasks only after their dependencies complete)
4. Use the `delegate` tool to assign tasks to team members
5. Collect results from all tasks
6. Provide a summary of the overall workflow outcome

**Available Team Members**: {', '.join(crew.list_roles())}

**Execution Mode**: Hierarchical (you coordinate all tasks)

Please begin by delegating the first independent tasks."""

        # Get manager agent
        manager_agent = crew._get_or_create_agent("manager")

        # Execute manager coordination
        manager_result = await manager_agent.run(manager_prompt)

        # Parse manager result to extract task results
        # Note: In a more advanced implementation, we would parse the manager's
        # delegation actions and map them back to task IDs
        results: Dict[str, Any] = {
            "_manager_coordination": {
                "status": "completed",
                "result": manager_result,
                "mode": "hierarchical",
                "coordinated_tasks": len(plan.tasks),
            }
        }

        # Add summary to shared context
        plan.shared_context["_hierarchical_summary"] = manager_result

        return results

    def _topological_sort(self, tasks: List[Task]) -> List[Task]:
        """
        Topologically sort tasks by dependencies.

        Uses Kahn's algorithm for topological sorting.

        Args:
            tasks: List of tasks to sort

        Returns:
            List[Task]: Tasks in execution order

        Raises:
            ValueError: If circular dependencies detected
        """
        # Build adjacency list and in-degree map
        task_map = {t.id: t for t in tasks}
        in_degree: Dict[str, int] = {t.id: 0 for t in tasks}
        adjacency: Dict[str, List[str]] = {t.id: [] for t in tasks}

        for task in tasks:
            for dep_id in task.dependencies:
                adjacency[dep_id].append(task.id)
                in_degree[task.id] += 1

        # Find tasks with no dependencies
        queue = [tid for tid, degree in in_degree.items() if degree == 0]
        sorted_ids: List[str] = []

        while queue:
            # Pop task with no remaining dependencies
            current_id = queue.pop(0)
            sorted_ids.append(current_id)

            # Decrease in-degree for dependent tasks
            for dependent_id in adjacency[current_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        # Check for circular dependencies
        if len(sorted_ids) != len(tasks):
            raise ValueError(
                "Circular dependencies detected in task graph. "
                f"Sorted {len(sorted_ids)} tasks out of {len(tasks)}."
            )

        return [task_map[tid] for tid in sorted_ids]

    def _group_by_dependencies(self, tasks: List[Task]) -> List[List[Task]]:
        """
        Group tasks into levels for parallel execution.

        Tasks in the same level have no dependencies on each other.
        Levels are ordered so that all dependencies of a level are in previous levels.

        Args:
            tasks: List of tasks to group

        Returns:
            List[List[Task]]: List of task groups (levels)
        """
        task_map = {t.id: t for t in tasks}
        completed: Set[str] = set()
        groups: List[List[Task]] = []

        while len(completed) < len(tasks):
            # Find tasks whose dependencies are all completed
            current_level = []
            for task in tasks:
                if task.id in completed:
                    continue

                # Check if all dependencies are completed
                deps_satisfied = all(dep in completed for dep in task.dependencies)
                if deps_satisfied:
                    current_level.append(task)

            if not current_level:
                # No progress made - circular dependency
                remaining = [t.id for t in tasks if t.id not in completed]
                raise ValueError(
                    f"Circular dependencies detected. Cannot schedule: {remaining}"
                )

            groups.append(current_level)
            completed.update(t.id for t in current_level)

        return groups

    def _build_task_context(
        self,
        task: Task,
        results: Dict[str, Any],
        shared_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build execution context for a task.

        Combines task-specific context with dependency results and shared context.

        Args:
            task: Task to build context for
            results: Results from completed tasks
            shared_context: Shared context dictionary

        Returns:
            Dict[str, Any]: Complete task context
        """
        context = {
            **shared_context,
            **task.context,
        }

        # Add dependency results
        dependency_results = {}
        for dep_id in task.dependencies:
            if dep_id in results:
                dependency_results[dep_id] = results[dep_id]

        if dependency_results:
            context["dependency_results"] = dependency_results

        return context
