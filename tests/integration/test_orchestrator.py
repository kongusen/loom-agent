"""
Orchestrator Integration Tests

测试编排器的协调执行能力，验证A5公理（认知调度公理）。
"""

import pytest

from loom.orchestration.crew import CrewOrchestrator
from loom.protocol import Task, TaskStatus
from tests.integration.mock_agents import MockAnalysisAgent


class TestCrewOrchestrator:
    """Crew编排器测试"""

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """测试并行执行多个节点"""
        # 创建3个分析节点
        summary_agent = MockAnalysisAgent("summary-agent", "summary")
        keyword_agent = MockAnalysisAgent("keyword-agent", "keyword")
        sentiment_agent = MockAnalysisAgent("sentiment-agent", "sentiment")

        # 创建编排器
        orchestrator = CrewOrchestrator(nodes=[summary_agent, keyword_agent, sentiment_agent])

        # 创建任务
        task = Task(action="analyze", parameters={"text": "Test document for parallel analysis"})

        # 执行编排
        result = await orchestrator.orchestrate(task)

        # 验证结果
        assert result.status == TaskStatus.COMPLETED
        assert result.result is not None
        assert "results" in result.result
        assert "errors" in result.result
        assert len(result.result["results"]) == 3
        assert len(result.result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_result_aggregation(self):
        """测试结果聚合"""
        # 创建2个分析节点
        agent1 = MockAnalysisAgent("agent-1", "summary")
        agent2 = MockAnalysisAgent("agent-2", "keyword")

        # 创建编排器
        orchestrator = CrewOrchestrator(nodes=[agent1, agent2])

        # 创建任务
        task = Task(action="analyze", parameters={"text": "Aggregation test document"})

        # 执行编排
        result = await orchestrator.orchestrate(task)

        # 验证聚合结果
        assert result.status == TaskStatus.COMPLETED
        assert "results" in result.result
        assert "errors" in result.result
        assert len(result.result["results"]) == 2
        assert len(result.result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_empty_nodes(self):
        """测试空节点列表"""
        # 创建没有节点的编排器
        orchestrator = CrewOrchestrator(nodes=[])

        # 创建任务
        task = Task(action="analyze", parameters={"text": "Empty nodes test"})

        # 执行编排
        result = await orchestrator.orchestrate(task)

        # 验证错误处理
        assert result.status == TaskStatus.FAILED
        assert result.error == "No nodes available"

    @pytest.mark.asyncio
    async def test_dynamic_node_management(self):
        """测试动态添加和移除节点"""
        # 创建初始节点
        agent1 = MockAnalysisAgent("dynamic-1", "summary")

        # 创建编排器
        orchestrator = CrewOrchestrator(nodes=[agent1])

        # 动态添加节点
        agent2 = MockAnalysisAgent("dynamic-2", "keyword")
        orchestrator.add_node(agent2)

        # 验证节点数量
        assert len(orchestrator.nodes) == 2

        # 创建任务
        task = Task(action="analyze", parameters={"text": "Dynamic management test"})

        # 执行编排
        result = await orchestrator.orchestrate(task)

        # 验证两个节点都执行了
        assert result.status == TaskStatus.COMPLETED
        assert len(result.result["results"]) == 2

        # 移除一个节点
        removed = orchestrator.remove_node("dynamic-1")
        assert removed is True
        assert len(orchestrator.nodes) == 1

        # 再次执行
        task2 = Task(action="analyze", parameters={"text": "After removal test"})
        result2 = await orchestrator.orchestrate(task2)

        # 验证只有一个节点执行了
        assert result2.status == TaskStatus.COMPLETED
        assert len(result2.result["results"]) == 1
        assert result2.result["results"][0]["agent_id"] == "dynamic-2"
