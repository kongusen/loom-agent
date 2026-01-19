"""
Tests for Orchestrator Base Class
"""

from unittest.mock import Mock

import pytest

from loom.orchestration.base import Orchestrator
from loom.protocol import Task, TaskStatus


class TestOrchestratorBase:
    """Test suite for Orchestrator base class"""

    def test_orchestrator_is_abstract(self):
        """Test Orchestrator cannot be instantiated directly"""
        with pytest.raises(TypeError):
            Orchestrator()

    def test_orchestrator_init_without_nodes(self):
        """Test initialization without nodes"""

        class ConcreteOrchestrator(Orchestrator):
            async def orchestrate(self, task: Task) -> Task:
                return task

        orchestrator = ConcreteOrchestrator()

        assert orchestrator.nodes == []

    def test_orchestrator_init_with_nodes(self):
        """Test initialization with nodes"""

        class ConcreteOrchestrator(Orchestrator):
            async def orchestrate(self, task: Task) -> Task:
                return task

        mock_node1 = Mock()
        mock_node1.node_id = "node1"
        mock_node2 = Mock()
        mock_node2.node_id = "node2"

        orchestrator = ConcreteOrchestrator([mock_node1, mock_node2])

        assert len(orchestrator.nodes) == 2
        assert orchestrator.nodes[0].node_id == "node1"
        assert orchestrator.nodes[1].node_id == "node2"

    def test_orchestrator_init_with_empty_list(self):
        """Test initialization with empty node list"""

        class ConcreteOrchestrator(Orchestrator):
            async def orchestrate(self, task: Task) -> Task:
                return task

        orchestrator = ConcreteOrchestrator([])

        assert orchestrator.nodes == []

    def test_orchestrator_add_node(self):
        """Test adding a node"""

        class ConcreteOrchestrator(Orchestrator):
            async def orchestrate(self, task: Task) -> Task:
                return task

        orchestrator = ConcreteOrchestrator()
        mock_node = Mock()
        mock_node.node_id = "test_node"

        orchestrator.add_node(mock_node)

        assert len(orchestrator.nodes) == 1
        assert orchestrator.nodes[0] is mock_node

    def test_orchestrator_add_multiple_nodes(self):
        """Test adding multiple nodes"""

        class ConcreteOrchestrator(Orchestrator):
            async def orchestrate(self, task: Task) -> Task:
                return task

        orchestrator = ConcreteOrchestrator()

        for i in range(3):
            mock_node = Mock()
            mock_node.node_id = f"node{i}"
            orchestrator.add_node(mock_node)

        assert len(orchestrator.nodes) == 3
        assert orchestrator.nodes[0].node_id == "node0"
        assert orchestrator.nodes[1].node_id == "node1"
        assert orchestrator.nodes[2].node_id == "node2"

    def test_orchestrator_remove_node_success(self):
        """Test removing an existing node"""

        class ConcreteOrchestrator(Orchestrator):
            async def orchestrate(self, task: Task) -> Task:
                return task

        mock_node = Mock()
        mock_node.node_id = "test_node"

        orchestrator = ConcreteOrchestrator([mock_node])
        result = orchestrator.remove_node("test_node")

        assert result is True
        assert len(orchestrator.nodes) == 0

    def test_orchestrator_remove_node_not_found(self):
        """Test removing a non-existent node"""

        class ConcreteOrchestrator(Orchestrator):
            async def orchestrate(self, task: Task) -> Task:
                return task

        mock_node = Mock()
        mock_node.node_id = "other_node"

        orchestrator = ConcreteOrchestrator([mock_node])
        result = orchestrator.remove_node("nonexistent")

        assert result is False
        assert len(orchestrator.nodes) == 1

    def test_orchestrator_remove_node_from_multiple(self):
        """Test removing a node from multiple nodes"""

        class ConcreteOrchestrator(Orchestrator):
            async def orchestrate(self, task: Task) -> Task:
                return task

        nodes = []
        for i in range(3):
            mock_node = Mock()
            mock_node.node_id = f"node{i}"
            nodes.append(mock_node)

        orchestrator = ConcreteOrchestrator(nodes)
        result = orchestrator.remove_node("node1")

        assert result is True
        assert len(orchestrator.nodes) == 2
        assert orchestrator.nodes[0].node_id == "node0"
        assert orchestrator.nodes[1].node_id == "node2"

    def test_orchestrator_remove_node_preserves_order(self):
        """Test that removing a node preserves order"""

        class ConcreteOrchestrator(Orchestrator):
            async def orchestrate(self, task: Task) -> Task:
                return task

        nodes = []
        for i in range(5):
            mock_node = Mock()
            mock_node.node_id = f"node{i}"
            nodes.append(mock_node)

        orchestrator = ConcreteOrchestrator(nodes)

        # Remove middle node
        orchestrator.remove_node("node2")

        assert len(orchestrator.nodes) == 4
        assert [n.node_id for n in orchestrator.nodes] == ["node0", "node1", "node3", "node4"]

    @pytest.mark.asyncio
    async def test_orchestrator_orchestrate_implementation(self):
        """Test orchestrate method implementation"""

        class ConcreteOrchestrator(Orchestrator):
            async def orchestrate(self, task: Task) -> Task:
                task.status = TaskStatus.COMPLETED
                return task

        orchestrator = ConcreteOrchestrator()
        task = Task(task_id="test", action="test_action")

        result = await orchestrator.orchestrate(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.task_id == "test"
