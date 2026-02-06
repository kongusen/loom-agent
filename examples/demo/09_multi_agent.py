"""
09_multi_agent.py - 多 Agent 协作

演示：
- 多个 Agent 共享 EventBus
- Agent 间任务委派
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from loom.agent import Agent
from loom.events import EventBus
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def main():
    # 1. 创建共享的 EventBus
    event_bus = EventBus()

    # 2. 创建 LLM Provider（从环境变量获取配置）
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量")
        return

    config = LLMConfig(provider="openai", model=model, api_key=api_key, base_url=base_url)
    llm = OpenAIProvider(config)

    # 3. 创建多个 Agent，共享 EventBus
    agent_a = Agent.create(
        llm=llm,
        node_id="agent-a",
        event_bus=event_bus,
        system_prompt="你是助手 A。",
    )

    agent_b = Agent.create(
        llm=llm,
        node_id="agent-b",
        event_bus=event_bus,
        system_prompt="你是助手 B。",
    )

    print(f"Agent A: {agent_a.node_id}")
    print(f"Agent B: {agent_b.node_id}")
    print("两个 Agent 共享同一个 EventBus")

    # 4. 运行 Agent A
    result = await agent_a.run("你好！")
    print(f"Agent A 结果: {result}")


if __name__ == "__main__":
    asyncio.run(main())
