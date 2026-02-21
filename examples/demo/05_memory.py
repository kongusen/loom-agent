"""05 — 记忆层级：Memory 让 Agent 具备多轮对话上下文能力。"""

import asyncio

from _provider import create_provider

from loom import Agent, AgentConfig, MemoryManager, SlidingWindow, WorkingMemory


async def main():
    provider = create_provider()

    # ── 1. 无记忆 Agent — 每轮独立，无法关联上下文 ──
    print("[1] 无记忆 Agent")
    agent1 = Agent(provider=provider, config=AgentConfig(max_steps=2))
    await agent1.run("我叫小明，我是一名Python开发者")
    r1 = await agent1.run("我叫什么名字？")
    print(f"  回复: {r1.content[:100]}")

    # ── 2. 有记忆 Agent — L1 滑动窗口保持对话连贯 ──
    print("\n[2] 有记忆 Agent (L1 滑动窗口 + L2 工作记忆)")
    memory = MemoryManager(
        l1=SlidingWindow(token_budget=2000),
        l2=WorkingMemory(token_budget=500),
    )
    agent2 = Agent(
        provider=provider,
        config=AgentConfig(max_steps=2),
        memory=memory,
    )
    await agent2.run("我叫小明，我是一名Python开发者")
    r2 = await agent2.run("我叫什么名字？我的职业是什么？")
    print(f"  回复: {r2.content[:150]}")

    # ── 3. 查看记忆状态 ──
    print("\n[记忆状态]")
    print(f"  L1 消息数: {len(memory.l1.get_messages())}")
    l2 = await memory.l2.retrieve()
    print(f"  L2 条目数: {len(l2)}")


if __name__ == "__main__":
    asyncio.run(main())
