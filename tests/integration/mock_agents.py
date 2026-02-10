"""
Mock Agents for Fractal Testing

提供测试用的Mock Agent实现，用于验证分形、递归、编排等机制。
"""

from loom.agent.card import AgentCapability, AgentCard
from loom.runtime import Task, TaskStatus


class MockAnalysisAgent:
    """
    Mock分析Agent

    模拟文档分析功能，用于测试。
    """

    def __init__(self, node_id: str, analysis_type: str = "general"):
        """
        初始化Mock分析Agent

        Args:
            node_id: 节点ID
            analysis_type: 分析类型（summary, keyword, sentiment等）
        """
        self.node_id = node_id
        self.source_uri = f"node://{node_id}"
        self.analysis_type = analysis_type
        self.agent_card = AgentCard(
            agent_id=node_id,
            name=f"{analysis_type.capitalize()} Analysis Agent",
            description=f"Mock agent for {analysis_type} analysis",
            capabilities=[AgentCapability.TOOL_USE],
        )

    async def execute_task(self, task: Task) -> Task:
        """
        执行分析任务

        Args:
            task: 任务对象

        Returns:
            更新后的任务
        """
        # 模拟分析处理
        input_text = task.parameters.get("text", "")

        if self.analysis_type == "summary":
            result = f"Summary of '{input_text[:50]}...': This is a mock summary."
        elif self.analysis_type == "keyword":
            result = f"Keywords: mock, test, analysis, {input_text[:20]}"
        elif self.analysis_type == "sentiment":
            result = "Sentiment: Neutral (mock result)"
        else:
            result = f"Analysis result for '{input_text[:30]}...'"

        task.result = {
            "agent_id": self.node_id,
            "analysis_type": self.analysis_type,
            "result": result,
        }
        task.status = TaskStatus.COMPLETED
        return task

    def get_capabilities(self) -> AgentCard:
        """获取能力声明"""
        return self.agent_card


class MockPlanningAgent:
    """
    Mock规划Agent

    模拟任务分解和规划功能。
    """

    def __init__(self, node_id: str):
        """
        初始化Mock规划Agent

        Args:
            node_id: 节点ID
        """
        self.node_id = node_id
        self.source_uri = f"node://{node_id}"
        self.agent_card = AgentCard(
            agent_id=node_id,
            name="Planning Agent",
            description="Mock agent for task planning and decomposition",
            capabilities=[AgentCapability.PLANNING],
        )

    async def execute_task(self, task: Task) -> Task:
        """
        执行规划任务

        将任务分解为子任务列表。

        Args:
            task: 任务对象

        Returns:
            更新后的任务
        """
        input_text = task.parameters.get("text", "")

        # 模拟任务分解
        subtasks = [
            {
                "type": "summary",
                "description": "Extract summary from document",
                "parameters": {"text": input_text},
            },
            {
                "type": "keyword",
                "description": "Extract keywords from document",
                "parameters": {"text": input_text},
            },
            {
                "type": "sentiment",
                "description": "Analyze sentiment of document",
                "parameters": {"text": input_text},
            },
        ]

        task.result = {"agent_id": self.node_id, "plan": subtasks, "subtask_count": len(subtasks)}
        task.status = TaskStatus.COMPLETED
        return task

    def get_capabilities(self) -> AgentCard:
        """获取能力声明"""
        return self.agent_card


class MockReflectionAgent:
    """
    Mock反思Agent

    模拟结果评估和质量检查功能。
    """

    def __init__(self, node_id: str, quality_threshold: float = 0.7):
        """
        初始化Mock反思Agent

        Args:
            node_id: 节点ID
            quality_threshold: 质量阈值
        """
        self.node_id = node_id
        self.source_uri = f"node://{node_id}"
        self.quality_threshold = quality_threshold
        self.agent_card = AgentCard(
            agent_id=node_id,
            name="Reflection Agent",
            description="Mock agent for result evaluation and quality check",
            capabilities=[AgentCapability.REFLECTION],
        )

    async def execute_task(self, task: Task) -> Task:
        """
        执行反思任务

        评估结果质量并提供改进建议。

        Args:
            task: 任务对象

        Returns:
            更新后的任务
        """
        results = task.parameters.get("results", [])

        # 模拟质量评估
        quality_score = 0.85  # Mock质量分数
        passed = quality_score >= self.quality_threshold

        evaluation = {
            "quality_score": quality_score,
            "passed": passed,
            "threshold": self.quality_threshold,
            "feedback": "Results meet quality standards."
            if passed
            else "Results need improvement.",
            "evaluated_count": len(results),
        }

        task.result = {"agent_id": self.node_id, "evaluation": evaluation}
        task.status = TaskStatus.COMPLETED
        return task

    def get_capabilities(self) -> AgentCard:
        """获取能力声明"""
        return self.agent_card
