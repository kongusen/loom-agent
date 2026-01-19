"""
Task - A2A协议任务模型

基于Google A2A协议的任务定义。
每次agent间的交互都是一个任务，有明确的开始和结束。

符合公理A2（事件主权公理）：所有通信都是事件驱动的。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"  # 待处理
    RUNNING = "running"  # 运行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class Task:
    """
    A2A任务模型

    属性：
        task_id: 任务唯一标识
        source_agent: 发起任务的代理ID
        target_agent: 目标代理ID
        action: 要执行的动作
        parameters: 任务参数
        status: 任务状态
        created_at: 创建时间
        updated_at: 更新时间
        result: 任务结果（Artifact）
        error: 错误信息（如果失败）
        metadata: 元数据（重要性、摘要、标签等）
        parent_task_id: 父任务ID（分形架构）
    """

    task_id: str = field(default_factory=lambda: str(uuid4()))
    source_agent: str = ""
    target_agent: str = ""
    action: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_task_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为A2A协议JSON格式"""
        return {
            "taskId": self.task_id,
            "sourceAgent": self.source_agent,
            "targetAgent": self.target_agent,
            "action": self.action,
            "parameters": self.parameters,
            "status": self.status.value,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "parentTaskId": self.parent_task_id,
        }
