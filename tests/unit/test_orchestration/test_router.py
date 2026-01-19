"""
Router Orchestrator Unit Tests

测试路由编排器的核心功能
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.orchestration.router import RouterOrchestrator
from loom.protocol import AgentCapability, AgentCard, Task, TaskStatus


class TestRouterOrchestratorInit:
    """测试路由编排器初始化"""

    def test_init_without_nodes(self):
        """测试无节点初始化"""
        router = RouterOrchestrator()
        assert router.nodes == []

    def test_init_with_nodes(self):
        """测试带节点初始化"""
        mock_node1 = Mock()
        mock_node2 = Mock()

        router = RouterOrchestrator(nodes=[mock_node1, mock_node2])
        assert len(router.nodes) == 2


class TestRouterOrchestratorOrchestrate:
    """测试路由编排器的orchestrate方法"""

    @pytest.mark.asyncio
    async def test_orchestrate_no_nodes(self):
        """测试无节点时的编排"""
        router = RouterOrchestrator()
        task = Task(task_id="test_task", action="test_action")

        result = await router.orchestrate(task)

        assert result.status == TaskStatus.FAILED
        assert result.error == "No nodes available"

    @pytest.mark.asyncio
    async def test_orchestrate_with_node_success(self):
        """测试成功编排到节点"""
        mock_node = Mock()
        mock_node.execute_task = AsyncMock(
            return_value=Task(
                task_id="test_task",
                action="test_action",
                result={"data": "success"},
                status=TaskStatus.COMPLETED,
            )
        )

        router = RouterOrchestrator(nodes=[mock_node])
        task = Task(task_id="test_task", action="test_action")

        result = await router.orchestrate(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.result["data"] == "success"
        mock_node.execute_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrate_node_execution_error(self):
        """测试节点执行错误"""
        mock_node = Mock()
        mock_node.execute_task = AsyncMock(side_effect=ValueError("Execution failed"))

        router = RouterOrchestrator(nodes=[mock_node])
        task = Task(task_id="test_task", action="test_action")

        result = await router.orchestrate(task)

        assert result.status == TaskStatus.FAILED
        assert "Execution failed" in result.error


class TestRouterOrchestratorNodeSelection:
    """测试路由编排器的节点选择逻辑"""

    def test_select_node_no_nodes(self):
        """测试无节点时的选择"""
        router = RouterOrchestrator()
        task = Task(task_id="test_task", action="test_action")

        selected = router._select_node(task)
        assert selected is None

    def test_select_node_tool_use_capability(self):
        """测试选择tool_use能力的节点"""
        # 创建带tool_use能力的节点
        mock_node_tool = Mock()
        mock_node_tool.get_capabilities = Mock(
            return_value=AgentCard(
                agent_id="tool_agent",
                name="Tool Agent",
                description="Tool agent",
                capabilities=[AgentCapability.TOOL_USE],
            )
        )

        # 创建其他节点
        mock_node_other = Mock()
        mock_node_other.get_capabilities = Mock(
            return_value=AgentCard(
                agent_id="other_agent",
                name="Other Agent",
                description="Other agent",
                capabilities=[AgentCapability.PLANNING],
            )
        )

        router = RouterOrchestrator(nodes=[mock_node_other, mock_node_tool])
        task = Task(task_id="test_task", action="use_tool_to_fetch_data")

        selected = router._select_node(task)
        assert selected == mock_node_tool

    def test_select_node_planning_capability(self):
        """测试选择planning能力的节点"""
        mock_node_plan = Mock()
        mock_node_plan.get_capabilities = Mock(
            return_value=AgentCard(
                agent_id="plan_agent",
                name="Planning Agent",
                description="Planning agent",
                capabilities=[AgentCapability.PLANNING],
            )
        )

        mock_node_other = Mock()
        mock_node_other.get_capabilities = Mock(
            return_value=AgentCard(
                agent_id="other_agent",
                name="Other Agent",
                description="Other agent",
                capabilities=[AgentCapability.TOOL_USE],
            )
        )

        router = RouterOrchestrator(nodes=[mock_node_other, mock_node_plan])
        task = Task(task_id="test_task", action="plan_the_project")

        selected = router._select_node(task)
        assert selected == mock_node_plan

    def test_select_node_reflection_capability(self):
        """测试选择reflection能力的节点"""
        mock_node_reflect = Mock()
        mock_node_reflect.get_capabilities = Mock(
            return_value=AgentCard(
                agent_id="reflect_agent",
                name="Reflection Agent",
                description="Reflection agent",
                capabilities=[AgentCapability.REFLECTION],
            )
        )

        mock_node_other = Mock()
        mock_node_other.get_capabilities = Mock(
            return_value=AgentCard(
                agent_id="other_agent",
                name="Other Agent",
                description="Other agent",
                capabilities=[AgentCapability.TOOL_USE],
            )
        )

        router = RouterOrchestrator(nodes=[mock_node_other, mock_node_reflect])
        task = Task(task_id="test_task", action="reflect_on_results")

        selected = router._select_node(task)
        assert selected == mock_node_reflect

    def test_select_node_multi_agent_capability(self):
        """测试选择multi_agent能力的节点"""
        mock_node_multi = Mock()
        mock_node_multi.get_capabilities = Mock(
            return_value=AgentCard(
                agent_id="multi_agent",
                name="Multi Agent",
                description="Multi agent",
                capabilities=[AgentCapability.MULTI_AGENT],
            )
        )

        mock_node_other = Mock()
        mock_node_other.get_capabilities = Mock(
            return_value=AgentCard(
                agent_id="other_agent",
                name="Other Agent",
                description="Other agent",
                capabilities=[AgentCapability.TOOL_USE],
            )
        )

        router = RouterOrchestrator(nodes=[mock_node_other, mock_node_multi])
        task = Task(task_id="test_task", action="multi_agent_collaboration")

        selected = router._select_node(task)
        assert selected == mock_node_multi

    def test_select_node_fallback_strategy(self):
        """测试降级策略（无匹配时返回第一个节点）"""
        mock_node1 = Mock()
        mock_node1.get_capabilities = Mock(
            return_value=AgentCard(
                agent_id="node1",
                name="Node 1",
                description="Node 1",
                capabilities=[AgentCapability.TOOL_USE],
            )
        )

        mock_node2 = Mock()
        mock_node2.get_capabilities = Mock(
            return_value=AgentCard(
                agent_id="node2",
                name="Node 2",
                description="Node 2",
                capabilities=[AgentCapability.PLANNING],
            )
        )

        router = RouterOrchestrator(nodes=[mock_node1, mock_node2])
        # 使用不匹配任何关键词的action
        task = Task(task_id="test_task", action="some_random_action")

        selected = router._select_node(task)
        # 应该返回第一个节点（降级策略）
        assert selected == mock_node1

    def test_select_node_no_capabilities_method(self):
        """测试节点没有get_capabilities方法时的处理"""
        mock_node_no_cap = Mock()
        mock_node_no_cap.get_capabilities = Mock(side_effect=AttributeError("No capabilities"))

        mock_node_fallback = Mock()

        router = RouterOrchestrator(nodes=[mock_node_no_cap, mock_node_fallback])
        task = Task(task_id="test_task", action="use_tool")

        selected = router._select_node(task)
        # 应该跳过异常节点，返回降级策略（第一个节点）
        assert selected == mock_node_no_cap
