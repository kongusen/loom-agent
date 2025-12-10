"""
测试 DelegateTool - 委托工具功能测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.builtin.tools.delegate import DelegateTool, DelegateInput
from loom.crew.crew import Crew, CrewMember
from loom.crew.roles import Role, BUILTIN_ROLES
from loom.crew.orchestration import Task


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
def delegate_tool(test_crew):
    """DelegateTool 实例"""
    return DelegateTool(crew=test_crew)


# ============================================================================
# DelegateInput Tests
# ============================================================================


class TestDelegateInput:
    """测试 DelegateInput 参数模型"""

    def test_minimal_input(self):
        """测试最小输入参数"""
        input_data = DelegateInput(
            task_description="Test task",
            prompt="Do something",
            target_role="researcher"
        )

        assert input_data.task_description == "Test task"
        assert input_data.prompt == "Do something"
        assert input_data.target_role == "researcher"
        assert input_data.context == {}

    def test_input_with_context(self):
        """测试带上下文的输入"""
        context = {"key": "value", "number": 42}
        input_data = DelegateInput(
            task_description="Task with context",
            prompt="Use the context",
            target_role="developer",
            context=context
        )

        assert input_data.context == context


# ============================================================================
# DelegateTool Initialization Tests
# ============================================================================


class TestDelegateToolInit:
    """测试 DelegateTool 初始化"""

    def test_initialization(self, test_crew):
        """测试基本初始化"""
        tool = DelegateTool(crew=test_crew)

        assert tool.crew is test_crew
        assert tool.name == "delegate"
        assert tool.is_concurrency_safe is True
        assert tool.category == "coordination"

    def test_initial_stats(self, delegate_tool):
        """测试初始统计信息"""
        stats = delegate_tool.get_delegation_stats()

        assert stats["total_delegations"] == 0
        assert stats["successful_delegations"] == 0
        assert stats["failed_delegations"] == 0
        assert stats["success_rate"] == 0
        assert stats["delegations_by_role"] == {}


# ============================================================================
# DelegateTool Execution Tests
# ============================================================================


class TestDelegateToolExecution:
    """测试 DelegateTool 执行功能"""

    @pytest.mark.asyncio
    async def test_successful_delegation(self, delegate_tool, test_crew):
        """测试成功的委托"""
        # Mock crew.execute_task
        expected_result = "Research completed successfully"
        test_crew.execute_task = AsyncMock(return_value=expected_result)

        result = await delegate_tool.run(
            task_description="Research code",
            prompt="Analyze the authentication module",
            target_role="researcher"
        )

        # 验证结果格式
        assert "Delegated Task: Research code" in result
        assert "Assigned to**: researcher" in result
        assert expected_result in result

        # 验证 execute_task 被调用
        test_crew.execute_task.assert_called_once()
        call_args = test_crew.execute_task.call_args

        # 验证传递的任务对象
        task = call_args[0][0]
        assert isinstance(task, Task)
        assert task.description == "Research code"
        assert task.prompt == "Analyze the authentication module"
        assert task.assigned_role == "researcher"

    @pytest.mark.asyncio
    async def test_delegation_with_context(self, delegate_tool, test_crew):
        """测试带上下文的委托"""
        test_crew.execute_task = AsyncMock(return_value="Task completed")
        context = {"file": "auth.py", "line": 42}

        result = await delegate_tool.run(
            task_description="Review code",
            prompt="Check for security issues",
            target_role="developer",
            context=context
        )

        # 验证上下文被传递
        call_args = test_crew.execute_task.call_args
        task = call_args[0][0]
        assert task.context == context

        # 验证 context 参数也被传递
        context_arg = call_args[1].get("context")
        assert context_arg == context

    @pytest.mark.asyncio
    async def test_delegation_to_invalid_role(self, delegate_tool):
        """测试委托给不存在的角色"""
        result = await delegate_tool.run(
            task_description="Invalid delegation",
            prompt="This should fail",
            target_role="nonexistent_role"
        )

        assert "Delegation Error" in result
        assert "nonexistent_role" in result
        assert "not found in crew" in result
        assert "Available roles:" in result

    @pytest.mark.asyncio
    async def test_delegation_execution_error(self, delegate_tool, test_crew):
        """测试执行时发生错误"""
        # Mock execute_task 抛出异常
        test_crew.execute_task = AsyncMock(
            side_effect=Exception("Execution failed")
        )

        result = await delegate_tool.run(
            task_description="Failing task",
            prompt="This will error",
            target_role="researcher"
        )

        assert "Delegation Error" in result
        assert "Failing task" in result
        assert "researcher" in result
        assert "Execution failed" in result


# ============================================================================
# Statistics Tests
# ============================================================================


class TestDelegationStatistics:
    """测试委托统计功能"""

    @pytest.mark.asyncio
    async def test_stats_after_successful_delegation(self, delegate_tool, test_crew):
        """测试成功委托后的统计"""
        test_crew.execute_task = AsyncMock(return_value="Success")

        await delegate_tool.run(
            task_description="Task 1",
            prompt="Do task 1",
            target_role="researcher"
        )

        stats = delegate_tool.get_delegation_stats()
        assert stats["total_delegations"] == 1
        assert stats["successful_delegations"] == 1
        assert stats["failed_delegations"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["delegations_by_role"]["researcher"] == 1

    @pytest.mark.asyncio
    async def test_stats_after_failed_delegation(self, delegate_tool):
        """测试失败委托后的统计"""
        await delegate_tool.run(
            task_description="Invalid",
            prompt="Fail",
            target_role="invalid"
        )

        stats = delegate_tool.get_delegation_stats()
        assert stats["total_delegations"] == 1
        assert stats["successful_delegations"] == 0
        assert stats["failed_delegations"] == 1
        assert stats["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_stats_multiple_delegations(self, delegate_tool, test_crew):
        """测试多次委托的统计"""
        test_crew.execute_task = AsyncMock(return_value="Success")

        # 3 次成功委托
        await delegate_tool.run("Task 1", "Do 1", "researcher")
        await delegate_tool.run("Task 2", "Do 2", "developer")
        await delegate_tool.run("Task 3", "Do 3", "researcher")

        # 1 次失败委托
        await delegate_tool.run("Task 4", "Do 4", "invalid_role")

        stats = delegate_tool.get_delegation_stats()
        assert stats["total_delegations"] == 4
        assert stats["successful_delegations"] == 3
        assert stats["failed_delegations"] == 1
        assert stats["success_rate"] == 0.75
        assert stats["delegations_by_role"]["researcher"] == 2
        assert stats["delegations_by_role"]["developer"] == 1

    def test_reset_stats(self, delegate_tool):
        """测试重置统计"""
        # 修改统计数据
        delegate_tool._delegation_stats["total_delegations"] = 10
        delegate_tool._delegation_stats["successful_delegations"] = 8

        # 重置
        delegate_tool.reset_stats()

        # 验证重置
        stats = delegate_tool.get_delegation_stats()
        assert stats["total_delegations"] == 0
        assert stats["successful_delegations"] == 0
        assert stats["failed_delegations"] == 0
        assert stats["delegations_by_role"] == {}


# ============================================================================
# Utility Functions Tests
# ============================================================================


class TestDelegateToolUtilities:
    """测试 DelegateTool 工具方法"""

    def test_list_available_roles(self, delegate_tool):
        """测试列出可用角色"""
        roles = delegate_tool.list_available_roles()

        assert isinstance(roles, list)
        assert "manager" in roles
        assert "researcher" in roles
        assert "developer" in roles

    def test_format_delegation_result(self, delegate_tool):
        """测试格式化委托结果"""
        result = delegate_tool._format_delegation_result(
            task_description="Test task",
            target_role="researcher",
            result="Task completed successfully"
        )

        assert "Delegated Task: Test task" in result
        assert "Assigned to**: researcher" in result
        assert "Task completed successfully" in result


# ============================================================================
# Integration Tests
# ============================================================================


class TestDelegateToolIntegration:
    """测试 DelegateTool 与 Crew 的集成"""

    @pytest.mark.asyncio
    async def test_manager_can_delegate_to_team(self, test_crew, mock_llm):
        """测试 manager 可以委托任务给团队成员"""
        # 创建 DelegateTool 并添加到 manager
        delegate_tool = DelegateTool(crew=test_crew)

        # Mock execute_task
        test_crew.execute_task = AsyncMock(
            return_value="Researcher found 5 security issues"
        )

        # Manager 委托安全审计任务
        result = await delegate_tool.run(
            task_description="Security audit",
            prompt="Audit the authentication module for vulnerabilities",
            target_role="researcher",
            context={"module": "auth.py"}
        )

        assert "Security audit" in result
        assert "researcher" in result
        assert "5 security issues" in result

    @pytest.mark.asyncio
    async def test_multiple_sequential_delegations(self, delegate_tool, test_crew):
        """测试多次顺序委托"""
        # Mock 不同角色的返回结果
        async def mock_execute(task, context=None):
            if task.assigned_role == "researcher":
                return "Research findings: API uses JWT tokens"
            elif task.assigned_role == "developer":
                return "Implementation complete: Added token refresh"
            return "Task completed"

        test_crew.execute_task = AsyncMock(side_effect=mock_execute)

        # Manager 顺序委托多个任务
        result1 = await delegate_tool.run(
            "Research auth", "Research authentication system", "researcher"
        )
        result2 = await delegate_tool.run(
            "Implement feature", "Add token refresh mechanism", "developer"
        )

        assert "JWT tokens" in result1
        assert "token refresh" in result2

        # 验证统计
        stats = delegate_tool.get_delegation_stats()
        assert stats["total_delegations"] == 2
        assert stats["successful_delegations"] == 2
        assert stats["delegations_by_role"]["researcher"] == 1
        assert stats["delegations_by_role"]["developer"] == 1
