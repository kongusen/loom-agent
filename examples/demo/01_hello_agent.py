"""01 — 基础 Agent：创建、运行、流式输出。"""

import asyncio

from _provider import create_provider

from loom import Agent, AgentConfig, DoneEvent, TextDeltaEvent


async def main():
    provider = create_provider()

    agent = Agent(
        provider=provider,
        config=AgentConfig(system_prompt="你是一个有帮助的助手。", max_steps=3),
        name="demo-agent",
    )

    # ── run(): 一次性获取结果 ──
    print("[run]")
    result = await agent.run("用一句话介绍 Python")
    print(f"  结果: {result.content}")
    print(f"  token: {result.usage.total_tokens}")

    # ── stream(): 逐 token 流式输出 ──
    print("\n[stream]")
    agent2 = Agent(provider=provider, name="stream-agent")
    async for event in agent2.stream("用一句话介绍 Rust"):
        if isinstance(event, TextDeltaEvent):
            print(event.text, end="", flush=True)
        elif isinstance(event, DoneEvent):
            print(f"\n  完成, steps={event.steps}")


if __name__ == "__main__":
    asyncio.run(main())
