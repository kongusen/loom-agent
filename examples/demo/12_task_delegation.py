"""
12_task_delegation.py - 任务委派

演示：
- 通过 EventBus 委派任务
- 父Agent委派给子Agent
- 任务结果回传
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from loom.agent import Agent
from loom.events import EventBus
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig
from loom.runtime import Task, TaskStatus

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def main():
    # 1. 创建共享 EventBus
    event_bus = EventBus()

    # 2. 创建 LLM Provider
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量")
        return

    config = LLMConfig(provider="openai", model=model, api_key=api_key, base_url=base_url)
    llm = OpenAIProvider(config)

    # 3. 创建工作Agent（子Agent）
    worker_agent = Agent.create(
        llm=llm,
        node_id="worker",
        event_bus=event_bus,
        system_prompt="你是一个专业的翻译助手，负责将中文翻译成英文。",
        max_iterations=3,
    )

    # 4. 注册工作Agent的任务处理器
    async def handle_worker_task(task: Task) -> Task:
        print(f"[Worker] 收到任务: {task.parameters.get('task', '')[:50]}...")
        result = await worker_agent.run(task.parameters.get("task", ""))
        task.status = TaskStatus.COMPLETED
        task.result = {"content": result}
        print(f"[Worker] 完成任务")
        return task

    event_bus.register_handler("execute", handle_worker_task)

    # 5. 创建主Agent（父Agent）
    main_agent = Agent.create(
        llm=llm,
        node_id="main",
        event_bus=event_bus,
        system_prompt="你是一个任务协调者。",
        max_iterations=3,
    )

    # 6. 委派任务
    print("=== 任务委派演示 ===\n")
    print("[Main] 委派翻译任务给 Worker...")

    delegation_result = await main_agent.delegate(
        subtask="请将以下内容翻译成英文：人工智能正在改变世界。",
        target_node_id="worker",
    )

    print(f"\n[Main] 收到结果: {delegation_result.result}")


if __name__ == "__main__":
    asyncio.run(main())
