"""
Loom App Unit Tests

测试Loom应用主类
"""

from unittest.mock import Mock, patch

import pytest

from loom.api.app import LoomApp
from loom.api.models import AgentConfig


class TestLoomAppInit:
    """测试LoomApp初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        app = LoomApp()

        assert app.event_bus is not None
        assert app.dispatcher is not None
        assert app._llm_provider is None
        assert app._default_tools == []
        assert app._agents == {}

    def test_init_with_event_bus(self):
        """测试带事件总线的初始化"""
        mock_event_bus = Mock()
        app = LoomApp(event_bus=mock_event_bus)

        assert app.event_bus == mock_event_bus


class TestSetLLMProvider:
    """测试设置LLM提供者"""

    def test_set_llm_provider(self):
        """测试设置LLM提供者"""
        app = LoomApp()
        mock_llm = Mock()

        result = app.set_llm_provider(mock_llm)

        assert app._llm_provider == mock_llm
        assert result == app  # 支持链式调用


class TestAddTools:
    """测试添加工具"""

    def test_add_tools(self):
        """测试添加工具"""
        app = LoomApp()
        tools = [{"name": "tool1"}, {"name": "tool2"}]

        result = app.add_tools(tools)

        assert len(app._default_tools) == 2
        assert result == app  # 支持链式调用


class TestCreateAgent:
    """测试创建Agent"""

    @patch("loom.api.app.Agent")
    def test_create_agent_success(self, mock_agent_class):
        """测试成功创建Agent"""
        app = LoomApp()
        mock_llm = Mock()
        app.set_llm_provider(mock_llm)

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        config = AgentConfig(agent_id="test-agent", name="Test Agent")
        agent = app.create_agent(config)

        assert agent == mock_agent
        assert app._agents["test-agent"] == mock_agent
        mock_agent_class.assert_called_once()

    def test_create_agent_no_llm_provider(self):
        """测试没有LLM提供者时创建Agent失败"""
        app = LoomApp()
        config = AgentConfig(agent_id="test-agent", name="Test Agent")

        with pytest.raises(ValueError, match="LLM provider is required"):
            app.create_agent(config)


class TestGetAgent:
    """测试获取Agent"""

    @patch("loom.api.app.Agent")
    def test_get_agent_exists(self, mock_agent_class):
        """测试获取存在的Agent"""
        app = LoomApp()
        mock_llm = Mock()
        app.set_llm_provider(mock_llm)

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        config = AgentConfig(agent_id="test-agent", name="Test Agent")
        app.create_agent(config)

        agent = app.get_agent("test-agent")
        assert agent == mock_agent

    def test_get_agent_not_exists(self):
        """测试获取不存在的Agent"""
        app = LoomApp()
        agent = app.get_agent("non-existent")
        assert agent is None


class TestListAgents:
    """测试列出Agents"""

    @patch("loom.api.app.Agent")
    def test_list_agents(self, mock_agent_class):
        """测试列出所有Agents"""
        app = LoomApp()
        mock_llm = Mock()
        app.set_llm_provider(mock_llm)

        mock_agent_class.return_value = Mock()

        config1 = AgentConfig(agent_id="agent-1", name="Agent 1")
        config2 = AgentConfig(agent_id="agent-2", name="Agent 2")
        app.create_agent(config1)
        app.create_agent(config2)

        agents = app.list_agents()
        assert len(agents) == 2
        assert "agent-1" in agents
        assert "agent-2" in agents


class TestCreateAgentWithTools:
    """测试创建Agent时使用工具"""

    @patch("loom.api.app.Agent")
    def test_create_agent_with_tools_parameter(self, mock_agent_class):
        """测试创建Agent时传递工具参数（触发line 128）"""
        app = LoomApp()
        mock_llm = Mock()
        app.set_llm_provider(mock_llm)

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        config = AgentConfig(agent_id="test-agent", name="Test Agent")
        tools = [{"name": "custom_tool", "description": "A custom tool"}]

        agent = app.create_agent(config, tools=tools)

        assert agent == mock_agent
        # 验证Agent被调用时传入了合并后的工具列表
        call_args = mock_agent_class.call_args
        assert "tools" in call_args.kwargs
        agent_tools = call_args.kwargs["tools"]
        assert agent_tools == tools  # 因为没有默认工具，应该只是传入的工具

    @patch("loom.api.app.Agent")
    def test_create_agent_with_global_and_parameter_tools(self, mock_agent_class):
        """测试创建Agent时合并全局工具和参数工具（触发line 128）"""
        app = LoomApp()
        mock_llm = Mock()
        app.set_llm_provider(mock_llm)

        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent

        # 添加全局工具
        global_tools = [{"name": "global_tool"}]
        app.add_tools(global_tools)

        config = AgentConfig(agent_id="test-agent", name="Test Agent")
        param_tools = [{"name": "param_tool"}]

        agent = app.create_agent(config, tools=param_tools)

        assert agent == mock_agent
        # 验证Agent被调用时传入了合并后的工具列表
        call_args = mock_agent_class.call_args
        agent_tools = call_args.kwargs["tools"]
        assert len(agent_tools) == 2
        assert global_tools[0] in agent_tools
        assert param_tools[0] in agent_tools

