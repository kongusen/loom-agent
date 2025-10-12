"""代码助手 Agent - 使用文件工具和 Python REPL"""

import asyncio
import os

from loom import Agent
from loom.builtin.llms import OpenAILLM
from loom.builtin.tools import Calculator, ReadFileTool, WriteFileTool, GlobTool, GrepTool

try:
    from loom.builtin.tools import PythonREPLTool

    has_repl = True
except ImportError:
    has_repl = False


async def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        return

    # 创建工具集
    tools = [
        Calculator(),
        ReadFileTool(),
        WriteFileTool(),
        GlobTool(),
        GrepTool(),
    ]

    if has_repl:
        tools.append(PythonREPLTool())

    # 创建代码助手
    code_agent = Agent(
        llm=OpenAILLM(api_key=api_key, model="gpt-4", temperature=0.3),
        tools=tools,
        max_iterations=15,
    )

    # 示例任务
    tasks = [
        # 任务 1: 代码生成
        "Create a Python script that calculates the factorial of a number and write it to factorial.py",
        # 任务 2: 代码分析
        "Read the factorial.py file, analyze it, and suggest improvements",
        # 任务 3: 搜索代码
        "Use glob to find all Python files in the current directory",
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n{'=' * 60}")
        print(f"Task {i}: {task}")
        print("=" * 60)

        result = await code_agent.run(task)
        print(f"\nResult:\n{result}")

        # 打印指标
        metrics = code_agent.get_metrics()
        print(f"\nMetrics: {metrics['tool_calls']} tool calls, {metrics['llm_calls']} LLM calls")


if __name__ == "__main__":
    asyncio.run(main())
