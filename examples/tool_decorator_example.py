"""Showcase for @loom.tool decorator."""

import asyncio
import loom
from typing import List


@loom.tool(description="Sum a list of numbers")
def sum_list(nums: List[float]) -> float:
    return sum(nums)


async def main() -> None:
    agent = loom.agent(provider="openai", model="gpt-4o", tools=[sum_list()])
    print(await agent.ainvoke("Use sum_list to sum 1.5, 2.5, 3"))


if __name__ == "__main__":
    asyncio.run(main())

