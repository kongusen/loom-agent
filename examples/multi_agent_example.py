"""Multi-Agent 系统示例"""

import asyncio
import os

from loom import Agent
from loom.builtin.llms import OpenAILLM
from loom.builtin.tools import Calculator, ReadFileTool, WriteFileTool
from loom.patterns import MultiAgentSystem


async def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        return

    # 创建专业 Agent
    researcher = Agent(
        llm=OpenAILLM(api_key=api_key, model="gpt-4", temperature=0.3),
        tools=[ReadFileTool()],
    )

    analyst = Agent(
        llm=OpenAILLM(api_key=api_key, model="gpt-4", temperature=0.5),
        tools=[Calculator()],
    )

    writer = Agent(
        llm=OpenAILLM(api_key=api_key, model="gpt-4", temperature=0.7),
        tools=[WriteFileTool()],
    )

    # 创建协调器
    coordinator = OpenAILLM(api_key=api_key, model="gpt-4", temperature=0.5)

    # 创建 Multi-Agent 系统
    system = MultiAgentSystem(
        agents={
            "researcher": researcher,
            "analyst": analyst,
            "writer": writer,
        },
        coordinator=coordinator,
    )

    # 执行复杂任务
    print("=== Multi-Agent Task Execution ===\n")

    task = (
        "Research information about Python programming, "
        "analyze its popularity trends, "
        "and write a summary report to 'python_report.txt'"
    )

    result = await system.run(task)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
