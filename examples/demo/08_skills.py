"""08 — Skill 系统：根据用户输入自动激活技能，增强 Agent 专业能力。"""

import asyncio

from _provider import create_provider

from loom import Agent, AgentConfig, SkillRegistry
from loom.types import Skill, SkillTrigger


async def main():
    provider = create_provider()

    # ── 1. 定义技能 ──
    registry = SkillRegistry()
    registry.register(
        Skill(
            name="python-expert",
            trigger=SkillTrigger(type="keyword", keywords=["python", "pip", "asyncio"]),
            instructions="你是资深 Python 专家，回答要包含最佳实践和代码示例。",
            priority=0.9,
        )
    )
    registry.register(
        Skill(
            name="code-reviewer",
            trigger=SkillTrigger(type="pattern", pattern=r"\bdef\s+\w+|class\s+\w+"),
            instructions="你是代码审查专家，关注代码质量、性能和安全性。",
            priority=0.8,
        )
    )
    print(f"已注册技能: {[s.name for s in registry.all()]}")

    # ── 2. 自动激活匹配技能 ──
    query = "用 python asyncio 写一个并发爬虫"
    activations = await registry.activate(query)
    print(f"\n[技能匹配] '{query}'")
    for a in activations:
        print(f"  {a.skill.name}: score={a.score:.2f}")

    # ── 3. 用激活的技能增强 Agent ──
    print("\n[Agent + Skill] 技能增强对话")
    skill_prompt = "\n".join(a.skill.instructions for a in activations if a.skill.instructions)
    agent = Agent(
        provider=provider,
        config=AgentConfig(system_prompt=skill_prompt, max_steps=2),
    )
    result = await agent.run(query)
    print(f"  回复: {result.content[:200]}")


if __name__ == "__main__":
    asyncio.run(main())
