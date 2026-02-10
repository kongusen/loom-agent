"""
事件处理器协议定义

提供类型安全的处理器协议，确保处理器签名正确。
"""

from typing import Any, Protocol

from loom.runtime import Task


class TaskHandler(Protocol):
    """任务处理器协议"""

    async def __call__(self, task: Task) -> Task:
        """
        处理任务

        Args:
            task: 输入任务

        Returns:
            处理后的任务
        """
        ...


class MemoryHandler(Protocol):
    """记忆处理器协议"""

    async def __call__(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        处理记忆操作

        Args:
            data: 记忆数据

        Returns:
            处理结果
        """
        ...


class AgentHandler(Protocol):
    """Agent处理器协议"""

    async def __call__(self, agent_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        处理Agent操作

        Args:
            agent_id: Agent ID
            data: 操作数据

        Returns:
            处理结果
        """
        ...
