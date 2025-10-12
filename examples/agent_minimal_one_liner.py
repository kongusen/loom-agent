"""Minimal example using loom.agent one-liner."""

import asyncio
import loom
from loom.builtin.llms import MockLLM


async def main() -> None:
    agent = loom.agent(llm=MockLLM(responses=["Hello from Loom agent!"]))
    print(await agent.ainvoke("Say hello"))


if __name__ == "__main__":
    asyncio.run(main())

