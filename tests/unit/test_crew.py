"""
测试增强的 Crew (v0.1.5)

验证：
- Sequential/Parallel/Coordinated 三种模式
- Message 接口和追溯
- 智能任务分解
- 执行历史管理
"""

import pytest
from loom.patterns.crew import (
    Crew,
    sequential_crew,
    parallel_crew,
    coordinated_crew,
)
from loom.core.base_agent import BaseAgent
from loom.core.message import Message, create_user_message
from loom.builtin.llms import MockLLM


# ===== 测试用 Agent =====


class EchoAgent(BaseAgent):
    """回声 Agent（用于测试）"""

    def __init__(self, name: str, prefix: str = ""):
        super().__init__(name=name)
        self.prefix = prefix

    async def run(self, input: str) -> str:
        if self.prefix:
            return f"{self.prefix}: {input}"
        return input

    async def reply(self, message: Message) -> Message:
        """实现 Message 接口"""
        result = await self.run(message.get_text_content())
        return message.reply(result, name=self.name)


class SimpleTestAgent(BaseAgent):
    """简单测试 Agent（替代 SimpleAgent）"""

    def __init__(self, name: str, llm=None, **kwargs):
        super().__init__(name=name, **kwargs)
        self.llm = llm or MockLLM()

    async def run(self, input: str) -> str:
        """简单的 LLM 调用"""
        # MockLLM 使用 stream() 接口
        content = ""
        async for event in self.llm.stream(
            messages=[{"role": "user", "content": input}]
        ):
            if hasattr(event, 'content') and event.content:
                content += event.content
        return content or "OK"

    async def reply(self, message: Message) -> Message:
        """Message 接口"""
        result = await self.run(message.get_text_content())
        return message.reply(result, name=self.name)


# 创建别名以保持测试代码不变
SimpleAgent = SimpleTestAgent


# ===== Crew 创建测试 =====


class TestCrewCreation:
    """测试 Crew 创建"""

    def test_sequential_crew_creation(self):
        """创建顺序 Crew"""
        agent1 = EchoAgent("a1")
        agent2 = EchoAgent("a2")

        crew = Crew([agent1, agent2], mode="sequential")

        assert crew.mode == "sequential"
        assert len(crew.agents) == 2
        assert "a1 -> a2" in crew.name

    def test_parallel_crew_creation(self):
        """创建并行 Crew"""
        agent1 = EchoAgent("a1")
        agent2 = EchoAgent("a2")

        crew = Crew([agent1, agent2], mode="parallel")

        assert crew.mode == "parallel"
        assert len(crew.agents) == 2
        assert "a1 + a2" in crew.name

    def test_coordinated_crew_creation(self):
        """创建协调 Crew"""
        agent1 = EchoAgent("a1")
        agent2 = EchoAgent("a2")
        coordinator = EchoAgent("coordinator")

        crew = Crew(
            [agent1, agent2], mode="coordinated", coordinator=coordinator
        )

        assert crew.mode == "coordinated"
        assert crew.coordinator == coordinator
        assert len(crew.agents) == 2

    def test_requires_at_least_one_agent(self):
        """至少需要一个 Agent"""
        with pytest.raises(ValueError, match="at least one agent"):
            Crew([], mode="sequential")

    def test_invalid_mode(self):
        """无效的模式"""
        agent1 = EchoAgent("a1")

        with pytest.raises(ValueError, match="Invalid mode"):
            Crew([agent1], mode="invalid")

    def test_coordinated_requires_coordinator(self):
        """协调模式需要协调器"""
        agent1 = EchoAgent("a1")

        with pytest.raises(ValueError, match="requires a coordinator"):
            Crew([agent1], mode="coordinated")

    def test_custom_name(self):
        """自定义名称"""
        agent1 = EchoAgent("a1")
        agent2 = EchoAgent("a2")

        crew = Crew([agent1, agent2], mode="sequential", name="my_crew")

        assert crew.name == "my_crew"


# ===== Sequential Mode 测试 =====


class TestSequentialCrew:
    """测试顺序 Crew"""

    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """基本执行"""
        agent1 = EchoAgent("a1", prefix="A")
        agent2 = EchoAgent("a2", prefix="B")

        crew = Crew([agent1, agent2], mode="sequential")

        result = await crew.run("Test")

        assert result == "B: A: Test"

    @pytest.mark.asyncio
    async def test_with_real_agents(self):
        """使用真实 Agent"""
        llm = MockLLM()

        agent1 = loom.agent("researcher", llm=llm)
        agent2 = loom.agent("writer", llm=llm)

        crew = Crew([agent1, agent2], mode="sequential")

        result = await crew.run("Write about AI")

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_message_interface(self):
        """测试 Message 接口"""
        agent1 = EchoAgent("a1", prefix="A")
        agent2 = EchoAgent("a2", prefix="B")

        crew = Crew([agent1, agent2], mode="sequential")

        msg = create_user_message("Test")
        reply = await crew.reply(msg)

        assert reply.content == "B: A: Test"
        assert reply.parent_id is not None

    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """测试便捷函数"""
        agent1 = EchoAgent("a1")
        agent2 = EchoAgent("a2")

        crew = sequential_crew(agent1, agent2)

        assert crew.mode == "sequential"
        result = await crew.run("Test")
        assert isinstance(result, str)


# ===== Parallel Mode 测试 =====


class TestParallelCrew:
    """测试并行 Crew"""

    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """基本执行"""
        agent1 = EchoAgent("a1", prefix="A")
        agent2 = EchoAgent("a2", prefix="B")
        agent3 = EchoAgent("a3", prefix="C")

        crew = Crew([agent1, agent2, agent3], mode="parallel")

        result = await crew.run("Test")

        # 结果应该包含所有 Agent 的输出
        assert "A: Test" in result
        assert "B: Test" in result
        assert "C: Test" in result

    @pytest.mark.asyncio
    async def test_parallel_execution_speed(self):
        """验证并行执行速度"""
        import time

        class SlowAgent(BaseAgent):
            async def run(self, input: str) -> str:
                import asyncio

                await asyncio.sleep(0.1)
                return f"{self.name}: {input}"

        agent1 = SlowAgent("a1")
        agent2 = SlowAgent("a2")
        agent3 = SlowAgent("a3")

        crew = Crew([agent1, agent2, agent3], mode="parallel")

        start = time.time()
        result = await crew.run("Test")
        elapsed = time.time() - start

        # 并行执行应该接近单个任务时间
        assert elapsed < 0.2  # 而不是 0.3 秒（顺序执行）
        assert "a1" in result
        assert "a2" in result
        assert "a3" in result

    @pytest.mark.asyncio
    async def test_custom_aggregator(self):
        """自定义聚合器"""

        def custom_agg(results):
            return " | ".join(results)

        agent1 = EchoAgent("a1", prefix="A")
        agent2 = EchoAgent("a2", prefix="B")

        crew = Crew([agent1, agent2], mode="parallel", aggregator=custom_agg)

        result = await crew.run("Test")

        assert " | " in result
        assert "A: Test" in result
        assert "B: Test" in result

    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """测试便捷函数"""
        agent1 = EchoAgent("a1")
        agent2 = EchoAgent("a2")

        crew = parallel_crew(agent1, agent2)

        assert crew.mode == "parallel"
        result = await crew.run("Test")
        assert isinstance(result, str)


# ===== Coordinated Mode 测试 =====


class TestCoordinatedCrew:
    """测试协调 Crew"""

    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """基本执行（使用 MockLLM）"""
        llm = MockLLM()

        specialist1 = loom.agent("specialist1", llm=llm)
        specialist2 = loom.agent("specialist2", llm=llm)
        coordinator = loom.agent("coordinator", llm=llm)

        crew = Crew(
            [specialist1, specialist2],
            mode="coordinated",
            coordinator=coordinator,
        )

        result = await crew.run("Complex task")

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_task_decomposition(self):
        """测试任务分解"""
        llm = MockLLM()

        # 模拟协调器返回 JSON 格式的任务分解
        class CoordinatorAgent(BaseAgent):
            async def run(self, input: str) -> str:
                return """
[
  {"id": "task1", "agent": "specialist1", "task": "Subtask 1", "depends_on": []},
  {"id": "task2", "agent": "specialist2", "task": "Subtask 2", "depends_on": ["task1"]}
]
"""

        specialist1 = loom.agent("specialist1", llm=llm)
        specialist2 = loom.agent("specialist2", llm=llm)
        coordinator = CoordinatorAgent("coordinator")

        crew = Crew(
            [specialist1, specialist2],
            mode="coordinated",
            coordinator=coordinator,
        )

        result = await crew.run("Task")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_convenience_function(self):
        """测试便捷函数"""
        llm = MockLLM()

        agent1 = loom.agent("a1", llm=llm)
        agent2 = loom.agent("a2", llm=llm)
        coordinator = loom.agent("coord", llm=llm)

        crew = coordinated_crew(agent1, agent2, coordinator=coordinator)

        assert crew.mode == "coordinated"
        assert crew.coordinator == coordinator


# ===== Message Interface 和追溯测试 =====


class TestCrewMessageInterface:
    """测试 Crew 的 Message 接口"""

    @pytest.mark.asyncio
    async def test_execute_with_history(self):
        """测试执行并获取历史"""
        agent1 = EchoAgent("a1", prefix="A")
        agent2 = EchoAgent("a2", prefix="B")

        crew = Crew([agent1, agent2], mode="sequential")

        task = create_user_message("Test task")
        result, history = await crew.execute_with_history(task)

        assert result.content == "B: A: Test task"
        assert len(history) >= 1
        assert result in history

    @pytest.mark.asyncio
    async def test_execution_history_recording(self):
        """测试执行历史记录"""
        agent1 = EchoAgent("a1")
        agent2 = EchoAgent("a2")

        crew = Crew([agent1, agent2], mode="sequential")

        # 执行几次任务
        await crew.run("Task 1")
        await crew.run("Task 2")

        history = crew.get_execution_history()

        assert len(history) == 2
        assert all("duration" in record for record in history)
        assert all("mode" in record for record in history)

    @pytest.mark.asyncio
    async def test_message_metadata(self):
        """测试 Message 元数据"""
        agent1 = EchoAgent("a1")
        agent2 = EchoAgent("a2")

        crew = Crew([agent1, agent2], mode="sequential")

        task = Message(
            role="user",
            content="Task",
            metadata={"priority": "high", "user_id": "123"},
        )

        result = await crew.reply(task)

        assert result.parent_id is not None


# ===== 执行图测试 =====


class TestCrewExecutionGraph:
    """测试执行图生成"""

    def test_sequential_graph(self):
        """顺序模式的执行图"""
        agent1 = EchoAgent("a1")
        agent2 = EchoAgent("a2")
        agent3 = EchoAgent("a3")

        crew = Crew([agent1, agent2, agent3], mode="sequential")

        graph = crew.get_execution_graph()

        assert len(graph["nodes"]) == 3
        assert len(graph["edges"]) == 2
        # a1 -> a2 -> a3
        assert {"from": "a1", "to": "a2"} in graph["edges"]
        assert {"from": "a2", "to": "a3"} in graph["edges"]

    def test_parallel_graph(self):
        """并行模式的执行图"""
        agent1 = EchoAgent("a1")
        agent2 = EchoAgent("a2")

        crew = Crew([agent1, agent2], mode="parallel")

        graph = crew.get_execution_graph()

        # 应该有 input, a1, a2, output 节点
        assert len(graph["nodes"]) == 4
        # 每个 agent 都连接到 input 和 output
        assert {"from": "input", "to": "a1"} in graph["edges"]
        assert {"from": "input", "to": "a2"} in graph["edges"]

    def test_coordinated_graph(self):
        """协调模式的执行图"""
        llm = MockLLM()

        agent1 = loom.agent("a1", llm=llm)
        agent2 = loom.agent("a2", llm=llm)
        coordinator = loom.agent("coord", llm=llm)

        crew = Crew([agent1, agent2], mode="coordinated", coordinator=coordinator)

        graph = crew.get_execution_graph()

        # 应该有 coordinator 节点
        assert any(node["type"] == "coordinator" for node in graph["nodes"])


# ===== 错误处理测试 =====


class TestCrewErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_agent_error_propagation(self):
        """Agent 错误应该传播"""

        class FailingAgent(BaseAgent):
            async def run(self, input: str) -> str:
                raise RuntimeError("Agent failed!")

        agent1 = EchoAgent("a1")
        failing = FailingAgent("failing")

        crew = Crew([agent1, failing], mode="sequential")

        with pytest.raises(RuntimeError, match="Agent failed"):
            await crew.run("Test")

    @pytest.mark.asyncio
    async def test_coordinated_fallback(self):
        """协调模式在分解失败时的降级"""
        llm = MockLLM()

        # 协调器返回无效 JSON
        class BadCoordinator(BaseAgent):
            async def run(self, input: str) -> str:
                return "Invalid JSON {not json}"

        agent1 = loom.agent("a1", llm=llm)
        agent2 = loom.agent("a2", llm=llm)
        coordinator = BadCoordinator("coord")

        crew = Crew([agent1, agent2], mode="coordinated", coordinator=coordinator)

        # 应该降级到 sequential 模式
        result = await crew.run("Task")

        assert isinstance(result, str)


# ===== 集成测试 =====


class TestCrewIntegration:
    """Crew 集成测试"""

    @pytest.mark.asyncio
    async def test_real_workflow(self):
        """真实工作流测试"""
        llm = MockLLM()

        # 研究 -> 写作 -> 审阅
        researcher = loom.agent("researcher", llm=llm)
        writer = loom.agent("writer", llm=llm)
        reviewer = loom.agent("reviewer", llm=llm)

        crew = sequential_crew(researcher, writer, reviewer)

        result = await crew.run("Write about AI")

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_multi_perspective_analysis(self):
        """多角度分析测试"""
        llm = MockLLM()

        technical = loom.agent("technical", llm=llm)
        business = loom.agent("business", llm=llm)
        user = loom.agent("user", llm=llm)

        crew = parallel_crew(technical, business, user)

        result = await crew.run("Analyze AI impact")

        assert isinstance(result, str)
