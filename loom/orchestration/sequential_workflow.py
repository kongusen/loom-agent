"""
Sequential Workflow - 固定流程工作流

预定义的步骤序列，按顺序执行。
"""

from collections.abc import Callable

from loom.protocol import Task, TaskStatus

from .workflow import Workflow


class SequentialWorkflow(Workflow):
    """
    固定流程工作流

    按预定义的步骤顺序执行。
    """

    def __init__(
        self,
        workflow_id: str,
        steps: list[Callable],
        description: str = "",
    ):
        """
        初始化固定流程工作流

        Args:
            workflow_id: 工作流ID
            steps: 步骤函数列表
            description: 工作流描述
        """
        super().__init__(workflow_id)
        self.steps = steps
        self.description = description

    async def execute(self, task: Task) -> Task:
        """执行工作流"""
        results = []

        for i, step in enumerate(self.steps):
            try:
                # 执行步骤
                result = await step(task, results)
                results.append(result)

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = f"Step {i+1} failed: {str(e)}"
                return task

        # 所有步骤完成
        task.status = TaskStatus.COMPLETED
        task.result = {"steps_results": results}
        return task

    def get_description(self) -> str:
        """获取描述"""
        return self.description or f"Sequential workflow with {len(self.steps)} steps"
