"""08 — Progressive Disclosure：Agent 按需加载技能，避免 context bloat。"""

import asyncio

from _provider import create_provider

from loom import Agent, AgentConfig, SkillRegistry, ToolRegistry
from loom.tools import create_skill_tool
from loom.types import Skill


async def main():
    provider = create_provider()

    # ── 1. 注册技能 ──
    registry = SkillRegistry()
    registry.register(
        Skill(
            name="python-expert",
            description="Python 编程专家，精通 asyncio 和最佳实践",
            instructions="你是资深 Python 专家。回答时使用类型提示、遵循 PEP 8、提供完整代码示例。",
        )
    )
    registry.register(
        Skill(
            name="code-reviewer",
            description="代码审查专家，关注质量、性能和安全",
            instructions="你是代码审查专家。检查：代码风格、性能问题、安全漏洞、错误处理。",
        )
    )
    print(f"已注册 {len(registry.all())} 个技能")

    # ── 2. Discovery：只注入轻量级列表 ──
    discovery = registry.get_discovery_prompt()
    system_prompt = "你是智能助手。需要时调用 Skill tool 加载完整指导。\n\n" + discovery
    print(f"System prompt 大小: {len(system_prompt)} 字符（轻量级）\n")

    # ── 3. 创建 Skill tool ──
    tools = ToolRegistry()
    tools.register(create_skill_tool(registry))

    # ── 4. Agent 按需加载技能 ──
    agent = Agent(provider, config=AgentConfig(system_prompt=system_prompt, max_steps=5), tools=tools)

    query = "用 Python asyncio 写一个并发爬虫"
    print(f"用户: {query}\n")
    result = await agent.run(query)
    print(f"\n回复: {result.content[:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
