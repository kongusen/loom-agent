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


class TestAgentCreateSkills:
    """测试 Agent.create() 支持 skills 参数（Phase 3 Task 2）"""

    def test_create_with_skills_parameter(self, mock_llm):
        """测试传入 skills 参数时自动配置"""
        agent = Agent.create(
            mock_llm,
            system_prompt="Test agent",
            skills=["python-dev", "testing"],
        )

        # 应该设置 config.enabled_skills
        assert agent.config.enabled_skills == {"python-dev", "testing"}

        # 应该自动设置 skill_registry
        assert agent.skill_registry is not None

    def test_create_without_skills_parameter(self, mock_llm):
        """测试不传 skills 参数时保持现有行为"""
        agent = Agent.create(
            mock_llm,
            system_prompt="Test agent",
        )

        # config.enabled_skills 应该为空或默认值
        assert agent.config.enabled_skills == set()

    def test_create_with_empty_skills_list(self, mock_llm):
        """测试传入空 skills 列表"""
        agent = Agent.create(
            mock_llm,
            system_prompt="Test agent",
            skills=[],
        )

        # 应该设置为空集合
        assert agent.config.enabled_skills == set()

    def test_create_with_skills_uses_skill_market(self, mock_llm):
        """测试 skills 参数使用全局 skill_market"""
        from loom.skills.skill_registry import skill_market

        agent = Agent.create(
            mock_llm,
            system_prompt="Test agent",
            skills=["test-skill"],
        )

        # 应该使用全局 skill_market 作为 skill_registry
        assert agent.skill_registry is skill_market


class TestAgentCreateCapabilities:
    """测试 Agent.create() 支持 capabilities 参数（Phase 3 Task 3）"""

    def test_create_with_capabilities_parameter(self, mock_llm, tmp_path):
        """测试传入 capabilities 参数时自动配置组件"""
        from loom.capabilities.registry import CapabilityRegistry
        from loom.tools.sandbox import Sandbox
        from loom.tools.sandbox_manager import SandboxToolManager
        from loom.skills.skill_registry import skill_market

        # 创建组件
        sandbox = Sandbox(tmp_path)
        tool_manager = SandboxToolManager(sandbox)

        # 创建 CapabilityRegistry
        capabilities = CapabilityRegistry(
            sandbox_manager=tool_manager,
            skill_registry=skill_market,
            skill_activator=None,
        )

        # 使用 capabilities 创建 Agent
        agent = Agent.create(
            mock_llm,
            system_prompt="Test agent",
            capabilities=capabilities,
        )

        # 应该使用 CapabilityRegistry 中的组件
        assert agent.sandbox_manager is tool_manager
        assert agent.skill_registry is skill_market

    def test_create_without_capabilities_parameter(self, mock_llm):
        """测试不传 capabilities 参数时保持现有行为"""
        agent = Agent.create(
            mock_llm,
            system_prompt="Test agent",
        )

        # 不应该自动设置这些组件
        assert agent.sandbox_manager is None
        assert agent.skill_registry is None

    def test_create_capabilities_does_not_override_explicit_params(self, mock_llm, tmp_path):
        """测试 capabilities 不会覆盖显式传入的参数"""
        from loom.capabilities.registry import CapabilityRegistry
        from loom.tools.sandbox import Sandbox
        from loom.tools.sandbox_manager import SandboxToolManager
        from loom.skills.skill_registry import skill_market

        # 创建两套组件
        sandbox1 = Sandbox(tmp_path / "sandbox1")
        tool_manager1 = SandboxToolManager(sandbox1)

        sandbox2 = Sandbox(tmp_path / "sandbox2")
        tool_manager2 = SandboxToolManager(sandbox2)

        # 创建 CapabilityRegistry（包含 tool_manager1）
        capabilities = CapabilityRegistry(
            sandbox_manager=tool_manager1,
            skill_registry=skill_market,
        )

        # 显式传入 tool_manager2，应该优先使用显式传入的
        agent = Agent.create(
            mock_llm,
            system_prompt="Test agent",
            capabilities=capabilities,
            sandbox_manager=tool_manager2,
        )

        # 应该使用显式传入的 tool_manager2，而不是 capabilities 中的 tool_manager1
        assert agent.sandbox_manager is tool_manager2
        # skill_registry 没有显式传入，应该使用 capabilities 中的
        assert agent.skill_registry is skill_market
