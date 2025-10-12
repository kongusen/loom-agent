"""OpenAI Agent 示例 - 带工具调用的完整示例"""

import asyncio
import os

from loom import Agent
from loom.builtin.llms import OpenAILLM
from loom.builtin.memory import InMemoryMemory
from loom.builtin.tools import Calculator, ReadFileTool, WriteFileTool
from loom.builtin.compression import StructuredCompressor


async def main() -> None:
    # 从环境变量获取 API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        return

    # 创建 LLM
    llm = OpenAILLM(api_key=api_key, model="gpt-4", temperature=0.7)

    # 创建 Agent (带工具、内存、压缩)
    agent = Agent(
        llm=llm,
        tools=[Calculator(), ReadFileTool(), WriteFileTool()],
        memory=InMemoryMemory(),
        compressor=StructuredCompressor(llm=llm, threshold=0.92),
        max_iterations=10,
    )

    # 示例 1: 简单计算
    print("=== Example 1: Simple Calculation ===")
    result = await agent.run("What is 123 * 456?")
    print(f"Result: {result}\n")

    # 示例 2: 多步任务
    print("=== Example 2: Multi-Step Task ===")
    result = await agent.run(
        "Calculate 100 + 200, then write the result to a file called result.txt, "
        "and then read that file back to verify."
    )
    print(f"Result: {result}\n")

    # 示例 3: 流式输出
    print("=== Example 3: Streaming Output ===")
    async for event in agent.stream("Tell me a short joke and calculate 7 * 8"):
        if event.type == "text_delta":
            print(event.content, end="", flush=True)
        elif event.type == "tool_calls_start":
            print(f"\n[Calling tools: {[tc.name for tc in event.tool_calls]}]")
        elif event.type == "tool_result":
            print(f"[Tool result: {event.result.content[:50]}...]")
        elif event.type == "agent_finish":
            print("\n[Agent finished]")

    # 打印指标
    print("\n=== Metrics ===")
    metrics = agent.get_metrics()
    print(f"Total iterations: {metrics['total_iterations']}")
    print(f"LLM calls: {metrics['llm_calls']}")
    print(f"Tool calls: {metrics['tool_calls']}")


if __name__ == "__main__":
    asyncio.run(main())
