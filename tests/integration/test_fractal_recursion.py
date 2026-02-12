"""
Fractal Recursion Tests

测试分形容器的递归组合能力，验证A3公理（分形自相似公理）。
"""

import pytest

from loom.agent.card import AgentCapability, AgentCard
from loom.fractal.container import NodeContainer
from loom.runtime import Task, TaskStatus
from tests.integration.mock_agents import MockAnalysisAgent


class TestFractalRecursion:
    """分形递归测试"""

    @pytest.mark.asyncio
    async def test_single_layer_container(self):
        """测试单层容器包装"""
        # 创建叶子节点
        leaf_agent = MockAnalysisAgent("leaf-1", "summary")

        # 创建容器包装叶子节点
        container = NodeContainer(
            node_id="container-1",
            agent_card=AgentCard(
                agent_id="container-1",
                name="Container Level 1",
                description="Single layer container",
                capabilities=[AgentCapability.MULTI_AGENT],
            ),
            child=leaf_agent,
        )

        # 创建任务
        task = Task(action="analyze", parameters={"text": "Test document for analysis"})

        # 执行任务
        result = await container.execute_task(task)

        # 验证结果
        assert result.status == TaskStatus.COMPLETED
        assert result.result is not None
        assert result.result["agent_id"] == "leaf-1"
        assert "summary" in result.result["result"].lower()

    @pytest.mark.asyncio
    async def test_two_layer_nested_container(self):
        """测试两层嵌套容器"""
        # 创建叶子节点
        leaf_agent = MockAnalysisAgent("leaf-2", "keyword")

        # 创建第一层容器
        container_l1 = NodeContainer(
            node_id="container-l1",
            agent_card=AgentCard(
                agent_id="container-l1",
                name="Container Level 1",
                description="First layer container",
                capabilities=[AgentCapability.MULTI_AGENT],
            ),
            child=leaf_agent,
        )

        # 创建第二层容器（包装第一层）
        container_l2 = NodeContainer(
            node_id="container-l2",
            agent_card=AgentCard(
                agent_id="container-l2",
                name="Container Level 2",
                description="Second layer container",
                capabilities=[AgentCapability.MULTI_AGENT],
            ),
            child=container_l1,
        )

        # 创建任务
        task = Task(action="analyze", parameters={"text": "Nested container test document"})

        # 执行任务（应该递归到叶子节点）
        result = await container_l2.execute_task(task)

        # 验证结果
        assert result.status == TaskStatus.COMPLETED
        assert result.result is not None
        assert result.result["agent_id"] == "leaf-2"
        assert result.result["analysis_type"] == "keyword"

    @pytest.mark.asyncio
    async def test_three_layer_deep_nesting(self):
        """测试三层深度嵌套"""
        # 创建叶子节点
        leaf_agent = MockAnalysisAgent("leaf-3", "sentiment")

        # 创建三层嵌套容器
        container_l1 = NodeContainer(
            node_id="container-l1-deep",
            agent_card=AgentCard(
                agent_id="container-l1-deep",
                name="Deep Container L1",
                description="First layer",
                capabilities=[AgentCapability.MULTI_AGENT],
            ),
            child=leaf_agent,
        )

        container_l2 = NodeContainer(
            node_id="container-l2-deep",
            agent_card=AgentCard(
                agent_id="container-l2-deep",
                name="Deep Container L2",
                description="Second layer",
                capabilities=[AgentCapability.MULTI_AGENT],
            ),
            child=container_l1,
        )

        container_l3 = NodeContainer(
            node_id="container-l3-deep",
            agent_card=AgentCard(
                agent_id="container-l3-deep",
                name="Deep Container L3",
                description="Third layer",
                capabilities=[AgentCapability.MULTI_AGENT],
            ),
            child=container_l2,
        )

        # 创建任务
        task = Task(action="analyze", parameters={"text": "Deep nesting test"})

        # 执行任务（应该递归三层到达叶子节点）
        result = await container_l3.execute_task(task)

        # 验证结果
        assert result.status == TaskStatus.COMPLETED
        assert result.result["agent_id"] == "leaf-3"
        assert result.result["analysis_type"] == "sentiment"

    @pytest.mark.asyncio
    async def test_dynamic_child_setting(self):
        """测试动态设置子节点"""
        # 创建空容器
        container = NodeContainer(
            node_id="dynamic-container",
            agent_card=AgentCard(
                agent_id="dynamic-container",
                name="Dynamic Container",
                description="Container with dynamic child",
                capabilities=[AgentCapability.MULTI_AGENT],
            ),
        )

        # 动态设置子节点
        child_agent = MockAnalysisAgent("dynamic-child", "summary")
        container.set_child(child_agent)

        # 创建任务
        task = Task(action="analyze", parameters={"text": "Dynamic child test"})

        # 执行任务
        result = await container.execute_task(task)

        # 验证结果
        assert result.status == TaskStatus.COMPLETED
        assert result.result["agent_id"] == "dynamic-child"

    @pytest.mark.asyncio
    async def test_container_without_child(self):
        """测试没有子节点的容器"""
        # 创建没有子节点的容器
        container = NodeContainer(
            node_id="empty-container",
            agent_card=AgentCard(
                agent_id="empty-container",
                name="Empty Container",
                description="Container without child",
                capabilities=[AgentCapability.MULTI_AGENT],
            ),
        )

        # 创建任务
        task = Task(action="analyze", parameters={"text": "Empty container test"})

        # 执行任务
        result = await container.execute_task(task)

        # 验证错误处理
        assert result.error == "No child to execute task"
