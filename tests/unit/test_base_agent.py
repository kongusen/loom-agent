"""
测试 BaseAgent 抽象基类

验证：
- BaseAgent 是抽象类，不能直接实例化
- 子类必须实现 run() 方法
- observe() 和 reset() 方法正常工作
- 工具函数（is_agent, validate_agent）正常工作
"""

import pytest
from loom.core.base_agent import BaseAgent, is_agent, validate_agent


class TestBaseAgentAbstract:
    """测试 BaseAgent 的抽象性"""

    def test_cannot_instantiate_directly(self):
        """BaseAgent 不能直接实例化"""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseAgent(name="test")

    def test_must_implement_run(self):
        """子类必须实现 run() 方法"""

        class IncompleteAgent(BaseAgent):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteAgent(name="incomplete")


class TestBaseAgentImplementation:
    """测试 BaseAgent 的正常实现"""

    @pytest.fixture
    def simple_agent(self):
        """创建一个简单的测试 Agent"""

        class EchoAgent(BaseAgent):
            async def run(self, input: str) -> str:
                return f"Echo: {input}"

        return EchoAgent(name="echo")

    @pytest.mark.asyncio
    async def test_run_method(self, simple_agent):
        """测试 run() 方法"""
        result = await simple_agent.run("Hello")
        assert result == "Echo: Hello"

    @pytest.mark.asyncio
    async def test_observe_method(self, simple_agent):
        """测试 observe() 方法"""
        # 初始历史为空
        assert len(simple_agent.get_observation_history()) == 0

        # 观察一些内容
        await simple_agent.observe("Message 1")
        await simple_agent.observe("Message 2")
        await simple_agent.observe("Message 3")

        # 验证观察历史
        history = simple_agent.get_observation_history()
        assert len(history) == 3
        assert history[0] == "Message 1"
        assert history[1] == "Message 2"
        assert history[2] == "Message 3"

    @pytest.mark.asyncio
    async def test_reset_method(self, simple_agent):
        """测试 reset() 方法"""
        # 添加一些观察
        await simple_agent.observe("Message 1")
        await simple_agent.observe("Message 2")
        assert len(simple_agent.get_observation_history()) == 2

        # 重置
        await simple_agent.reset()

        # 验证历史被清空
        assert len(simple_agent.get_observation_history()) == 0

    @pytest.mark.asyncio
    async def test_run_stream_default(self, simple_agent):
        """测试 run_stream() 默认实现"""
        chunks = []
        async for chunk in simple_agent.run_stream("Hello"):
            chunks.append(chunk)

        # 默认实现应该一次性返回完整结果
        assert len(chunks) == 1
        assert chunks[0] == "Echo: Hello"


class TestBaseAgentAttributes:
    """测试 BaseAgent 的属性"""

    def test_initialization_with_minimal_params(self):
        """使用最少参数初始化"""

        class MinimalAgent(BaseAgent):
            async def run(self, input: str) -> str:
                return "ok"

        agent = MinimalAgent(name="minimal")

        assert agent.name == "minimal"
        assert agent.llm is None
        assert agent.tools == []
        assert agent.config == {}

    def test_initialization_with_all_params(self):
        """使用所有参数初始化"""
        from loom.builtin.llms import MockLLM
        from loom.builtin.tools import MockTool

        class FullAgent(BaseAgent):
            async def run(self, input: str) -> str:
                return "ok"

        llm = MockLLM()
        tools = [MockTool()]
        agent = FullAgent(
            name="full",
            llm=llm,
            tools=tools,
            custom_param="value",
            max_iterations=10,
        )

        assert agent.name == "full"
        assert agent.llm == llm
        assert agent.tools == tools
        assert agent.config["custom_param"] == "value"
        assert agent.config["max_iterations"] == 10

    def test_repr(self):
        """测试字符串表示"""
        from loom.builtin.llms import MockLLM

        class TestAgent(BaseAgent):
            async def run(self, input: str) -> str:
                return "ok"

        llm = MockLLM()
        agent = TestAgent(name="test_agent", llm=llm)

        repr_str = repr(agent)
        assert "TestAgent" in repr_str
        assert "test_agent" in repr_str

    def test_str(self):
        """测试用户友好的字符串表示"""

        class TestAgent(BaseAgent):
            async def run(self, input: str) -> str:
                return "ok"

        agent = TestAgent(name="test_agent")
        str_repr = str(agent)
        assert "TestAgent[test_agent]" in str_repr


class TestUtilityFunctions:
    """测试工具函数"""

    def test_is_agent_true(self):
        """is_agent() 对 BaseAgent 实例返回 True"""

        class TestAgent(BaseAgent):
            async def run(self, input: str) -> str:
                return "ok"

        agent = TestAgent(name="test")
        assert is_agent(agent) is True

    def test_is_agent_false(self):
        """is_agent() 对非 BaseAgent 对象返回 False"""
        assert is_agent("not an agent") is False
        assert is_agent(123) is False
        assert is_agent(None) is False
        assert is_agent({"name": "fake"}) is False

    def test_validate_agent_success(self):
        """validate_agent() 对有效 Agent 不抛出异常"""

        class TestAgent(BaseAgent):
            async def run(self, input: str) -> str:
                return "ok"

        agent = TestAgent(name="test")
        validate_agent(agent)  # 不应抛出异常

    def test_validate_agent_failure(self):
        """validate_agent() 对无效对象抛出 TypeError"""
        with pytest.raises(TypeError, match="must be a BaseAgent instance"):
            validate_agent("not an agent")

        with pytest.raises(TypeError, match="must be a BaseAgent instance"):
            validate_agent(123)

    def test_validate_agent_custom_name(self):
        """validate_agent() 使用自定义参数名"""
        with pytest.raises(TypeError, match="my_param must be a BaseAgent instance"):
            validate_agent("invalid", name="my_param")


class TestCustomAgentExample:
    """测试自定义 Agent 的示例"""

    @pytest.mark.asyncio
    async def test_stateful_agent(self):
        """测试带状态的自定义 Agent"""

        class CounterAgent(BaseAgent):
            def __init__(self, name: str, **config):
                super().__init__(name=name, **config)
                self.count = 0

            async def run(self, input: str) -> str:
                self.count += 1
                return f"Call #{self.count}: {input}"

        agent = CounterAgent(name="counter")

        assert await agent.run("First") == "Call #1: First"
        assert await agent.run("Second") == "Call #2: Second"
        assert await agent.run("Third") == "Call #3: Third"

    @pytest.mark.asyncio
    async def test_agent_with_llm_access(self):
        """测试可以访问 LLM 的 Agent"""
        from loom.builtin.llms import MockLLM

        class LLMAgent(BaseAgent):
            async def run(self, input: str) -> str:
                if self.llm is None:
                    return "No LLM"
                # 调用 LLM（这里简化为直接返回）
                return f"LLM processed: {input}"

        # 无 LLM
        agent1 = LLMAgent(name="agent1")
        assert await agent1.run("test") == "No LLM"

        # 有 LLM
        agent2 = LLMAgent(name="agent2", llm=MockLLM())
        assert await agent2.run("test") == "LLM processed: test"

    @pytest.mark.asyncio
    async def test_agent_with_tools_access(self):
        """测试可以访问工具的 Agent"""
        from loom.builtin.tools import MockTool

        class ToolAgent(BaseAgent):
            async def run(self, input: str) -> str:
                if not self.tools:
                    return "No tools"
                tool_names = [t.name for t in self.tools]
                return f"Tools: {', '.join(tool_names)}"

        # 无工具
        agent1 = ToolAgent(name="agent1")
        assert await agent1.run("test") == "No tools"

        # 有工具
        tool1 = MockTool(name="tool1")
        tool2 = MockTool(name="tool2")
        agent2 = ToolAgent(name="agent2", tools=[tool1, tool2])
        assert await agent2.run("test") == "Tools: tool1, tool2"
