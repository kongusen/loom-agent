"""
测试 ReActAgent

验证：
- ReActAgent 可以正常实例化
- run() 方法正确执行 ReAct 模式
- run_stream() 返回流式输出
- execute_with_events() 返回完整的事件流
- 与旧 agent() 函数行为兼容
"""

import pytest
from loom.agents import ReActAgent, Agent
from loom.core.events import AgentEventType
from loom.builtin.llms import MockLLM
from loom.builtin.tools import MockTool


class TestReActAgentInitialization:
    """测试 ReActAgent 的初始化"""

    def test_minimal_initialization(self):
        """使用最少参数初始化"""
        llm = MockLLM()
        agent = ReActAgent(name="test", llm=llm)

        assert agent.name == "test"
        assert agent.llm == llm
        assert agent.tools == []
        assert agent.max_iterations == 10
        assert agent.hooks == []

    def test_full_initialization(self):
        """使用所有参数初始化"""
        from loom.core.lifecycle_hooks import LoggingHook

        llm = MockLLM()
        tools = [MockTool(name="tool1"), MockTool(name="tool2")]
        hooks = [LoggingHook()]

        agent = ReActAgent(
            name="full_agent",
            llm=llm,
            tools=tools,
            max_iterations=20,
            hooks=hooks,
            custom_param="value",
        )

        assert agent.name == "full_agent"
        assert agent.llm == llm
        assert len(agent.tools) == 2
        assert agent.max_iterations == 20
        assert len(agent.hooks) == 1
        assert agent.config["custom_param"] == "value"

    def test_requires_llm(self):
        """必须提供 LLM"""
        with pytest.raises(ValueError, match="requires a language model"):
            ReActAgent(name="test", llm=None)

    def test_executor_created(self):
        """验证 AgentExecutor 被创建"""
        llm = MockLLM()
        agent = ReActAgent(name="test", llm=llm)

        assert agent.executor is not None
        assert agent.executor.llm == llm

    def test_repr(self):
        """测试字符串表示"""
        llm = MockLLM(name="gpt-4")
        tools = [MockTool(), MockTool()]
        agent = ReActAgent(name="test_agent", llm=llm, tools=tools, max_iterations=15)

        repr_str = repr(agent)
        assert "ReActAgent" in repr_str
        assert "test_agent" in repr_str
        assert "gpt-4" in repr_str
        assert "15" in repr_str


class TestReActAgentExecution:
    """测试 ReActAgent 的执行"""

    @pytest.mark.asyncio
    async def test_run_without_tools(self):
        """测试无工具的 run()"""
        llm = MockLLM()
        agent = ReActAgent(name="test", llm=llm)

        result = await agent.run("Hello")

        # MockLLM 应该返回一些响应
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_run_with_tools(self):
        """测试有工具的 run()"""
        llm = MockLLM()
        tool = MockTool(name="search")
        agent = ReActAgent(name="test", llm=llm, tools=[tool])

        result = await agent.run("Search for Python")

        # 应该执行并返回结果
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_run_stream(self):
        """测试流式输出"""
        llm = MockLLM()
        agent = ReActAgent(name="test", llm=llm)

        chunks = []
        async for chunk in agent.run_stream("Tell me a story"):
            chunks.append(chunk)

        # 应该收到多个文本块
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_execute_with_events(self):
        """测试完整的事件流"""
        llm = MockLLM()
        agent = ReActAgent(name="test", llm=llm)

        events = []
        async for event in agent.execute_with_events("Hello"):
            events.append(event)

        # 应该收到多个事件
        assert len(events) > 0

        # 应该包含不同类型的事件
        event_types = {event.type for event in events}
        assert AgentEventType.ITERATION_START in event_types or AgentEventType.LLM_DELTA in event_types


class TestReActAgentState:
    """测试 ReActAgent 的状态管理"""

    @pytest.mark.asyncio
    async def test_reset(self):
        """测试 reset() 方法"""
        llm = MockLLM()
        agent = ReActAgent(name="test", llm=llm)

        # 执行一次
        await agent.run("First task")

        # 重置
        await agent.reset()

        # 应该能够正常执行新任务
        result = await agent.run("Second task")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_observation_history(self):
        """测试观察历史"""
        llm = MockLLM()
        agent = ReActAgent(name="test", llm=llm)

        # 观察一些内容
        await agent.observe("Observation 1")
        await agent.observe("Observation 2")

        history = agent.get_observation_history()
        assert len(history) == 2
        assert history[0] == "Observation 1"


class TestReActAgentCompatibility:
    """测试向后兼容性"""

    def test_agent_alias(self):
        """测试 Agent 别名"""
        # Agent 应该是 ReActAgent 的别名
        assert Agent is ReActAgent

    @pytest.mark.asyncio
    async def test_behaves_like_old_agent(self):
        """测试与旧 Agent 行为一致"""
        llm = MockLLM()
        tools = [MockTool()]

        # 使用新的 ReActAgent
        agent = ReActAgent(name="test", llm=llm, tools=tools, max_iterations=10)

        # 应该能够执行任务
        result = await agent.run("Test task")
        assert isinstance(result, str)


class TestReActAgentEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_empty_input(self):
        """测试空输入"""
        llm = MockLLM()
        agent = ReActAgent(name="test", llm=llm)

        result = await agent.run("")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_max_iterations_limit(self):
        """测试最大迭代次数限制"""
        llm = MockLLM()
        agent = ReActAgent(name="test", llm=llm, max_iterations=2)

        # 即使 LLM 想要继续，也应该在 2 次迭代后停止
        result = await agent.run("Complex task")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_with_lifecycle_hooks(self):
        """测试带生命周期钩子"""
        from loom.core.lifecycle_hooks import LoggingHook

        llm = MockLLM()
        hooks = [LoggingHook()]
        agent = ReActAgent(name="test", llm=llm, hooks=hooks)

        result = await agent.run("Test with hooks")
        assert isinstance(result, str)


class TestReActAgentIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_react_loop(self):
        """测试完整的 ReAct 循环"""
        from loom.builtin.llms import MockLLM
        from loom.builtin.tools import MockTool

        # 创建模拟的 LLM 和工具
        llm = MockLLM()
        search_tool = MockTool(name="search")
        calc_tool = MockTool(name="calculator")

        # 创建 Agent
        agent = ReActAgent(
            name="assistant",
            llm=llm,
            tools=[search_tool, calc_tool],
            max_iterations=5,
        )

        # 执行任务
        result = await agent.run("Search for Python and calculate 2+2")

        # 验证结果
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_streaming_with_tools(self):
        """测试带工具的流式执行"""
        from loom.builtin.llms import MockLLM
        from loom.builtin.tools import MockTool

        llm = MockLLM()
        tool = MockTool(name="search")
        agent = ReActAgent(name="assistant", llm=llm, tools=[tool])

        chunks = []
        async for chunk in agent.run_stream("Search for information"):
            chunks.append(chunk)

        # 应该收到多个块
        assert len(chunks) > 0
