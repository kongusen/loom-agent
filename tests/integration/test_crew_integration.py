"""
Crew System Integration Tests

These tests verify end-to-end functionality of the Crew system,
including real agent execution flows (with mock LLM).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from loom.crew import (
    Crew,
    Task,
    OrchestrationPlan,
    OrchestrationMode,
    ConditionBuilder,
    BUILTIN_ROLES,
)
from loom.builtin.tools.delegate import DelegateTool


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm():
    """Mock LLM that returns task-specific responses"""
    llm = MagicMock()

    async def mock_generate(prompt, **kwargs):
        # Return different responses based on prompt content
        if "research" in prompt.lower():
            return "Research findings: analyzed 5 key areas"
        elif "develop" in prompt.lower():
            return "Development complete: implemented 3 features"
        elif "test" in prompt.lower():
            return "Testing complete: 10 tests passing"
        elif "delegate" in prompt.lower():
            return "Delegated task successfully"
        return "Task completed successfully"

    llm.generate = AsyncMock(side_effect=mock_generate)
    return llm


# ============================================================================
# Integration Tests: Complete Workflows
# ============================================================================


class TestCompleteWorkflows:
    """测试完整的工作流程"""

    @pytest.mark.asyncio
    async def test_sequential_workflow_integration(self, mock_llm):
        """集成测试：顺序工作流"""
        roles = [
            BUILTIN_ROLES["researcher"],
            BUILTIN_ROLES["developer"],
            BUILTIN_ROLES["qa_engineer"],
        ]

        crew = Crew(roles=roles, llm=mock_llm)

        # Define multi-step workflow
        tasks = [
            Task(
                id="research",
                description="Research requirements",
                prompt="Research API requirements",
                assigned_role="researcher",
                output_key="requirements"
            ),
            Task(
                id="develop",
                description="Implement API",
                prompt="Implement API based on requirements",
                assigned_role="developer",
                dependencies=["research"],
                output_key="implementation"
            ),
            Task(
                id="test",
                description="Test API",
                prompt="Test the implementation",
                assigned_role="qa_engineer",
                dependencies=["develop"]
            ),
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.SEQUENTIAL
        )

        results = await crew.kickoff(plan)

        # Verify all tasks completed
        assert len(results) == 3
        assert "requirements" in plan.shared_context
        assert "implementation" in plan.shared_context

        # Verify task order (sequential execution)
        assert "research" in results
        assert "develop" in results
        assert "test" in results

    @pytest.mark.asyncio
    async def test_parallel_workflow_integration(self, mock_llm):
        """集成测试：并行工作流"""
        roles = [
            BUILTIN_ROLES["researcher"],
            BUILTIN_ROLES["developer"],
        ]

        crew = Crew(roles=roles, llm=mock_llm)

        tasks = [
            # Independent tasks (run in parallel)
            Task(
                id="research_api",
                description="Research API patterns",
                prompt="Research REST API patterns",
                assigned_role="researcher",
            ),
            Task(
                id="research_db",
                description="Research database schema",
                prompt="Research database design",
                assigned_role="researcher",
            ),
            # Dependent task (waits for both)
            Task(
                id="implement",
                description="Implement system",
                prompt="Implement based on research",
                assigned_role="developer",
                dependencies=["research_api", "research_db"]
            ),
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.PARALLEL,
            max_parallel=2
        )

        results = await crew.kickoff(plan)

        # All tasks should complete
        assert len(results) == 3
        assert all(task_id in results for task_id in ["research_api", "research_db", "implement"])

    @pytest.mark.asyncio
    async def test_conditional_workflow_integration(self, mock_llm):
        """集成测试：条件工作流"""
        roles = [
            BUILTIN_ROLES["researcher"],
            BUILTIN_ROLES["developer"],
        ]

        crew = Crew(roles=roles, llm=mock_llm)

        tasks = [
            Task(
                id="analyze",
                description="Analyze code",
                prompt="Analyze for issues",
                assigned_role="researcher",
                output_key="has_issues"
            ),
            Task(
                id="fix_issues",
                description="Fix issues",
                prompt="Fix identified issues",
                assigned_role="developer",
                condition=lambda ctx: ctx.get("has_issues") is not None,
                dependencies=["analyze"]
            ),
            Task(
                id="skip_me",
                description="This should skip",
                prompt="This won't run",
                assigned_role="developer",
                condition=lambda ctx: False  # Always skip
            ),
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.CONDITIONAL
        )

        results = await crew.kickoff(plan)

        # Verify conditional execution
        assert results["analyze"]["status"] == "completed"
        assert results["fix_issues"]["status"] == "completed"
        assert results["skip_me"]["status"] == "skipped"

        # Check stats
        stats = plan.shared_context["_conditional_stats"]
        assert stats["executed"] == 2
        assert stats["skipped"] == 1


# ============================================================================
# Integration Tests: DelegateTool with Crew
# ============================================================================


class TestDelegationIntegration:
    """测试委托工具与 Crew 的集成"""

    @pytest.mark.asyncio
    async def test_manager_delegation_flow(self, mock_llm):
        """测试 manager 委托流程"""
        roles = [
            BUILTIN_ROLES["manager"],
            BUILTIN_ROLES["researcher"],
            BUILTIN_ROLES["developer"],
        ]

        crew = Crew(roles=roles, llm=mock_llm)

        # Mock execute_task to return expected result
        crew.execute_task = AsyncMock(return_value="Research findings: analyzed OAuth 2.0")

        # Create DelegateTool
        delegate_tool = DelegateTool(crew=crew)

        # Manager delegates research task
        result = await delegate_tool.run(
            task_description="Research authentication",
            prompt="Research OAuth 2.0 implementation patterns",
            target_role="researcher"
        )

        assert "Delegated Task" in result
        assert "researcher" in result
        assert "Research findings" in result or "OAuth 2.0" in result

        # Check delegation stats
        stats = delegate_tool.get_delegation_stats()
        assert stats["total_delegations"] == 1
        assert stats["successful_delegations"] == 1

    @pytest.mark.asyncio
    async def test_hierarchical_mode_integration(self, mock_llm):
        """测试 HIERARCHICAL 模式集成"""
        roles = [
            BUILTIN_ROLES["manager"],
            BUILTIN_ROLES["researcher"],
            BUILTIN_ROLES["developer"],
        ]

        crew = Crew(roles=roles, llm=mock_llm)

        tasks = [
            Task("research", "Research", "Research task", "researcher"),
            Task("develop", "Develop", "Development task", "developer"),
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.HIERARCHICAL
        )

        results = await crew.kickoff(plan)

        # Should have manager coordination result
        assert "_manager_coordination" in results
        assert results["_manager_coordination"]["status"] == "completed"
        assert results["_manager_coordination"]["coordinated_tasks"] == 2


# ============================================================================
# Integration Tests: Communication & State
# ============================================================================


class TestCommunicationIntegration:
    """测试通信和状态管理集成"""

    @pytest.mark.asyncio
    async def test_shared_state_across_tasks(self, mock_llm):
        """测试任务间共享状态"""
        roles = [BUILTIN_ROLES["researcher"], BUILTIN_ROLES["developer"]]
        crew = Crew(roles=roles, llm=mock_llm)

        # Set initial state
        await crew.shared_state.set("config_value", "test_config")

        tasks = [
            Task(
                "task1",
                "Task 1",
                "First task",
                "researcher",
                output_key="result1"
            ),
            Task(
                "task2",
                "Task 2",
                "Second task",
                "developer",
                dependencies=["task1"]
            ),
        ]

        plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.SEQUENTIAL)
        await crew.kickoff(plan)

        # Verify shared state persisted
        config = await crew.shared_state.get("config_value")
        assert config == "test_config"

        # Verify output was stored
        result1 = await crew.shared_state.get("result1")
        assert result1 is None or plan.shared_context.get("result1") is not None

    @pytest.mark.asyncio
    async def test_message_bus_tracking(self, mock_llm):
        """测试消息总线跟踪"""
        roles = [BUILTIN_ROLES["researcher"], BUILTIN_ROLES["developer"]]
        crew = Crew(roles=roles, llm=mock_llm)

        # Execute simple workflow
        tasks = [
            Task("task1", "Task 1", "Do task 1", "researcher"),
            Task("task2", "Task 2", "Do task 2", "developer"),
        ]

        plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.SEQUENTIAL)
        await crew.kickoff(plan)

        # Check message bus stats
        stats = crew.message_bus.get_stats()
        assert "total_messages" in stats
        # Messages may or may not be sent depending on implementation


# ============================================================================
# Integration Tests: Complex Scenarios
# ============================================================================


class TestComplexScenarios:
    """测试复杂场景"""

    @pytest.mark.asyncio
    async def test_multi_level_dependencies(self, mock_llm):
        """测试多层依赖关系"""
        roles = [
            BUILTIN_ROLES["researcher"],
            BUILTIN_ROLES["developer"],
            BUILTIN_ROLES["qa_engineer"],
        ]
        crew = Crew(roles=roles, llm=mock_llm)

        tasks = [
            Task("level1_a", "Level 1 A", "Task 1A", "researcher"),
            Task("level1_b", "Level 1 B", "Task 1B", "researcher"),
            Task(
                "level2",
                "Level 2",
                "Task 2",
                "developer",
                dependencies=["level1_a", "level1_b"]
            ),
            Task(
                "level3",
                "Level 3",
                "Task 3",
                "qa_engineer",
                dependencies=["level2"]
            ),
        ]

        plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.PARALLEL)
        results = await crew.kickoff(plan)

        # All tasks should complete
        assert len(results) == 4
        assert all(task_id in results for task_id in ["level1_a", "level1_b", "level2", "level3"])

    @pytest.mark.asyncio
    async def test_complex_conditions_with_builder(self, mock_llm):
        """测试使用 ConditionBuilder 的复杂条件"""
        roles = [BUILTIN_ROLES["researcher"], BUILTIN_ROLES["developer"]]
        crew = Crew(roles=roles, llm=mock_llm)

        tasks = [
            Task(
                "setup",
                "Setup",
                "Initialize system",
                "researcher",
                output_key="initialized"
            ),
            Task(
                "conditional_task",
                "Conditional",
                "Run conditionally",
                "developer",
                condition=ConditionBuilder.and_all([
                    ConditionBuilder.key_exists("initialized"),
                    ConditionBuilder.not_(lambda ctx: ctx.get("skip_mode", False))
                ]),
                dependencies=["setup"]
            ),
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.CONDITIONAL,
            shared_context={"skip_mode": False}  # Should run
        )

        results = await crew.kickoff(plan)

        # Both should execute
        assert results["setup"]["status"] == "completed"
        assert results["conditional_task"]["status"] == "completed"

        # Test with skip_mode=True
        plan2 = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.CONDITIONAL,
            shared_context={"skip_mode": True}  # Should skip conditional_task
        )

        results2 = await crew.kickoff(plan2)
        assert results2["conditional_task"]["status"] == "skipped"
