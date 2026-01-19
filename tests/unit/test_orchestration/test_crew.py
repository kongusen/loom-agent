"""
CrewOrchestrator Tests

测试团队编排器功能，目标覆盖率 90%+
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.orchestration.crew import CrewOrchestrator
from loom.protocol import Task, TaskStatus


class TestCrewOrchestratorInit:
    """测试 CrewOrchestrator 初始化"""

    def test_init_without_nodes(self):
        """测试无节点初始化"""
        orchestrator = CrewOrchestrator()

        assert orchestrator.nodes == []

    def test_init_with_nodes(self):
        """测试带节点初始化"""
        mock_node1 = Mock()
        mock_node1.node_id = "node1"
        mock_node2 = Mock()
        mock_node2.node_id = "node2"

        orchestrator = CrewOrchestrator(nodes=[mock_node1, mock_node2])

        assert len(orchestrator.nodes) == 2
        assert orchestrator.nodes[0].node_id == "node1"
        assert orchestrator.nodes[1].node_id == "node2"


class TestCrewOrchestratorNodeManagement:
    """测试节点管理功能"""

    def test_add_node(self):
        """测试添加节点"""
        orchestrator = CrewOrchestrator()
        mock_node = Mock()
        mock_node.node_id = "test_node"

        orchestrator.add_node(mock_node)

        assert len(orchestrator.nodes) == 1
        assert orchestrator.nodes[0].node_id == "test_node"

    def test_add_multiple_nodes(self):
        """测试添加多个节点"""
        orchestrator = CrewOrchestrator()

        for i in range(3):
            mock_node = Mock()
            mock_node.node_id = f"node{i}"
            orchestrator.add_node(mock_node)

        assert len(orchestrator.nodes) == 3

    def test_remove_node_success(self):
        """测试成功移除节点"""
        mock_node = Mock()
        mock_node.node_id = "test_node"
        orchestrator = CrewOrchestrator(nodes=[mock_node])

        result = orchestrator.remove_node("test_node")

        assert result is True
        assert len(orchestrator.nodes) == 0

    def test_remove_node_not_found(self):
        """测试移除不存在的节点"""
        orchestrator = CrewOrchestrator()

        result = orchestrator.remove_node("nonexistent")

        assert result is False

    def test_remove_node_from_multiple(self):
        """测试从多个节点中移除一个"""
        nodes = []
        for i in range(3):
            mock_node = Mock()
            mock_node.node_id = f"node{i}"
            nodes.append(mock_node)

        orchestrator = CrewOrchestrator(nodes=nodes)

        result = orchestrator.remove_node("node1")

        assert result is True
        assert len(orchestrator.nodes) == 2
        assert orchestrator.nodes[0].node_id == "node0"
        assert orchestrator.nodes[1].node_id == "node2"


class TestCrewOrchestratorOrchestrate:
    """测试编排执行功能"""

    @pytest.mark.asyncio
    async def test_orchestrate_no_nodes(self):
        """测试无节点时的编排"""
        orchestrator = CrewOrchestrator()
        task = Task(task_id="task1", action="test task")

        result = await orchestrator.orchestrate(task)

        assert result.status == TaskStatus.FAILED
        assert result.error == "No nodes available"

    @pytest.mark.asyncio
    async def test_orchestrate_single_node_success(self):
        """测试单节点成功执行"""
        # 创建 mock 节点
        mock_node = Mock()
        mock_node.node_id = "node1"

        # 创建成功的任务结果
        success_task = Task(
            task_id="task1", action="test", status=TaskStatus.COMPLETED, result="success"
        )
        mock_node.execute_task = AsyncMock(return_value=success_task)

        orchestrator = CrewOrchestrator(nodes=[mock_node])
        task = Task(task_id="task1", action="test task")

        result = await orchestrator.orchestrate(task)

        assert result.status == TaskStatus.COMPLETED
        assert result.result is not None
        assert "results" in result.result
        assert len(result.result["results"]) == 1
        assert result.result["results"][0] == "success"

    @pytest.mark.asyncio
    async def test_orchestrate_multiple_nodes_success(self):
        """测试多节点并行成功执行"""
        # 创建多个 mock 节点
        nodes = []
        for i in range(3):
            mock_node = Mock()
            mock_node.node_id = f"node{i}"
            success_task = Task(
                task_id=f"task{i}", action="test", status=TaskStatus.COMPLETED, result=f"result{i}"
            )
            mock_node.execute_task = AsyncMock(return_value=success_task)
            nodes.append(mock_node)

        orchestrator = CrewOrchestrator(nodes=nodes)
        task = Task(task_id="task1", action="test task")

        result = await orchestrator.orchestrate(task)

        assert result.status == TaskStatus.COMPLETED
        assert len(result.result["results"]) == 3
        assert "result0" in result.result["results"]
        assert "result1" in result.result["results"]
        assert "result2" in result.result["results"]

    @pytest.mark.asyncio
    async def test_orchestrate_node_raises_exception(self):
        """测试节点执行抛出异常"""
        # 创建会抛出异常的 mock 节点
        mock_node = Mock()
        mock_node.node_id = "node1"
        mock_node.execute_task = AsyncMock(side_effect=ValueError("Node error"))

        orchestrator = CrewOrchestrator(nodes=[mock_node])
        task = Task(task_id="task1", action="test task")

        result = await orchestrator.orchestrate(task)

        assert result.status == TaskStatus.COMPLETED
        assert "errors" in result.result
        assert len(result.result["errors"]) == 1
        assert "Node error" in result.result["errors"][0]

    @pytest.mark.asyncio
    async def test_orchestrate_mixed_success_and_failure(self):
        """测试混合成功和失败的场景"""
        # 创建成功的节点
        success_node = Mock()
        success_node.node_id = "success_node"
        success_task = Task(
            task_id="task1", action="test", status=TaskStatus.COMPLETED, result="success"
        )
        success_node.execute_task = AsyncMock(return_value=success_task)

        # 创建失败的节点
        failure_node = Mock()
        failure_node.node_id = "failure_node"
        failure_node.execute_task = AsyncMock(side_effect=RuntimeError("Failed"))

        orchestrator = CrewOrchestrator(nodes=[success_node, failure_node])
        task = Task(task_id="task1", action="test task")

        result = await orchestrator.orchestrate(task)

        assert result.status == TaskStatus.COMPLETED
        assert len(result.result["results"]) == 1
        assert result.result["results"][0] == "success"
        assert len(result.result["errors"]) == 1
        assert "Failed" in result.result["errors"][0]


class TestCrewOrchestratorAggregateResults:
    """测试结果聚合功能"""

    def test_aggregate_empty_results(self):
        """测试聚合空结果"""
        orchestrator = CrewOrchestrator()

        result = orchestrator._aggregate_results([])

        assert result["results"] == []
        assert result["errors"] == []

    def test_aggregate_only_tasks(self):
        """测试只聚合任务结果"""
        orchestrator = CrewOrchestrator()

        task1 = Task(task_id="task1", action="test", result="result1")
        task2 = Task(task_id="task2", action="test", result="result2")

        result = orchestrator._aggregate_results([task1, task2])

        assert len(result["results"]) == 2
        assert "result1" in result["results"]
        assert "result2" in result["results"]
        assert len(result["errors"]) == 0

    def test_aggregate_only_exceptions(self):
        """测试只聚合异常"""
        orchestrator = CrewOrchestrator()

        exc1 = ValueError("Error 1")
        exc2 = RuntimeError("Error 2")

        result = orchestrator._aggregate_results([exc1, exc2])

        assert len(result["results"]) == 0
        assert len(result["errors"]) == 2
        assert "Error 1" in result["errors"]
        assert "Error 2" in result["errors"]

    def test_aggregate_mixed_tasks_and_exceptions(self):
        """测试聚合混合的任务和异常"""
        orchestrator = CrewOrchestrator()

        task1 = Task(task_id="task1", action="test", result="success")
        exc1 = ValueError("Error occurred")
        task2 = Task(task_id="task2", action="test", result="another success")

        result = orchestrator._aggregate_results([task1, exc1, task2])

        assert len(result["results"]) == 2
        assert "success" in result["results"]
        assert "another success" in result["results"]
        assert len(result["errors"]) == 1
        assert "Error occurred" in result["errors"]

    def test_aggregate_with_none_results(self):
        """测试聚合包含 None 的结果"""
        orchestrator = CrewOrchestrator()

        task1 = Task(task_id="task1", action="test", result=None)
        task2 = Task(task_id="task2", action="test", result="result")

        result = orchestrator._aggregate_results([task1, task2])

        assert len(result["results"]) == 2
        assert None in result["results"]
        assert "result" in result["results"]

    @pytest.mark.asyncio
    async def test_orchestrate_aggregate_raises_exception(self):
        """测试聚合结果时抛出异常"""
        from unittest.mock import patch

        # 创建 mock 节点
        mock_node = Mock()
        mock_node.node_id = "node1"
        success_task = Task(
            task_id="task1", action="test", status=TaskStatus.COMPLETED, result="success"
        )
        mock_node.execute_task = AsyncMock(return_value=success_task)

        orchestrator = CrewOrchestrator(nodes=[mock_node])
        task = Task(task_id="task1", action="test task")

        # Mock _aggregate_results 使其抛出异常
        with patch.object(
            orchestrator, "_aggregate_results", side_effect=RuntimeError("Aggregation failed")
        ):
            result = await orchestrator.orchestrate(task)

        assert result.status == TaskStatus.FAILED
        assert "Aggregation failed" in result.error
