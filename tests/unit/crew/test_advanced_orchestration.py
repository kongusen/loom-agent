"""
测试高级编排模式 - CONDITIONAL 和 HIERARCHICAL 模式增强
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from loom.crew import (
    Crew,
    Task,
    OrchestrationPlan,
    OrchestrationMode,
    Orchestrator,
    ConditionBuilder,
    BUILTIN_ROLES,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm():
    """Mock LLM for testing"""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value="Mock LLM response")
    return llm


@pytest.fixture
def test_roles():
    """测试角色列表"""
    return [
        BUILTIN_ROLES["manager"],
        BUILTIN_ROLES["researcher"],
        BUILTIN_ROLES["developer"],
    ]


@pytest.fixture
def test_crew(test_roles, mock_llm):
    """测试 Crew 实例"""
    return Crew(roles=test_roles, llm=mock_llm)


@pytest.fixture
def orchestrator():
    """Orchestrator 实例"""
    return Orchestrator()


# ============================================================================
# ConditionBuilder Tests
# ============================================================================


class TestConditionBuilder:
    """测试 ConditionBuilder 辅助类"""

    def test_key_exists(self):
        """测试 key_exists 条件"""
        condition = ConditionBuilder.key_exists("test_key")

        assert condition({"test_key": "value"}) is True
        assert condition({"other_key": "value"}) is False
        assert condition({}) is False

    def test_key_equals(self):
        """测试 key_equals 条件"""
        condition = ConditionBuilder.key_equals("status", "complete")

        assert condition({"status": "complete"}) is True
        assert condition({"status": "pending"}) is False
        assert condition({}) is False

    def test_key_in_list(self):
        """测试 key_in_list 条件"""
        condition = ConditionBuilder.key_in_list("level", ["high", "critical"])

        assert condition({"level": "high"}) is True
        assert condition({"level": "critical"}) is True
        assert condition({"level": "low"}) is False
        assert condition({}) is False

    def test_and_all(self):
        """测试 and_all 组合条件"""
        condition = ConditionBuilder.and_all([
            lambda ctx: "key1" in ctx,
            lambda ctx: "key2" in ctx,
            lambda ctx: ctx.get("value", 0) > 5
        ])

        assert condition({"key1": 1, "key2": 2, "value": 10}) is True
        assert condition({"key1": 1, "key2": 2, "value": 3}) is False
        assert condition({"key1": 1}) is False

    def test_or_any(self):
        """测试 or_any 组合条件"""
        condition = ConditionBuilder.or_any([
            lambda ctx: ctx.get("path_a") == "ok",
            lambda ctx: ctx.get("path_b") == "ok"
        ])

        assert condition({"path_a": "ok"}) is True
        assert condition({"path_b": "ok"}) is True
        assert condition({"path_a": "ok", "path_b": "ok"}) is True
        assert condition({"path_a": "fail", "path_b": "fail"}) is False

    def test_not_(self):
        """测试 not_ 否定条件"""
        condition = ConditionBuilder.not_(
            lambda ctx: ctx.get("has_error", False)
        )

        assert condition({"has_error": False}) is True
        assert condition({"has_error": True}) is False
        assert condition({}) is True  # Default False

    def test_complex_combination(self):
        """测试复杂组合条件"""
        # (key1 exists AND key2 exists) OR (NOT has_error)
        condition = ConditionBuilder.or_any([
            ConditionBuilder.and_all([
                ConditionBuilder.key_exists("key1"),
                ConditionBuilder.key_exists("key2")
            ]),
            ConditionBuilder.not_(lambda ctx: ctx.get("has_error", False))
        ])

        assert condition({"key1": 1, "key2": 2}) is True
        assert condition({"has_error": False}) is True
        assert condition({"has_error": True, "key1": 1}) is False
        assert condition({}) is True  # No error by default


# ============================================================================
# CONDITIONAL Mode Tests
# ============================================================================


class TestConditionalMode:
    """测试 CONDITIONAL 编排模式"""

    @pytest.mark.asyncio
    async def test_conditional_all_tasks_execute(self, orchestrator, test_crew):
        """测试所有任务都满足条件时的执行"""
        # Mock execute_task
        test_crew.execute_task = AsyncMock(
            side_effect=lambda task, context: f"Result of {task.id}"
        )

        # 创建无条件任务
        tasks = [
            Task(
                id="task1",
                description="Task 1",
                prompt="Do task 1",
                assigned_role="researcher",
            ),
            Task(
                id="task2",
                description="Task 2",
                prompt="Do task 2",
                assigned_role="developer",
            ),
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.CONDITIONAL
        )

        results = await orchestrator.execute(plan, test_crew)

        # 验证所有任务都执行了
        assert results["task1"]["status"] == "completed"
        assert results["task2"]["status"] == "completed"
        assert "Result of task1" in results["task1"]["result"]
        assert "Result of task2" in results["task2"]["result"]

        # 验证统计信息
        stats = plan.shared_context["_conditional_stats"]
        assert stats["total_tasks"] == 2
        assert stats["executed"] == 2
        assert stats["skipped"] == 0

    @pytest.mark.asyncio
    async def test_conditional_some_tasks_skipped(self, orchestrator, test_crew):
        """测试部分任务因条件不满足而跳过"""
        test_crew.execute_task = AsyncMock(
            side_effect=lambda task, context: f"Result of {task.id}"
        )

        # 创建带条件的任务
        tasks = [
            Task(
                id="always_run",
                description="Always run",
                prompt="Task that always runs",
                assigned_role="researcher",
                output_key="research_done"
            ),
            Task(
                id="conditional_run",
                description="Conditional run",
                prompt="Task that runs conditionally",
                assigned_role="developer",
                condition=lambda ctx: ctx.get("research_done") is not None
            ),
            Task(
                id="never_run",
                description="Never run",
                prompt="Task that never runs",
                assigned_role="developer",
                condition=lambda ctx: False  # Always False
            ),
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.CONDITIONAL
        )

        results = await orchestrator.execute(plan, test_crew)

        # 验证执行和跳过的任务
        assert results["always_run"]["status"] == "completed"
        assert results["conditional_run"]["status"] == "completed"
        assert results["never_run"]["status"] == "skipped"
        assert results["never_run"]["reason"] == "condition_not_met"

        # 验证统计
        stats = plan.shared_context["_conditional_stats"]
        assert stats["executed"] == 2
        assert stats["skipped"] == 1
        assert "never_run" in stats["skipped_task_ids"]

    @pytest.mark.asyncio
    async def test_conditional_with_condition_builder(self, orchestrator, test_crew):
        """测试使用 ConditionBuilder 的条件任务"""
        test_crew.execute_task = AsyncMock(return_value="Task result")

        # 使用 ConditionBuilder 创建复杂条件
        tasks = [
            Task(
                id="setup",
                description="Setup",
                prompt="Initialize",
                assigned_role="researcher",
                output_key="initialized"
            ),
            Task(
                id="process",
                description="Process",
                prompt="Process data",
                assigned_role="developer",
                condition=ConditionBuilder.and_all([
                    ConditionBuilder.key_exists("initialized"),
                    ConditionBuilder.not_(lambda ctx: ctx.get("has_error", False))
                ])
            ),
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.CONDITIONAL
        )

        results = await orchestrator.execute(plan, test_crew)

        # 两个任务都应该执行（setup 初始化，process 条件满足）
        assert results["setup"]["status"] == "completed"
        assert results["process"]["status"] == "completed"


# ============================================================================
# HIERARCHICAL Mode Tests
# ============================================================================


class TestHierarchicalMode:
    """测试 HIERARCHICAL 编排模式"""

    @pytest.mark.asyncio
    async def test_hierarchical_requires_manager(self, orchestrator):
        """测试 HIERARCHICAL 模式需要 manager 角色"""
        # 创建没有 manager 的 crew
        crew_without_manager = Crew(
            roles=[BUILTIN_ROLES["researcher"], BUILTIN_ROLES["developer"]],
            llm=MagicMock()
        )

        tasks = [
            Task("task1", "Task 1", "Do task 1", "researcher")
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.HIERARCHICAL
        )

        # 应该抛出 ValueError
        with pytest.raises(ValueError, match="manager.*role"):
            await orchestrator.execute(plan, crew_without_manager)

    @pytest.mark.asyncio
    async def test_hierarchical_manager_coordination(self, orchestrator, test_crew, mock_llm):
        """测试 manager 协调任务执行"""
        # Mock manager agent's run method
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="Manager coordinated all tasks successfully")

        # Mock _get_or_create_agent to return our mock
        test_crew._get_or_create_agent = MagicMock(return_value=mock_agent)

        tasks = [
            Task("research", "Research", "Do research", "researcher"),
            Task("develop", "Develop", "Develop feature", "developer",
                 dependencies=["research"]),
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.HIERARCHICAL
        )

        results = await orchestrator.execute(plan, test_crew)

        # 验证 manager 被调用
        test_crew._get_or_create_agent.assert_called_once_with("manager")
        mock_agent.run.assert_called_once()

        # 验证调用的 prompt 包含任务信息
        call_args = mock_agent.run.call_args[0][0]
        assert "research" in call_args
        assert "develop" in call_args
        assert "dependencies" in call_args

        # 验证返回结果
        assert "_manager_coordination" in results
        assert results["_manager_coordination"]["status"] == "completed"
        assert results["_manager_coordination"]["mode"] == "hierarchical"
        assert results["_manager_coordination"]["coordinated_tasks"] == 2

        # 验证 shared context
        assert "_hierarchical_summary" in plan.shared_context

    @pytest.mark.asyncio
    async def test_hierarchical_includes_task_details(self, orchestrator, test_crew):
        """测试 manager prompt 包含详细的任务信息"""
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="Coordination complete")
        test_crew._get_or_create_agent = MagicMock(return_value=mock_agent)

        tasks = [
            Task(
                "task_with_condition",
                "Conditional task",
                "Do conditionally",
                "researcher",
                condition=lambda ctx: True
            ),
            Task(
                "task_with_deps",
                "Dependent task",
                "Do after first",
                "developer",
                dependencies=["task_with_condition"]
            ),
        ]

        plan = OrchestrationPlan(
            tasks=tasks,
            mode=OrchestrationMode.HIERARCHICAL
        )

        await orchestrator.execute(plan, test_crew)

        # 检查 prompt 内容
        prompt = mock_agent.run.call_args[0][0]
        assert "task_with_condition" in prompt
        assert "task_with_deps" in prompt
        assert "has_condition" in prompt
        assert "dependencies" in prompt
