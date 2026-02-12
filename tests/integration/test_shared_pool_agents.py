"""SharedMemoryPool 集成测试 - 多 Agent 共享"""

import pytest

from loom.memory.shared_pool import SharedMemoryPool


@pytest.mark.asyncio
async def test_two_agents_share_pool():
    """两个 Agent 共享同一 pool，A 写 B 读"""
    from unittest.mock import MagicMock

    from loom.agent.core import Agent

    pool = SharedMemoryPool(pool_id="shared")

    # 创建 mock LLM provider
    mock_llm = MagicMock()
    mock_llm.model = "test-model"
    mock_llm.supports_streaming = False

    agent_a = Agent(
        node_id="agent-a",
        llm_provider=mock_llm,
        system_prompt="You are agent A",
        shared_pool=pool,
        max_iterations=1,
    )
    agent_b = Agent(
        node_id="agent-b",
        llm_provider=mock_llm,
        system_prompt="You are agent B",
        shared_pool=pool,
        max_iterations=1,
    )

    # Agent A 写入
    await pool.write("research", {"finding": "important data"}, writer_id="agent-a")

    # Agent B 读取
    entry = await pool.read("research")
    assert entry is not None
    assert entry.content == {"finding": "important data"}
    assert entry.created_by == "agent-a"

    # 两个 Agent 共享同一 pool 引用
    assert agent_a.shared_pool is agent_b.shared_pool


@pytest.mark.asyncio
async def test_pool_propagates_to_child():
    """子 Agent 自动继承 pool 引用"""
    from unittest.mock import MagicMock

    from loom.agent.core import Agent

    pool = SharedMemoryPool(pool_id="inherited")

    mock_llm = MagicMock()
    mock_llm.model = "test-model"
    mock_llm.supports_streaming = False

    parent = Agent(
        node_id="parent",
        llm_provider=mock_llm,
        system_prompt="Parent agent",
        shared_pool=pool,
        max_iterations=1,
    )

    # 通过 _create_child_node 创建子节点
    child = await parent._create_child_node()

    assert child.shared_pool is pool
    assert child.shared_pool is parent.shared_pool


@pytest.mark.asyncio
async def test_factory_passes_shared_pool():
    """AgentFactory.create 正确传递 shared_pool"""
    from unittest.mock import MagicMock

    from loom.agent.factory import AgentFactory

    pool = SharedMemoryPool(pool_id="factory-test")

    mock_llm = MagicMock()
    mock_llm.model = "test-model"
    mock_llm.supports_streaming = False

    agent = AgentFactory.create(
        llm=mock_llm,
        system_prompt="Test",
        shared_pool=pool,
    )

    assert agent.shared_pool is pool
