"""
Task - A2A协议任务模型

基于Google A2A协议的任务定义。
每次agent间的交互都是一个任务，有明确的开始和结束。

符合公理A2（事件主权公理）：所有通信都是事件驱动的。

v0.5.0: 迁移为 Pydantic BaseModel，使用驼峰命名（与 A2A 协议一致）
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"  # 待处理
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class Task(BaseModel):
    """
    A2A任务模型 - 使用驼峰命名（与 A2A 协议一致）

    属性：
        taskId: 任务唯一标识
        sourceAgent: 发起任务的代理ID
        targetAgent: 目标代理ID
        action: 要执行的动作
        parameters: 任务参数
        status: 任务状态
        createdAt: 创建时间
        updatedAt: 更新时间
        result: 任务结果（Artifact）
        error: 错误信息（如果失败）
        metadata: 元数据（重要性、摘要、标签等）
        parentTaskId: 父任务ID（分形架构）
        sessionId: 会话ID（由上层定义）
    """

    taskId: str = Field(default_factory=lambda: str(uuid4()), alias="task_id")
    sourceAgent: str = Field(default="", alias="source_agent")
    targetAgent: str = Field(default="", alias="target_agent")
    action: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    createdAt: datetime = Field(default_factory=datetime.now, alias="created_at")
    updatedAt: datetime = Field(default_factory=datetime.now, alias="updated_at")
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    parentTaskId: str | None = Field(default=None, alias="parent_task_id")
    sessionId: str | None = Field(default=None, alias="session_id")

    model_config = {"extra": "allow", "populate_by_name": True}

    # 蛇形命名别名（向后兼容）
    @property
    def task_id(self) -> str:
        """task_id 别名，访问 taskId"""
        return self.taskId

    @task_id.setter
    def task_id(self, value: str):
        """task_id setter，设置 taskId"""
        self.taskId = value

    @property
    def source_agent(self) -> str:
        """source_agent 别名，访问 sourceAgent"""
        return self.sourceAgent

    @source_agent.setter
    def source_agent(self, value: str):
        """source_agent setter，设置 sourceAgent"""
        self.sourceAgent = value

    @property
    def target_agent(self) -> str:
        """target_agent 别名，访问 targetAgent"""
        return self.targetAgent

    @target_agent.setter
    def target_agent(self, value: str):
        """target_agent setter，设置 targetAgent"""
        self.targetAgent = value

    @property
    def created_at(self) -> datetime:
        """created_at 别名，访问 createdAt"""
        return self.createdAt

    @created_at.setter
    def created_at(self, value: datetime):
        """created_at setter，设置 createdAt"""
        self.createdAt = value

    @property
    def updated_at(self) -> datetime:
        """updated_at 别名，访问 updatedAt"""
        return self.updatedAt

    @updated_at.setter
    def updated_at(self, value: datetime):
        """updated_at setter，设置 updatedAt"""
        self.updatedAt = value

    @property
    def parent_task_id(self) -> str | None:
        """parent_task_id 别名，访问 parentTaskId"""
        return self.parentTaskId

    @parent_task_id.setter
    def parent_task_id(self, value: str | None):
        """parent_task_id setter，设置 parentTaskId"""
        self.parentTaskId = value

    @property
    def session_id(self) -> str | None:
        """session_id 别名，访问 sessionId"""
        return self.sessionId

    @session_id.setter
    def session_id(self, value: str | None):
        """session_id setter，设置 sessionId"""
        self.sessionId = value

    def to_dict(self) -> dict[str, Any]:
        """转换为 A2A 协议 JSON 格式（直接导出）"""
        data = self.model_dump()
        # 仅处理特殊类型
        data["status"] = self.status.value
        data["createdAt"] = self.createdAt.isoformat()
        data["updatedAt"] = self.updatedAt.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """
        从字典反序列化并校验（兼容蛇形输入）

        支持两种输入格式：
        1. 驼峰格式（A2A JSON）: {"taskId": "...", "sourceAgent": "..."}
        2. 蛇形格式（Python）: {"task_id": "...", "source_agent": "..."}

        Args:
            data: 输入字典（驼峰或蛇形）

        Returns:
            Task: 校验后的 Task 实例

        Raises:
            ValidationError: 如果数据不符合 Task schema
        """
        # 键映射：蛇形 -> 驼峰
        snake_to_camel = {
            "task_id": "taskId",
            "source_agent": "sourceAgent",
            "target_agent": "targetAgent",
            "created_at": "createdAt",
            "updated_at": "updatedAt",
            "parent_task_id": "parentTaskId",
            "session_id": "sessionId",
        }

        # 如果输入是蛇形，转换为驼峰
        normalized = {}
        for key, value in data.items():
            camel_key = snake_to_camel.get(key, key)
            normalized[camel_key] = value

        return cls.model_validate(normalized)
