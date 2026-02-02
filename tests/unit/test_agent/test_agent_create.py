"""
测试 Agent.create() 方法 - Phase 3
验证渐进式披露功能：简单用法自动创建默认组件
"""

import pytest

from loom.agent.core import Agent
from loom.events.event_bus import EventBus
from loom.providers.llm.mock import MockLLMProvider


@pytest.fixture
def mock_llm():
    """创建 Mock LLM Provider"""
    return MockLLMProvider()


class TestAgentCreateEventBus:
    """测试 Agent.create() 自动创建 EventBus（Phase 3 Task 1）"""

    def test_auto_create_event_bus(self, mock_llm):
        """测试未传 event_bus 时自动创建"""
        # 不传 event_bus 参数
        agent = Agent.create(
            mock_llm,
            system_prompt="Test agent",
        )

        # 应该自动创建 EventBus
        assert agent.event_bus is not None
        assert isinstance(agent.event_bus, EventBus)

    def test_explicit_event_bus(self, mock_llm):
        """测试显式传入 event_bus 时使用传入的实例"""
        # 显式创建 EventBus
        custom_bus = EventBus()

        agent = Agent.create(
            mock_llm,
            system_prompt="Test agent",
            event_bus=custom_bus,
        )

        # 应该使用传入的 EventBus 实例
        assert agent.event_bus is custom_bus

    def test_shared_event_bus_multi_agents(self, mock_llm):
        """测试多 Agent 共享同一 EventBus"""
        # 创建共享的 EventBus
        shared_bus = EventBus()

        # 创建两个 Agent，都使用同一 EventBus
        agent1 = Agent.create(
            mock_llm,
            system_prompt="Agent 1",
            event_bus=shared_bus,
        )

        agent2 = Agent.create(
            mock_llm,
            system_prompt="Agent 2",
            event_bus=shared_bus,
        )

        # 两个 Agent 应该共享同一 EventBus 实例
        assert agent1.event_bus is shared_bus
        assert agent2.event_bus is shared_bus
        assert agent1.event_bus is agent2.event_bus
