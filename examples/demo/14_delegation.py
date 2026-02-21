"""14 — 多 Agent 委派：父子 Agent 通过 DelegateHandler 路由任务。"""

import asyncio

from _provider import create_provider

from loom import Agent, AgentConfig, EventBus


async def main():
    bus = EventBus(node_id="root")
    provider = create_provider()

    # ── 1. 创建子 Agent ──
    researcher = Agent(
        provider=provider,
        name="researcher",
        config=AgentConfig(system_prompt="你是研究员", max_steps=2),
        event_bus=bus.create_child("researcher"),
    )
    writer = Agent(
        provider=provider,
        name="writer",
        config=AgentConfig(system_prompt="你是写作者", max_steps=2),
        event_bus=bus.create_child("writer"),
    )
    agents = {"research": researcher, "writing": writer}

    # ── 2. 创建协调者 + 委派处理器 ──
    async def delegate(task: str, domain: str) -> str:
        agent = agents.get(domain)
        if not agent:
            return f"未找到 {domain} 领域的 Agent"
        result = await agent.run(task)
        return result.content

    coordinator = Agent(
        provider=provider,
        name="coordinator",
        config=AgentConfig(system_prompt="你是协调者", max_steps=3),
        event_bus=bus,
    )
    coordinator.on_delegate = delegate

    # ── 3. 监听事件 ──
    events_log = []

    async def log_event(e):
        events_log.append(f"{e.type}")

    bus.on_all(log_event)

    # ── 4. 执行委派 ──
    print("[1] 直接委派到 researcher")
    r1 = await researcher.run("研究 AI Agent 记忆系统")
    print(f"  结果: {r1.content[:50]}")

    print("\n[2] 直接委派到 writer")
    r2 = await writer.run("撰写技术文章")
    print(f"  结果: {r2.content[:50]}")

    print("\n[3] 事件传播")
    print(f"  根节点收到 {len(events_log)} 个事件: {events_log[:5]}...")


if __name__ == "__main__":
    asyncio.run(main())
