"""
Agent Unit Tests

测试Agent类的核心功能
"""

from loom.events.event_bus import EventBus
from loom.orchestration.agent import Agent
from loom.providers.llm.mock import MockLLMProvider


class TestAgentInit:
    """测试Agent初始化"""

    def test_agent_init_basic(self):
        """测试基本初始化"""
        llm = MockLLMProvider()
        event_bus = EventBus()

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            event_bus=event_bus,
        )

        assert agent.node_id == "test-agent"
        assert agent.llm_provider == llm
        assert agent.event_bus == event_bus

    def test_agent_init_with_system_prompt(self):
        """测试带系统提示的初始化"""
        llm = MockLLMProvider()
        event_bus = EventBus()

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            event_bus=event_bus,
            system_prompt="You are a helpful assistant",
        )

        assert "helpful assistant" in agent.system_prompt

    def test_agent_init_with_tools(self):
        """测试带工具的初始化"""
        llm = MockLLMProvider()
        event_bus = EventBus()

        def test_tool(arg1: str) -> str:
            """Test tool"""
            return f"Result: {arg1}"

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            event_bus=event_bus,
            tools=[test_tool],
        )

        assert len(agent.tools) > 0


class TestAgentBuildToolList:
    """测试Agent构建工具列表"""

    def test_build_tool_list_basic(self):
        """测试基本工具列表构建"""
        llm = MockLLMProvider()
        event_bus = EventBus()

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            event_bus=event_bus,
        )

        tools = agent._build_tool_list()

        assert isinstance(tools, list)
        # 应该至少包含done工具
        assert len(tools) > 0

    def test_build_tool_list_with_custom_tools(self):
        """测试带自定义工具的工具列表构建"""
        llm = MockLLMProvider()
        event_bus = EventBus()

        def custom_tool(arg: str) -> str:
            """Custom tool"""
            return f"Result: {arg}"

        agent = Agent(
            node_id="test-agent",
            llm_provider=llm,
            event_bus=event_bus,
            tools=[custom_tool],
        )

        tools = agent._build_tool_list()

        assert isinstance(tools, list)
        assert len(tools) > 1  # custom tool + done tool
