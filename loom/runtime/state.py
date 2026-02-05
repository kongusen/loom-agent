"""
State - 状态类型定义

定义系统中的各种状态类型。

设计原则：
1. 简单明确 - 状态定义清晰
2. 类型安全 - 使用枚举和数据类
3. 可扩展 - 支持元数据扩展
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class AgentStatus(StrEnum):
    """
    Agent运行状态

    状态说明：
    - IDLE: 空闲，等待任务
    - BUSY: 忙碌，正在执行任务
    - ERROR: 错误，需要人工介入
    - OFFLINE: 离线，不可用
    """

    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentState:
    """
    Agent状态模型

    属性：
        agent_id: Agent唯一标识
        status: Agent运行状态
        current_task: 当前执行的任务ID（如果有）
        metadata: 额外元数据
        updated_at: 最后更新时间
    """

    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "current_task": self.current_task,
            "metadata": self.metadata,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentState":
        """从字典创建AgentState"""
        return cls(
            agent_id=data["agent_id"],
            status=AgentStatus(data["status"]),
            current_task=data.get("current_task"),
            metadata=data.get("metadata", {}),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
