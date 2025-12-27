"""
测试 loom.weave 模块
"""

import pytest
from loom.weave import (
    create_agent,
    create_tool,
    create_crew,
    run_async,
    reset_app,
    get_app,
    configure_app
)


@pytest.fixture(autouse=True)
def reset_global_app():
    """每个测试前重置全局 App"""
    reset_app()
    yield
    reset_app()


class TestGlobalAppManagement:
    """测试全局 App 管理"""

    def test_get_app_initially_none(self):
        """测试初始状态下 App 为 None"""
        assert get_app() is None

    def test_create_agent_creates_app(self):
        """测试创建 Agent 会自动创建 App"""
        agent = create_agent("test-agent")
        assert get_app() is not None
        assert agent.node_id == "test-agent"

    def test_configure_app_before_creation(self):
        """测试在创建前配置 App"""
        configure_app({"budget": 5000})
        app = get_app()
        assert app is not None

    def test_configure_app_after_creation_raises_error(self):
        """测试在创建后配置 App 会抛出错误"""
        create_agent("test-agent")
        with pytest.raises(RuntimeError):
            configure_app({"budget": 5000})


class TestCreateAgent:
    """测试 create_agent 函数"""

    def test_create_simple_agent(self):
        """测试创建简单的 Agent"""
        agent = create_agent("test-agent", role="Tester")
        assert agent.node_id == "test-agent"
        assert agent.role == "Tester"

    def test_create_agent_with_default_role(self):
        """测试使用默认角色创建 Agent"""
        agent = create_agent("test-agent")
        assert agent.role == "Assistant"

    def test_create_multiple_agents(self):
        """测试创建多个 Agent"""
        agent1 = create_agent("agent-1", role="Role1")
        agent2 = create_agent("agent-2", role="Role2")
        assert agent1.node_id == "agent-1"
        assert agent2.node_id == "agent-2"


class TestCreateTool:
    """测试 create_tool 函数"""

    def test_create_simple_tool(self):
        """测试创建简单的工具"""
        def test_func(x: int) -> int:
            """测试函数"""
            return x * 2

        tool = create_tool("test-tool", test_func)
        assert tool.node_id == "test-tool"
        assert tool.func == test_func

    def test_create_tool_with_description(self):
        """测试创建带描述的工具"""
        def test_func(x: int) -> int:
            return x * 2

        tool = create_tool("test-tool", test_func, description="自定义描述")
        assert tool.tool_def.description == "自定义描述"


class TestCreateCrew:
    """测试 create_crew 函数"""

    def test_create_simple_crew(self):
        """测试创建简单的 Crew"""
        agent1 = create_agent("agent-1")
        agent2 = create_agent("agent-2")
        crew = create_crew("test-crew", [agent1, agent2])
        assert crew.node_id == "test-crew"
        assert len(crew.agents) == 2


@pytest.mark.asyncio
class TestWeaveExecution:
    """测试 loom.weave 的执行功能"""

    async def test_run_agent(self):
        """测试运行简单的 Agent"""
        agent = create_agent("test-agent")
        
        result = await run_async(agent, "Hello")
        # AgentNode 返回 dict with "response"
        assert "response" in result
        assert result["response"] is not None

    async def test_run_agent_with_tool(self):
        """测试运行带工具的 Agent (集成测试)"""
        
        # 定义工具
        def calculator(expression: str) -> str:
            """计算器工具"""
            return "42"

        tool = create_tool("calculator", calculator)
        
        # 创建 Agent
        # MockLLMProvider 会在输入包含 "calculate" 时尝试调用 "calculator" 工具
        agent = create_agent("math-agent", tools=[tool])
        
        # 运行
        result = await run_async(agent, "Please calculate 21 * 2")
        
        # 验证
        assert "response" in result
        # 由于我们修复了 AgentNode 的 streaming loop，它应该能正确处理工具调用并返回
