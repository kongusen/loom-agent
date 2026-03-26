"""Demo 06: 技能系统

展示如何加载和使用技能。
"""

import asyncio
from loom.agent import Agent
from loom.providers.llm.openai import OpenAIProvider


async def main():
    provider = OpenAIProvider(api_key="your-key")
    agent = Agent(provider=provider)

    # 加载技能
    await agent.skill_registry.load_from_path("./skills")

    print("=== 可用技能 ===")
    for skill_id in agent.skill_registry.list_skills():
        skill = agent.skill_registry.get_skill(skill_id)
        print(f"- {skill_id}: {skill.description}")

    # 使用技能
    result = await agent.run("使用 translator 技能翻译: Hello World")
    print(f"\n结果: {result.content}")


if __name__ == "__main__":
    asyncio.run(main())
