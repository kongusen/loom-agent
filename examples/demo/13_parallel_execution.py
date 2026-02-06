"""
13_parallel_execution.py - 并行执行

演示：
- 使用 asyncio.gather 并行执行多个 Agent
- 使用 ParallelExecutor 进行框架级并行
- 结果合成
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from loom.agent import Agent
from loom.events import EventBus
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig
from loom.fractal import ParallelExecutor, ParallelTask, ParallelResult

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def main():
    # 1. 创建 LLM Provider
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量")
        return

    config = LLMConfig(provider="openai", model=model, api_key=api_key, base_url=base_url)
    llm = OpenAIProvider(config)

    print("=== 并行执行演示 ===\n")

    # ========== 方式1: 使用 asyncio.gather 简单并行 ==========
    print("--- 方式1: asyncio.gather 简单并行 ---\n")

    # 创建多个独立的 Agent
    agents = []
    tasks_content = [
        "用一句话介绍Python",
        "用一句话介绍JavaScript",
        "用一句话介绍Rust",
    ]

    for i, content in enumerate(tasks_content):
        agent = Agent.create(
            llm=llm,
            node_id=f"worker-{i}",
            system_prompt="你是一个编程语言专家，请简洁回答。",
            max_iterations=2,
        )
        agents.append((agent, content))

    # 并行执行
    print("并行执行 3 个任务...")
    start_time = asyncio.get_event_loop().time()

    results = await asyncio.gather(*[agent.run(content) for agent, content in agents])

    elapsed = asyncio.get_event_loop().time() - start_time
    print(f"完成! 耗时: {elapsed:.2f}s\n")

    for i, result in enumerate(results):
        print(f"[Agent-{i}] {result[:80]}...")

    # ========== 方式2: 使用 ParallelExecutor ==========
    print("\n--- 方式2: ParallelExecutor 框架级并行 ---\n")

    event_bus = EventBus()

    # 创建并行执行器
    executor = ParallelExecutor(
        event_bus=event_bus,
        max_concurrency=3,
    )

    # 定义并行任务
    parallel_tasks = [
        ParallelTask(task_id="task-1", content="什么是机器学习？一句话回答"),
        ParallelTask(task_id="task-2", content="什么是深度学习？一句话回答"),
        ParallelTask(task_id="task-3", content="什么是强化学习？一句话回答"),
    ]

    # Agent 工厂函数
    async def agent_factory(task: ParallelTask, child_bus: EventBus) -> str:
        agent = Agent.create(
            llm=llm,
            event_bus=child_bus,
            node_id=f"{task.task_id}:worker",
            system_prompt="你是AI专家，请简洁回答。",
            max_iterations=2,
        )
        return await agent.run(task.content)

    # 结果合成函数
    def synthesize_results(results: list[ParallelResult]) -> str:
        successful = [r for r in results if r.success]
        summary = f"成功完成 {len(successful)}/{len(results)} 个任务\n"
        for r in successful:
            summary += f"- {r.task_id}: {str(r.result)[:50]}...\n"
        return summary

    # 执行并合成
    print("并行执行 3 个 AI 任务...")
    results, synthesis = await executor.execute_and_synthesize(
        tasks=parallel_tasks,
        agent_factory=agent_factory,
        synthesizer=synthesize_results,
    )

    print("\n执行结果:")
    for r in results:
        status = "✓" if r.success else "✗"
        print(f"  [{status}] {r.task_id} ({r.duration:.2f}s)")

    print(f"\n合成摘要:\n{synthesis}")


if __name__ == "__main__":
    asyncio.run(main())
