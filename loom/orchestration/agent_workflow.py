"""
Agent Workflow - 动态流程工作流

由Agent自主决策流程，可以委派给其他Agents。
"""

from loom.agent import Agent
from loom.protocol import Task

from .workflow import Workflow


class AgentWorkflow(Workflow):
    """
    动态流程工作流

    由一个主Agent控制，可以委派给其他Agents。
    """

    def __init__(
        self,
        workflow_id: str,
        coordinator_agent: Agent,
        description: str = "",
    ):
        """
        初始化动态流程工作流

        Args:
            workflow_id: 工作流ID
            coordinator_agent: 协调Agent（负责决策和委派）
            description: 工作流描述
        """
        super().__init__(workflow_id)
        self.coordinator = coordinator_agent
        self.description = description

    async def execute(self, task: Task) -> Task:
        """
        执行工作流

        由coordinator_agent自主决策流程。
        """
        # 直接委派给coordinator agent执行
        result = await self.coordinator.execute_task(task)
        return result

    def get_description(self) -> str:
        """获取描述"""
        return (
            self.description or f"Agent-driven workflow coordinated by {self.coordinator.node_id}"
        )
