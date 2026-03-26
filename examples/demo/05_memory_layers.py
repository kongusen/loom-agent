"""Demo 05: 内存层级 - L1 能力

展示多层内存系统的使用。
"""

import asyncio
from loom.agent import Agent
from loom.providers.llm.openai import OpenAIProvider


async def main():
    provider = OpenAIProvider(api_key="your-key")
    agent = Agent(provider=provider)

    # 存储到不同层级
    await agent.memory_mgr.store("用户偏好", "喜欢简洁的代码", layer="L1")
    await agent.memory_mgr.store("项目信息", "使用 Python 3.11", layer="L2")

    print("=== 内存检索 ===")
    results = await agent.memory_mgr.retrieve("代码风格", top_k=2)
    for r in results:
        print(f"[{r.layer}] {r.content}")


if __name__ == "__main__":
    asyncio.run(main())
