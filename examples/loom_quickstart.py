import asyncio

from loom import Agent
from loom.builtin.llms import MockLLM
from loom.builtin.memory import InMemoryMemory
from loom.builtin.tools import Calculator


async def main() -> None:
    agent = Agent(llm=MockLLM(responses=["The answer is 42."]), tools=[Calculator()], memory=InMemoryMemory())
    print(await agent.run("What is the answer?"))


if __name__ == "__main__":
    asyncio.run(main())

