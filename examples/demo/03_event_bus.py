"""03 — EventBus：实时监控 Agent 执行过程，收集事件指标。"""

import asyncio

from _provider import create_provider

from loom import Agent, AgentConfig, EventBus, TextDeltaEvent


async def main():
    # ── 1. 创建带 EventBus 的 Agent ──
    bus = EventBus(node_id="monitor")
    metrics = {"text_deltas": 0, "steps": 0, "events": []}

    async def collect(e):
        metrics["events"].append(e.type)
        if isinstance(e, TextDeltaEvent):
            metrics["text_deltas"] += 1

    bus.on_all(collect)

    agent = Agent(
        provider=create_provider(),
        config=AgentConfig(system_prompt="你是助手", max_steps=3),
        event_bus=bus,
    )

    # ── 2. 运行 Agent，EventBus 实时采集 ──
    print("[Agent + EventBus] 实时监控 Agent 执行")
    result = await agent.run("用一句话解释什么是事件驱动架构")
    print(f"  回复: {result.content[:100]}")

    # ── 3. 查看采集到的指标 ──
    print("\n[监控指标]")
    print(f"  总事件数: {len(metrics['events'])}")
    print(f"  text_delta 数: {metrics['text_deltas']}")
    event_types = sorted(set(metrics["events"]))
    print(f"  事件类型: {event_types}")

    # ── 4. 父子传播 — 子 Agent 事件冒泡到父级 ──
    print("\n[父子传播]")
    parent_log = []
    parent = EventBus(node_id="parent")

    async def on_parent(e):
        parent_log.append(e.type)

    parent.on_all(on_parent)

    child_agent = Agent(
        provider=create_provider(),
        config=AgentConfig(max_steps=2),
        event_bus=parent.create_child("child"),
    )
    await child_agent.run("hi")
    print(f"  子 Agent 事件冒泡到父节点: {len(parent_log)} 个事件")


if __name__ == "__main__":
    asyncio.run(main())
