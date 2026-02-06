"""
01_basic_agent.py - 基础 Agent 使用

演示：
- Agent.create() 创建 Agent
- agent.run() 执行任务
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def main():
    # 1. 创建 LLM Provider（从环境变量获取配置）
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量")
        return

    config = LLMConfig(
        provider="openai",
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
    llm = OpenAIProvider(config)

    # 2. 创建 Agent
    agent = Agent.create(
        llm=llm,
        system_prompt="你是一个有帮助的助手。",
        max_iterations=5,
    )

    # 3. 运行任务
    result = await agent.run("请用一句话介绍 Python 语言。")
    print(f"结果: {result}")


if __name__ == "__main__":
    asyncio.run(main())
