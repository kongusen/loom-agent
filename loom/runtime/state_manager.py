"""
State Manager - 状态管理器

提供统一的状态管理接口。

设计原则：
1. 统一接口 - 统一的状态访问方式
2. 类型安全 - 使用类型化的状态模型
3. 可扩展 - 支持多种状态类型
"""

from loom.protocol.task import Task
from loom.runtime.state import AgentState
from loom.runtime.state_store import MemoryStateStore, StateStore


class StateManager:
    """
    状态管理器

    功能：
    - Agent状态管理
    - Task状态管理
    - 统一的状态存储接口
    """

    def __init__(self, store: StateStore | None = None):
        """
        初始化状态管理器

        Args:
            store: 状态存储（默认使用内存存储）
        """
        self.store = store or MemoryStateStore()

    # ==================== Agent状态管理 ====================

    async def save_agent_state(self, state: AgentState) -> None:
        """
        保存Agent状态

        Args:
            state: Agent状态对象
        """
        key = f"agent:{state.agent_id}"
        await self.store.save(key, state.to_dict())

    async def get_agent_state(self, agent_id: str) -> AgentState | None:
        """
        获取Agent状态

        Args:
            agent_id: Agent ID

        Returns:
            Agent状态对象，如果不存在返回None
        """
        key = f"agent:{agent_id}"
        data = await self.store.get(key)
        if data is None:
            return None
        return AgentState.from_dict(data)

    async def delete_agent_state(self, agent_id: str) -> None:
        """
        删除Agent状态

        Args:
            agent_id: Agent ID
        """
        key = f"agent:{agent_id}"
        await self.store.delete(key)

    async def list_agents(self) -> list[str]:
        """
        列出所有Agent ID

        Returns:
            Agent ID列表
        """
        keys = await self.store.list_keys("agent:")
        return [k.replace("agent:", "") for k in keys]

    # ==================== Task状态管理 ====================

    async def save_task_state(self, task: Task) -> None:
        """
        保存Task状态

        Args:
            task: Task对象
        """
        key = f"task:{task.task_id}"
        await self.store.save(key, task.to_dict())

    async def get_task_state(self, task_id: str) -> Task | None:
        """
        获取Task状态

        Args:
            task_id: Task ID

        Returns:
            Task对象，如果不存在返回None
        """
        key = f"task:{task_id}"
        data = await self.store.get(key)
        if data is None:
            return None

        # 从字典重建Task对象
        from datetime import datetime

        from loom.protocol.task import TaskStatus

        return Task(
            taskId=data["taskId"],
            sourceAgent=data["sourceAgent"],
            targetAgent=data["targetAgent"],
            action=data["action"],
            parameters=data["parameters"],
            status=TaskStatus(data["status"]),
            createdAt=datetime.fromisoformat(data["createdAt"]),
            updatedAt=datetime.fromisoformat(data["updatedAt"]),
            result=data.get("result"),
            error=data.get("error"),
        )

    async def delete_task_state(self, task_id: str) -> None:
        """
        删除Task状态

        Args:
            task_id: Task ID
        """
        key = f"task:{task_id}"
        await self.store.delete(key)

    async def list_tasks(self) -> list[str]:
        """
        列出所有Task ID

        Returns:
            Task ID列表
        """
        keys = await self.store.list_keys("task:")
        return [k.replace("task:", "") for k in keys]

    # ==================== 工具方法 ====================

    async def clear_all(self) -> None:
        """清空所有状态"""
        await self.store.clear()
