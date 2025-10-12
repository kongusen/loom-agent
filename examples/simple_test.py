"""简单的 Loom 框架测试"""

import asyncio

from loom import Agent
from loom.builtin.llms import MockLLM, RuleLLM
from loom.builtin.memory import InMemoryMemory
from loom.builtin.tools import Calculator
from loom.builtin.compression import StructuredCompressor


async def main():
    print("=" * 60)
    print("Loom Framework - Simple Tests")
    print("=" * 60)
    print()

    # Test 1: 基础 Agent
    print("Test 1: Basic Agent")
    agent = Agent(llm=MockLLM(responses=["Hello from Loom!"]))
    result = await agent.run("Hi")
    print(f"✓ Result: {result}")
    print()

    # Test 2: 带工具的 Agent
    print("Test 2: Agent with Calculator")
    agent = Agent(llm=RuleLLM(), tools=[Calculator()])
    result = await agent.run("Calculate 100 + 200")
    print(f"✓ Result: {result}")
    print()

    # Test 3: 带内存的 Agent
    print("Test 3: Agent with Memory")
    memory = InMemoryMemory()
    agent = Agent(llm=MockLLM(responses=["Got it!", "You said hello"]), memory=memory)

    result1 = await agent.run("Hello")
    print(f"✓ Turn 1: {result1}")

    result2 = await agent.run("What did I say?")
    print(f"✓ Turn 2: {result2}")

    messages = await memory.get_messages()
    print(f"✓ Memory has {len(messages)} messages")
    print()

    # Test 4: 流式输出
    print("Test 4: Streaming")
    agent = Agent(llm=MockLLM(responses=["Streaming response"]))

    print("Events: ", end="")
    async for event in agent.stream("Test"):
        print(f"{event.type} ", end="", flush=True)
    print()
    print()

    # Test 5: 指标收集
    print("Test 5: Metrics")
    agent = Agent(llm=RuleLLM(), tools=[Calculator()])
    await agent.run("Test")
    metrics = agent.get_metrics()
    print(f"✓ Metrics: {metrics}")
    print()

    # Test 6: 压缩
    print("Test 6: Compression")
    memory = InMemoryMemory()
    compressor = StructuredCompressor()
    agent = Agent(
        llm=MockLLM(responses=["OK"]),
        memory=memory,
        compressor=compressor,
        max_context_tokens=10,  # 极低阈值
    )

    # 添加很多消息触发压缩
    from loom.core.types import Message

    for i in range(20):
        await memory.add_message(Message(role="user", content=f"Message {i}" * 100))

    result = await agent.run("Test compression")
    print(f"✓ Compression test completed")
    metrics = agent.get_metrics()
    print(f"✓ Metrics: {metrics}")
    print()

    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
