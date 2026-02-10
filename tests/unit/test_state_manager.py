"""
状态管理测试

测试StateManager、StateStore和状态模型。
"""

from datetime import datetime

import pytest

from loom.runtime.task import Task, TaskStatus
from loom.runtime import (
    AgentState,
    AgentStatus,
    MemoryStateStore,
    StateManager,
)


class TestAgentState:
    """测试Agent状态模型"""

    def test_create_agent_state(self):
        """测试创建Agent状态"""
        state = AgentState(
            agent_id="agent-1",
            status=AgentStatus.IDLE,
        )

        assert state.agent_id == "agent-1"
        assert state.status == AgentStatus.IDLE
        assert state.current_task is None
        assert isinstance(state.metadata, dict)

    def test_agent_state_to_dict(self):
        """测试Agent状态序列化"""
        state = AgentState(
            agent_id="agent-1",
            status=AgentStatus.BUSY,
            current_task="task-1",
        )

        data = state.to_dict()

        assert data["agent_id"] == "agent-1"
        assert data["status"] == "busy"
        assert data["current_task"] == "task-1"

    def test_agent_state_from_dict(self):
        """测试Agent状态反序列化"""
        data = {
            "agent_id": "agent-1",
            "status": "idle",
            "current_task": None,
            "metadata": {},
            "updated_at": datetime.now().isoformat(),
        }

        state = AgentState.from_dict(data)

        assert state.agent_id == "agent-1"
        assert state.status == AgentStatus.IDLE


class TestMemoryStateStore:
    """测试内存状态存储"""

    @pytest.mark.asyncio
    async def test_save_and_get(self):
        """测试保存和获取状态"""
        store = MemoryStateStore()

        # 保存状态
        await store.save("key1", "value1")

        # 获取状态
        value = await store.get("key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """测试获取不存在的状态"""
        store = MemoryStateStore()

        value = await store.get("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_delete(self):
        """测试删除状态"""
        store = MemoryStateStore()

        await store.save("key1", "value1")
        await store.delete("key1")

        value = await store.get("key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_list_keys(self):
        """测试列出所有键"""
        store = MemoryStateStore()

        await store.save("agent:1", "data1")
        await store.save("agent:2", "data2")
        await store.save("task:1", "data3")

        # 列出所有键
        all_keys = await store.list_keys()
        assert len(all_keys) == 3

        # 列出带前缀的键
        agent_keys = await store.list_keys("agent:")
        assert len(agent_keys) == 2


class TestStateManager:
    """测试状态管理器"""

    @pytest.mark.asyncio
    async def test_save_and_get_agent_state(self):
        """测试保存和获取Agent状态"""
        manager = StateManager()

        # 创建Agent状态
        state = AgentState(
            agent_id="agent-1",
            status=AgentStatus.BUSY,
            current_task="task-1",
        )

        # 保存状态
        await manager.save_agent_state(state)

        # 获取状态
        retrieved = await manager.get_agent_state("agent-1")

        assert retrieved is not None
        assert retrieved.agent_id == "agent-1"
        assert retrieved.status == AgentStatus.BUSY
        assert retrieved.current_task == "task-1"

    @pytest.mark.asyncio
    async def test_save_and_get_task_state(self):
        """测试保存和获取Task状态"""
        manager = StateManager()

        # 创建Task
        task = Task(
            task_id="task-1",
            source_agent="agent-1",
            target_agent="agent-2",
            action="execute",
            status=TaskStatus.RUNNING,
        )

        # 保存状态
        await manager.save_task_state(task)

        # 获取状态
        retrieved = await manager.get_task_state("task-1")

        assert retrieved is not None
        assert retrieved.task_id == "task-1"
        assert retrieved.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_list_agents(self):
        """测试列出所有Agent"""
        manager = StateManager()

        # 保存多个Agent状态
        await manager.save_agent_state(AgentState(agent_id="agent-1"))
        await manager.save_agent_state(AgentState(agent_id="agent-2"))

        # 列出所有Agent
        agents = await manager.list_agents()

        assert len(agents) == 2
        assert "agent-1" in agents
        assert "agent-2" in agents
