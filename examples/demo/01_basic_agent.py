"""Demo 01: 基础 Agent - L0 能力

展示最简单的 Agent 使用。
"""

import asyncio
from loom.agent import Agent
from loom.config import AgentConfig
from loom.providers.llm.openai import OpenAIProvider


async def main():
    # 创建 Provider
    provider = OpenAIProvider(
        api_key="your-api-key",
        model="gpt-4"
    )

    # 创建 Agent
    agent = Agent(
        provider=provider,
        config=AgentConfig(
            max_steps=5,
            stream=True
        )
    )

    # 运行任务
    print("=== 基础对话 ===")
    result = await agent.run("你好，介绍一下你自己")
    print(f"\n结果: {result.content}")
    print(f"步数: {result.steps}")


if __name__ == "__main__":
    asyncio.run(main())
