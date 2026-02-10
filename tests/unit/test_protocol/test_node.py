"""
Tests for NodeProtocol
"""

import pytest

from loom.agent.card import AgentCapability, AgentCard, NodeProtocol
from loom.runtime.task import Task, TaskStatus


class MockNode(NodeProtocol):
    """Mock implementation of NodeProtocol for testing"""

    def __init__(self):
        self.node_id = "test_node"
        self.source_uri = "node://test_node"
        self.agent_card = AgentCard(
            agent_id="test_node",
            name="Test Node",
            description="A test node",
            capabilities=[AgentCapability.TOOL_USE],
        )

    async def execute_task(self, task: Task) -> Task:
        task.status = TaskStatus.COMPLETED
        task.result = {"done": True}
        return task

    def get_capabilities(self) -> AgentCard:
        return self.agent_card


class TestNodeProtocol:
    """Test suite for NodeProtocol"""

    def test_node_protocol_attributes(self):
        """Test NodeProtocol attributes"""
        node = MockNode()

        assert node.node_id == "test_node"
        assert node.source_uri == "node://test_node"
        assert node.agent_card.agent_id == "test_node"

    @pytest.mark.asyncio
    async def test_execute_task(self):
        """Test execute_task method"""
        node = MockNode()
        task = Task(task_id="test_task", action="test_action")

        result = await node.execute_task(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"done": True}
        assert result.task_id == "test_task"

    @pytest.mark.asyncio
    async def test_execute_task_preserves_task_id(self):
        """Test execute_task preserves task properties"""
        node = MockNode()
        task = Task(
            task_id="my_task",
            action="my_action",
            parameters={"key": "value"},
            source_agent="agent1",
            target_agent="agent2",
        )

        result = await node.execute_task(task)

        assert result.task_id == "my_task"
        assert result.action == "my_action"
        assert result.parameters == {"key": "value"}

    def test_get_capabilities(self):
        """Test get_capabilities method"""
        node = MockNode()
        card = node.get_capabilities()

        assert card.agent_id == "test_node"
        assert card.name == "Test Node"
        assert len(card.capabilities) == 1
        assert AgentCapability.TOOL_USE in card.capabilities

    def test_get_capabilities_returns_same_card(self):
        """Test get_capabilities returns the same AgentCard"""
        node = MockNode()
        card1 = node.get_capabilities()
        card2 = node.get_capabilities()

        assert card1 is card2

    def test_node_protocol_with_multiple_capabilities(self):
        """Test NodeProtocol with multiple capabilities"""

        class MultiCapabilityNode(NodeProtocol):
            def __init__(self):
                self.node_id = "multi_node"
                self.source_uri = "node://multi_node"
                self.agent_card = AgentCard(
                    agent_id="multi_node",
                    name="Multi Capability Node",
                    description="Node with multiple capabilities",
                    capabilities=[
                        AgentCapability.REFLECTION,
                        AgentCapability.TOOL_USE,
                        AgentCapability.PLANNING,
                        AgentCapability.MULTI_AGENT,
                    ],
                )

            async def execute_task(self, task: Task) -> Task:
                return task

            def get_capabilities(self) -> AgentCard:
                return self.agent_card

        node = MultiCapabilityNode()
        card = node.get_capabilities()

        assert len(card.capabilities) == 4
        assert AgentCapability.REFLECTION in card.capabilities
        assert AgentCapability.TOOL_USE in card.capabilities
        assert AgentCapability.PLANNING in card.capabilities
        assert AgentCapability.MULTI_AGENT in card.capabilities

    @pytest.mark.asyncio
    async def test_execute_task_with_error(self):
        """Test execute_task that returns failed task"""

        class ErrorNode(NodeProtocol):
            def __init__(self):
                self.node_id = "error_node"
                self.source_uri = "node://error_node"
                self.agent_card = AgentCard(
                    agent_id="error_node",
                    name="Error Node",
                    description="Node that returns errors",
                )

            async def execute_task(self, task: Task) -> Task:
                task.status = TaskStatus.FAILED
                task.error = "Task failed"
                return task

            def get_capabilities(self) -> AgentCard:
                return self.agent_card

        node = ErrorNode()
        task = Task(task_id="test_task", action="test_action")

        result = await node.execute_task(task)

        assert result.status == TaskStatus.FAILED
        assert result.error == "Task failed"
