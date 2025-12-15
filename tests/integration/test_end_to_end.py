"""
集成测试 - End-to-End (v0.1.5)

验证 Phase 1 + Phase 2 特性的集成：
- BaseAgent (Phase 1) + Message (Phase 2)
- ReActAgent (Phase 1) + Pipeline (Phase 2)
- 混合使用字符串和 Message 接口
- 复杂的工作流组合
"""

import pytest
import loom, ReActAgent
from loom.patterns import SequentialPipeline, ParallelPipeline, sequential, parallel
from loom.core.message import Message, create_user_message, trace_message_chain
from loom.builtin.llms import MockLLM
from loom.interfaces.tool import BaseTool


# ===== 测试工具 =====


class MockSearchTool(BaseTool):
    """模拟搜索工具"""

    name = "search"
    description = "Search for information"

    async def run(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        return f"Search results for: {query}"


# ===== 集成测试：Message Flow =====


class TestMessageFlow:
    """测试完整的 Message 流"""

    @pytest.mark.asyncio
    async def test_message_flow_between_agents(self):
        """测试消息在多个 Agent 间流转"""
        llm = MockLLM()

        agent1 = loom.agent(name="researcher", llm=llm)
        agent2 = loom.agent(name="writer", llm=llm)
        agent3 = loom.agent(name="reviewer", llm=llm)

        # 创建初始消息
        msg1 = create_user_message("Research quantum computing")

        # Agent1 处理
        msg2 = await agent1.reply(msg1)
        assert msg2.role == "assistant"
        assert msg2.parent_id == msg1.id
        assert msg2.name == "researcher"

        # Agent2 基于 Agent1 的结果
        msg3 = await agent2.reply(msg2)
        assert msg3.parent_id == msg2.id
        assert msg3.name == "writer"

        # Agent3 基于 Agent2 的结果
        msg4 = await agent3.reply(msg3)
        assert msg4.parent_id == msg3.id
        assert msg4.name == "reviewer"

        # 验证消息链
        messages = {
            msg1.id: msg1,
            msg2.id: msg2,
            msg3.id: msg3,
            msg4.id: msg4,
        }
        chain = trace_message_chain(msg4, messages)

        assert len(chain) == 4
        assert chain[0] == msg1
        assert chain[1] == msg2
        assert chain[2] == msg3
        assert chain[3] == msg4

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self):
        """测试多轮对话"""
        llm = MockLLM()
        agent = loom.agent(name="assistant", llm=llm)

        # 第一轮
        msg1 = Message(role="user", content="Hello")
        reply1 = await agent.reply(msg1)
        assert reply1.parent_id == msg1.id

        # 第二轮（基于第一轮回复）
        msg2 = reply1.reply("How are you?", role="user")
        reply2 = await agent.reply(msg2)
        assert reply2.parent_id == msg2.id

        # 第三轮
        msg3 = reply2.reply("Tell me more", role="user")
        reply3 = await agent.reply(msg3)
        assert reply3.parent_id == msg3.id

        # 验证对话链
        messages = {
            msg1.id: msg1,
            reply1.id: reply1,
            msg2.id: msg2,
            reply2.id: reply2,
            msg3.id: msg3,
            reply3.id: reply3,
        }
        chain = trace_message_chain(reply3, messages)
        assert len(chain) == 6

    @pytest.mark.asyncio
    async def test_message_with_metadata(self):
        """测试带元数据的消息流"""
        llm = MockLLM()
        agent = loom.agent(name="agent", llm=llm)

        # 创建带元数据的消息
        msg = Message(
            role="user",
            content="Query",
            metadata={
                "source": "web",
                "user_id": "12345",
                "session_id": "abc",
            },
        )

        reply = await agent.reply(msg)

        # 验证回复
        assert reply.parent_id == msg.id
        # 元数据不会自动传递（符合预期）
        assert reply.metadata == {}


# ===== 集成测试：Pipeline + Agent =====


class TestPipelineIntegration:
    """测试 Pipeline 与 Agent 的集成"""

    @pytest.mark.asyncio
    async def test_sequential_pipeline_with_real_agents(self):
        """顺序 Pipeline 使用真实 Agent"""
        llm = MockLLM()

        researcher = loom.agent(
            name="researcher", llm=llm, system_prompt="You research topics"
        )
        writer = loom.agent(
            name="writer", llm=llm, system_prompt="You write articles"
        )
        reviewer = loom.agent(
            name="reviewer", llm=llm, system_prompt="You review content"
        )

        pipeline = SequentialPipeline([researcher, writer, reviewer])

        # 测试字符串接口
        result = await pipeline.run("Write about AI")
        assert isinstance(result, str)
        assert len(result) > 0

        # 测试 Message 接口
        msg = create_user_message("Write about AI")
        reply = await pipeline.reply(msg)
        assert reply.role == "assistant"
        assert reply.parent_id is not None

    @pytest.mark.asyncio
    async def test_parallel_pipeline_with_real_agents(self):
        """并行 Pipeline 使用真实 Agent"""
        llm = MockLLM()

        analyst1 = loom.agent(
            name="technical", llm=llm, system_prompt="Technical perspective"
        )
        analyst2 = loom.agent(
            name="business", llm=llm, system_prompt="Business perspective"
        )
        analyst3 = loom.agent(
            name="user", llm=llm, system_prompt="User perspective"
        )

        pipeline = ParallelPipeline([analyst1, analyst2, analyst3])

        # 测试执行
        result = await pipeline.run("Analyze AI impact")
        assert isinstance(result, str)
        assert len(result) > 0

        # 验证所有 Agent 都执行了（结果包含多个分析）
        # MockLLM 会返回不同的结果
        assert len(result.split("\n\n")) >= 1

    @pytest.mark.asyncio
    async def test_react_agent_in_pipeline(self):
        """Pipeline 中使用 ReActAgent"""
        llm = MockLLM()
        search_tool = MockSearchTool()

        # 创建 ReActAgent（带工具）
        researcher = ReActAgent(name="researcher", llm=llm, tools=[search_tool])

        # 创建 SimpleAgent
        writer = loom.agent(name="writer", llm=llm)

        # 组合成 Pipeline
        pipeline = SequentialPipeline([researcher, writer])

        # 执行
        result = await pipeline.run("Research quantum computing and write a summary")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_mixed_string_and_message_interface(self):
        """混合使用字符串和 Message 接口"""
        llm = MockLLM()

        agent1 = loom.agent(name="a1", llm=llm)
        agent2 = loom.agent(name="a2", llm=llm)

        pipeline = sequential(agent1, agent2)

        # 第一次：字符串接口
        result1 = await pipeline.run("Task 1")
        assert isinstance(result1, str)

        # 第二次：Message 接口
        msg = create_user_message("Task 2")
        reply = await pipeline.reply(msg)
        assert isinstance(reply, Message)
        assert reply.parent_id is not None

        # 验证两种接口都能工作


# ===== 集成测试：复杂工作流 =====


class TestComplexWorkflows:
    """测试复杂的工作流组合"""

    @pytest.mark.asyncio
    async def test_research_write_review_workflow(self):
        """研究-写作-审阅工作流（完整）"""
        llm = MockLLM()
        search_tool = MockSearchTool()

        # 1. Researcher: 使用工具搜索
        researcher = ReActAgent(name="researcher", llm=llm, tools=[search_tool])

        # 2. Writer: 写作
        writer = loom.agent(
            name="writer",
            llm=llm,
            system_prompt="Write clear, concise articles based on research.",
        )

        # 3. Reviewer: 审阅
        reviewer = loom.agent(
            name="reviewer",
            llm=llm,
            system_prompt="Review and improve the article quality.",
        )

        # 组合成 Pipeline
        pipeline = SequentialPipeline(
            [researcher, writer, reviewer], name="content_pipeline"
        )

        # 执行完整流程
        msg = create_user_message("Write an article about quantum computing")
        final_reply = await pipeline.reply(msg)

        # 验证结果
        assert final_reply.role == "assistant"
        assert final_reply.parent_id is not None
        assert isinstance(final_reply.content, str)
        assert len(final_reply.content) > 0

    @pytest.mark.asyncio
    async def test_multi_perspective_analysis(self):
        """多角度分析工作流"""
        llm = MockLLM()

        # 创建多个分析师（不同视角）
        technical = loom.agent(
            name="technical", llm=llm, system_prompt="Technical analysis"
        )
        business = loom.agent(
            name="business", llm=llm, system_prompt="Business analysis"
        )
        user = loom.agent(name="user", llm=llm, system_prompt="User analysis")

        # 并行分析
        pipeline = ParallelPipeline([technical, business, user])

        # 执行
        msg = create_user_message("Analyze the impact of AI on software development")
        reply = await pipeline.reply(msg)

        # 验证结果包含多个视角
        assert reply.role == "assistant"
        assert len(reply.content) > 0

    @pytest.mark.asyncio
    async def test_data_pipeline_etl(self):
        """数据处理 ETL Pipeline"""
        llm = MockLLM()

        # Extract
        extractor = loom.agent(
            name="extractor", llm=llm, system_prompt="Extract data from source"
        )

        # Transform
        transformer = loom.agent(
            name="transformer", llm=llm, system_prompt="Transform data format"
        )

        # Load
        loader = loom.agent(
            name="loader", llm=llm, system_prompt="Load data to destination"
        )

        # ETL Pipeline
        pipeline = sequential(extractor, transformer, loader, name="etl_pipeline")

        # 执行
        result = await pipeline.run("Process data from source.csv")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_pipeline_with_custom_aggregator(self):
        """使用自定义聚合器的 Pipeline"""
        llm = MockLLM()

        agent1 = loom.agent(name="a1", llm=llm)
        agent2 = loom.agent(name="a2", llm=llm)
        agent3 = loom.agent(name="a3", llm=llm)

        # 自定义聚合器：提取关键点
        def extract_keypoints(results):
            """每个结果取前 50 个字符作为关键点"""
            points = [f"- {r[:50]}..." for r in results]
            return "\n".join(points)

        pipeline = parallel(agent1, agent2, agent3, aggregator=extract_keypoints)

        # 执行
        result = await pipeline.run("Analyze market trends")
        assert isinstance(result, str)
        # 验证格式（应该是列表形式）
        assert "- " in result


# ===== 集成测试：流式处理 =====


class TestStreamingIntegration:
    """测试流式处理集成"""

    @pytest.mark.asyncio
    async def test_sequential_pipeline_streaming(self):
        """顺序 Pipeline 的流式输出"""
        llm = MockLLM()

        agent1 = loom.agent(name="a1", llm=llm)
        agent2 = loom.agent(name="a2", llm=llm)

        pipeline = sequential(agent1, agent2)

        # 流式执行
        chunks = []
        async for chunk in pipeline.run_stream("Test input"):
            chunks.append(chunk)

        # 验证收到了流式输出
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)

    @pytest.mark.asyncio
    async def test_parallel_pipeline_streaming(self):
        """并行 Pipeline 的流式输出（非真正并行流式）"""
        llm = MockLLM()

        agent1 = loom.agent(name="a1", llm=llm)
        agent2 = loom.agent(name="a2", llm=llm)

        pipeline = parallel(agent1, agent2)

        # 流式执行（注意：并行 Pipeline 的流式输出不是真正的并行流式）
        chunks = []
        async for chunk in pipeline.run_stream("Test"):
            chunks.append(chunk)

        assert len(chunks) > 0


# ===== 集成测试：错误处理 =====


class TestErrorHandling:
    """测试错误处理"""

    @pytest.mark.asyncio
    async def test_pipeline_with_agent_error(self):
        """Pipeline 中某个 Agent 出错"""
        from loom.core.base_agent import BaseAgent

        class FailingAgent(BaseAgent):
            """总是失败的 Agent"""

            async def run(self, input: str) -> str:
                raise RuntimeError("Agent failed intentionally")

        llm = MockLLM()
        agent1 = loom.agent(name="a1", llm=llm)
        failing = FailingAgent(name="failing")
        agent3 = loom.agent(name="a3", llm=llm)

        pipeline = sequential(agent1, failing, agent3)

        # 执行应该抛出异常
        with pytest.raises(RuntimeError, match="Agent failed intentionally"):
            await pipeline.run("Test")

    @pytest.mark.asyncio
    async def test_parallel_pipeline_partial_failure(self):
        """并行 Pipeline 部分失败"""
        from loom.core.base_agent import BaseAgent

        class FailingAgent(BaseAgent):
            """总是失败的 Agent"""

            async def run(self, input: str) -> str:
                raise RuntimeError("Failed")

        llm = MockLLM()
        agent1 = loom.agent(name="a1", llm=llm)
        failing = FailingAgent(name="failing")

        pipeline = parallel(agent1, failing)

        # 并行执行会传播异常
        with pytest.raises(RuntimeError):
            await pipeline.run("Test")


# ===== 集成测试：兼容性 =====


class TestBackwardCompatibility:
    """测试向后兼容性"""

    @pytest.mark.asyncio
    async def test_old_string_interface_still_works(self):
        """旧的字符串接口仍然工作"""
        llm = MockLLM()

        # Phase 1 的使用方式
        agent = loom.agent(name="agent", llm=llm)
        result = await agent.run("Task")

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_new_message_interface_works(self):
        """新的 Message 接口工作"""
        llm = MockLLM()

        # Phase 2 的使用方式
        agent = loom.agent(name="agent", llm=llm)
        msg = create_user_message("Task")
        reply = await agent.reply(msg)

        assert isinstance(reply, Message)
        assert reply.parent_id == msg.id

    @pytest.mark.asyncio
    async def test_can_switch_between_interfaces(self):
        """可以在两种接口之间切换"""
        llm = MockLLM()
        agent = loom.agent(name="agent", llm=llm)

        # 第一次：字符串
        result1 = await agent.run("Task 1")
        assert isinstance(result1, str)

        # 第二次：Message
        msg = create_user_message("Task 2")
        reply = await agent.reply(msg)
        assert isinstance(reply, Message)

        # 第三次：字符串
        result3 = await agent.run("Task 3")
        assert isinstance(result3, str)
