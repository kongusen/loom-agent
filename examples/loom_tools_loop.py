import asyncio

from loom import Agent
from loom.builtin.llms import RuleLLM
from loom.builtin.compression import StructuredCompressor
from loom.builtin.tools import Calculator
from loom.builtin.memory import InMemoryMemory


async def main() -> None:
    agent = Agent(
        llm=RuleLLM(), tools=[Calculator()], memory=InMemoryMemory(), compressor=StructuredCompressor()
    )
    # 将触发工具调用：calculator(expression="10*5")
    result = await agent.run("请帮我计算 calc: 10*5")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
