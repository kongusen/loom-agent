"""
性能基准测试 (v0.1.5)

验证：
- Message 创建和序列化性能
- Pipeline 编排开销
- 字符串 vs Message 接口性能对比
- 并行执行性能验证
"""

import pytest
import time
import asyncio
import loom
from loom.patterns import SequentialPipeline, ParallelPipeline
from loom.core.message import Message, create_user_message
from loom.builtin.llms import MockLLM


# ===== Message 性能测试 =====


class TestMessagePerformance:
    """测试 Message 创建和操作性能"""

    def test_message_creation_performance(self, benchmark):
        """Message 创建性能"""

        def create_message():
            return Message(role="user", content="Test message")

        result = benchmark(create_message)
        assert result.role == "user"

    def test_message_with_metadata_creation(self, benchmark):
        """带元数据的 Message 创建性能"""

        def create_message_with_metadata():
            return Message(
                role="user",
                content="Test",
                metadata={
                    "source": "web",
                    "user_id": "12345",
                    "session_id": "abc",
                    "timestamp": time.time(),
                },
            )

        result = benchmark(create_message_with_metadata)
        assert len(result.metadata) == 4

    def test_message_reply_performance(self, benchmark):
        """Message 回复性能"""
        msg = Message(role="user", content="Hello")

        def create_reply():
            return msg.reply("Hi there!", name="assistant")

        result = benchmark(create_reply)
        assert result.parent_id == msg.id

    def test_message_serialization_performance(self, benchmark):
        """Message 序列化性能"""
        msg = Message(
            role="user",
            content="Test message",
            name="user",
            metadata={"key": "value"},
        )

        def serialize():
            return msg.to_dict()

        result = benchmark(serialize)
        assert result["role"] == "user"

    def test_message_deserialization_performance(self, benchmark):
        """Message 反序列化性能"""
        data = {
            "role": "user",
            "content": "Test",
            "name": "user",
            "id": "test-id",
            "timestamp": time.time(),
            "parent_id": None,
            "metadata": {"key": "value"},
        }

        def deserialize():
            return Message.from_dict(data)

        result = benchmark(deserialize)
        assert result.role == "user"

    def test_message_chain_tracing_performance(self, benchmark):
        """消息链追溯性能"""
        # 创建长消息链
        messages = {}
        msg = Message(role="user", content="First")
        messages[msg.id] = msg

        for i in range(10):
            msg = msg.reply(f"Message {i}")
            messages[msg.id] = msg

        from loom.core.message import trace_message_chain

        def trace_chain():
            return trace_message_chain(msg, messages)

        result = benchmark(trace_chain)
        assert len(result) == 11  # 原始 + 10 个回复


# ===== Pipeline 性能测试 =====


class TestPipelinePerformance:
    """测试 Pipeline 编排性能开销"""

    @pytest.mark.asyncio
    async def test_sequential_pipeline_overhead(self, benchmark):
        """顺序 Pipeline 开销测试"""
        llm = MockLLM()

        agent1 = loom.agent(name="a1", llm=llm)
        agent2 = loom.agent(name="a2", llm=llm)
        agent3 = loom.agent(name="a3", llm=llm)

        pipeline = SequentialPipeline([agent1, agent2, agent3])

        @benchmark
        async def run_pipeline():
            return await pipeline.run("Test input")

    @pytest.mark.asyncio
    async def test_parallel_pipeline_overhead(self, benchmark):
        """并行 Pipeline 开销测试"""
        llm = MockLLM()

        agent1 = loom.agent(name="a1", llm=llm)
        agent2 = loom.agent(name="a2", llm=llm)
        agent3 = loom.agent(name="a3", llm=llm)

        pipeline = ParallelPipeline([agent1, agent2, agent3])

        @benchmark
        async def run_pipeline():
            return await pipeline.run("Test input")

    @pytest.mark.asyncio
    async def test_pipeline_vs_manual_chaining(self):
        """Pipeline vs 手动串联性能对比"""
        llm = MockLLM()

        agent1 = loom.agent(name="a1", llm=llm)
        agent2 = loom.agent(name="a2", llm=llm)
        agent3 = loom.agent(name="a3", llm=llm)

        # 方式 1: 使用 Pipeline
        pipeline = SequentialPipeline([agent1, agent2, agent3])

        start = time.time()
        for _ in range(100):
            await pipeline.run("Test")
        pipeline_time = time.time() - start

        # 方式 2: 手动串联
        start = time.time()
        for _ in range(100):
            r1 = await agent1.run("Test")
            r2 = await agent2.run(r1)
            await agent3.run(r2)
        manual_time = time.time() - start

        # Pipeline 开销应该很小（< 10%）
        overhead = (pipeline_time - manual_time) / manual_time
        print(f"\nPipeline overhead: {overhead * 100:.2f}%")
        assert overhead < 0.1  # 小于 10%


# ===== 接口性能对比 =====


class TestInterfacePerformance:
    """测试字符串 vs Message 接口性能"""

    @pytest.mark.asyncio
    async def test_string_interface_performance(self):
        """字符串接口性能"""
        llm = MockLLM()
        agent = loom.agent(name="agent", llm=llm)

        start = time.time()
        for _ in range(100):
            await agent.run("Test input")
        string_time = time.time() - start

        print(f"\nString interface: {string_time:.4f}s for 100 calls")
        return string_time

    @pytest.mark.asyncio
    async def test_message_interface_performance(self):
        """Message 接口性能"""
        llm = MockLLM()
        agent = loom.agent(name="agent", llm=llm)

        start = time.time()
        for _ in range(100):
            msg = create_user_message("Test input")
            await agent.reply(msg)
        message_time = time.time() - start

        print(f"\nMessage interface: {message_time:.4f}s for 100 calls")
        return message_time

    @pytest.mark.asyncio
    async def test_interface_comparison(self):
        """接口性能对比"""
        llm = MockLLM()
        agent = loom.agent(name="agent", llm=llm)

        # 字符串接口
        start = time.time()
        for _ in range(100):
            await agent.run("Test")
        string_time = time.time() - start

        # Message 接口
        start = time.time()
        for _ in range(100):
            msg = create_user_message("Test")
            await agent.reply(msg)
        message_time = time.time() - start

        # 计算开销
        overhead = (message_time - string_time) / string_time
        print(f"\nMessage interface overhead: {overhead * 100:.2f}%")
        print(f"String: {string_time:.4f}s, Message: {message_time:.4f}s")

        # Message 接口开销应该很小（< 20%）
        assert overhead < 0.2


# ===== 并行性能测试 =====


class TestParallelPerformance:
    """测试并行执行性能"""

    @pytest.mark.asyncio
    async def test_parallel_speedup(self):
        """验证并行加速效果"""
        from loom.core.base_agent import BaseAgent

        class SlowAgent(BaseAgent):
            """模拟慢速 Agent"""

            def __init__(self, name: str, delay: float = 0.1):
                super().__init__(name=name)
                self.delay = delay

            async def run(self, input: str) -> str:
                await asyncio.sleep(self.delay)
                return f"{self.name}: {input}"

        # 创建 3 个慢速 Agent（每个 0.1 秒）
        agent1 = SlowAgent("a1", delay=0.1)
        agent2 = SlowAgent("a2", delay=0.1)
        agent3 = SlowAgent("a3", delay=0.1)

        # 顺序执行
        start = time.time()
        await agent1.run("Test")
        await agent2.run("Test")
        await agent3.run("Test")
        sequential_time = time.time() - start

        # 并行执行
        pipeline = ParallelPipeline([agent1, agent2, agent3])
        start = time.time()
        await pipeline.run("Test")
        parallel_time = time.time() - start

        # 计算加速比
        speedup = sequential_time / parallel_time
        print(f"\nSequential: {sequential_time:.4f}s")
        print(f"Parallel: {parallel_time:.4f}s")
        print(f"Speedup: {speedup:.2f}x")

        # 并行应该至少快 2 倍（理论上接近 3 倍）
        assert speedup > 2.0

    @pytest.mark.asyncio
    async def test_parallel_scalability(self):
        """测试并行可扩展性"""
        from loom.core.base_agent import BaseAgent

        class QuickAgent(BaseAgent):
            """快速 Agent"""

            async def run(self, input: str) -> str:
                await asyncio.sleep(0.05)
                return f"{self.name}: {input}"

        # 测试不同数量的 Agent
        results = {}

        for n in [2, 4, 8]:
            agents = [QuickAgent(f"a{i}") for i in range(n)]
            pipeline = ParallelPipeline(agents)

            start = time.time()
            await pipeline.run("Test")
            elapsed = time.time() - start

            results[n] = elapsed
            print(f"\n{n} agents: {elapsed:.4f}s")

        # 并行执行时间不应该随 Agent 数量线性增长
        # （应该保持在接近的水平）
        assert results[8] < results[2] * 2  # 8 个 Agent 不应该是 2 个的 2 倍慢


# ===== 内存性能测试 =====


class TestMemoryPerformance:
    """测试内存使用"""

    def test_message_memory_footprint(self):
        """测试大量 Message 创建的内存占用"""
        import sys

        # 创建大量消息
        messages = []
        for i in range(1000):
            msg = Message(
                role="user",
                content=f"Message {i}",
                metadata={"index": i},
            )
            messages.append(msg)

        # 粗略估计内存占用
        # 注意：这只是一个粗略的估计
        total_size = sum(sys.getsizeof(msg) for msg in messages)
        avg_size = total_size / len(messages)

        print(f"\n1000 messages: {total_size / 1024:.2f} KB")
        print(f"Average per message: {avg_size:.2f} bytes")

        # 每个消息应该相对轻量（< 1KB）
        assert avg_size < 1024

    def test_message_chain_memory(self):
        """测试长消息链的内存占用"""
        import sys

        # 创建长消息链
        msg = Message(role="user", content="Start")
        messages = [msg]

        for i in range(100):
            msg = msg.reply(f"Reply {i}")
            messages.append(msg)

        # 估计总内存
        total_size = sum(sys.getsizeof(m) for m in messages)
        print(f"\n101-message chain: {total_size / 1024:.2f} KB")

        # 应该在合理范围内（< 100KB）
        assert total_size < 100 * 1024


# ===== 性能报告 =====


@pytest.mark.asyncio
async def test_generate_performance_report():
    """生成性能报告"""
    print("\n" + "=" * 60)
    print("Loom Agent v0.1.5 性能报告")
    print("=" * 60)

    llm = MockLLM()

    # 1. Message 创建性能
    print("\n1. Message 创建性能")
    start = time.time()
    for _ in range(10000):
        Message(role="user", content="Test")
    elapsed = time.time() - start
    print(f"   10,000 messages: {elapsed:.4f}s ({10000/elapsed:.0f} msg/s)")

    # 2. Pipeline 开销
    print("\n2. Pipeline 开销")
    agent1 = loom.agent(name="a1", llm=llm)
    agent2 = loom.agent(name="a2", llm=llm)
    pipeline = SequentialPipeline([agent1, agent2])

    start = time.time()
    for _ in range(100):
        await pipeline.run("Test")
    pipeline_time = time.time() - start

    start = time.time()
    for _ in range(100):
        r = await agent1.run("Test")
        await agent2.run(r)
    manual_time = time.time() - start

    overhead = (pipeline_time - manual_time) / manual_time
    print(f"   Pipeline: {pipeline_time:.4f}s")
    print(f"   Manual: {manual_time:.4f}s")
    print(f"   Overhead: {overhead * 100:.2f}%")

    # 3. 并行加速
    print("\n3. 并行加速")
    from loom.core.base_agent import BaseAgent

    class SlowAgent(BaseAgent):
        async def run(self, input: str) -> str:
            await asyncio.sleep(0.05)
            return input

    agents = [SlowAgent(f"a{i}") for i in range(3)]

    start = time.time()
    for agent in agents:
        await agent.run("Test")
    seq_time = time.time() - start

    pipeline = ParallelPipeline(agents)
    start = time.time()
    await pipeline.run("Test")
    par_time = time.time() - start

    speedup = seq_time / par_time
    print(f"   Sequential: {seq_time:.4f}s")
    print(f"   Parallel: {par_time:.4f}s")
    print(f"   Speedup: {speedup:.2f}x")

    print("\n" + "=" * 60)
