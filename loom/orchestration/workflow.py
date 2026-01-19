"""
Workflow - 工作流编排抽象

Workflow是比Agent更高层次的抽象，用于编排多个Agent或定义固定流程。

两种类型：
1. 固定流程Workflow（SequentialWorkflow）- 预定义的步骤序列
2. 动态流程Workflow（AgentWorkflow）- 由Agent自主决策流程
"""

from abc import ABC, abstractmethod

from loom.protocol import Task


class Workflow(ABC):
    """
    Workflow抽象基类

    所有工作流都应该继承此类。
    """

    def __init__(self, workflow_id: str):
        """
        初始化Workflow

        Args:
            workflow_id: 工作流唯一标识
        """
        self.workflow_id = workflow_id

    @abstractmethod
    async def execute(self, task: Task) -> Task:
        """
        执行工作流

        Args:
            task: 输入任务

        Returns:
            完成后的任务
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        获取工作流描述

        Returns:
            工作流描述文本
        """
        pass
