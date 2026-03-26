"""Demo 02: 场景约束 - L2 能力

展示如何使用场景包限制 Agent 行为。
"""

import asyncio
from loom.agent import Agent
from loom.providers.llm.openai import OpenAIProvider
from loom.types.scene import ScenePackage


async def main():
    provider = OpenAIProvider(api_key="your-key")
    agent = Agent(provider=provider)

    # 定义只读场景
    readonly = ScenePackage(
        id="readonly",
        tools=["read_file", "list_files"],
        constraints={"write": False, "bash": False}
    )

    agent.scene_mgr.register(readonly)
    agent.scene_mgr.switch("readonly")

    print("=== 只读模式 ===")
    result = await agent.run("读取 README.md")
    print(result.content)


if __name__ == "__main__":
    asyncio.run(main())
