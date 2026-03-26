"""Demo 07: 场景组合 - L2 能力

展示场景包的组合和约束收窄。
"""

import asyncio
from loom.agent import Agent
from loom.providers.llm.openai import OpenAIProvider
from loom.types.scene import ScenePackage


async def main():
    provider = OpenAIProvider(api_key="your-key")
    agent = Agent(provider=provider)

    # 定义两个场景
    readonly = ScenePackage(
        id="readonly",
        tools=["read_file", "list_files", "search"],
        constraints={"write": False}
    )

    limited = ScenePackage(
        id="limited",
        tools=["read_file", "list_files", "write_file"],
        constraints={"max_file_size": 1000}
    )

    # 组合场景（约束收窄）
    combined = readonly + limited

    print("=== 场景组合 ===")
    print(f"工具白名单: {combined.tools}")  # 交集
    print(f"约束: {combined.constraints}")  # 布尔 AND, 数值 min


if __name__ == "__main__":
    asyncio.run(main())
