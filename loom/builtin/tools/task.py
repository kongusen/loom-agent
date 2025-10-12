"""Task 工具 - 启动 SubAgent 执行子任务"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool

if TYPE_CHECKING:
    from loom.components.agent import Agent


class TaskInput(BaseModel):
    """Task 工具输入参数"""

    description: str = Field(description="Short description of the task (3-5 words)")
    prompt: str = Field(description="Detailed task instructions for the sub-agent")


class TaskTool(BaseTool):
    """
    Task 工具 - 启动 SubAgent 执行专项任务

    对应 Claude Code 的 Task 工具和 SubAgent 机制
    """

    name = "task"
    description = (
        "Launch a sub-agent to handle a specific subtask independently. "
        "Useful for parallel execution or specialized processing. "
        "The sub-agent has its own execution environment and tool access."
    )
    args_schema = TaskInput
    is_concurrency_safe = True

    def __init__(
        self,
        agent_factory: Optional[callable] = None,
        max_iterations: int = 20,
    ) -> None:
        """
        Parameters:
        - agent_factory: 创建 SubAgent 的工厂函数
        - max_iterations: SubAgent 最大迭代次数
        """
        self.agent_factory = agent_factory
        self.max_iterations = max_iterations

    async def run(
        self,
        description: str,
        prompt: str,
        **kwargs: Any,
    ) -> str:
        """执行子任务"""
        if not self.agent_factory:
            return "Error: Task tool not configured with agent_factory"

        try:
            # 创建 SubAgent 实例
            sub_agent: Agent = self.agent_factory(max_iterations=self.max_iterations)

            # 运行子任务
            result = await sub_agent.run(prompt)

            # 格式化返回结果
            return f"**SubAgent Task: {description}**\n\nResult:\n{result}"

        except Exception as e:
            return f"SubAgent execution error: {type(e).__name__}: {str(e)}"
