"""13 — AmoebaLoop：6 阶段自组织循环 (SENSE→MATCH→SCALE+EXECUTE→EVALUATE+ADAPT)。"""

import asyncio

from _provider import create_provider

from loom import ClusterConfig, ClusterManager, LifecycleManager, RewardBus
from loom.agent.strategy import LoopContext
from loom.cluster.amoeba_loop import AmoebaLoop
from loom.cluster.planner import TaskPlanner
from loom.cluster.skill_registry import SkillNodeRegistry
from loom.types import AgentNode, CapabilityProfile, UserMessage


async def main():
    provider = create_provider()

    cluster = ClusterManager()
    cluster.add_node(
        AgentNode(
            id="coder",
            capabilities=CapabilityProfile(scores={"code": 0.9}),
            agent=None,  # AmoebaLoop 会自行管理
        )
    )

    loop = AmoebaLoop(
        cluster=cluster,
        reward_bus=RewardBus(),
        lifecycle=LifecycleManager(ClusterConfig(max_depth=3)),
        planner=TaskPlanner(provider),
        skill_registry=SkillNodeRegistry(),
        llm=provider,
    )

    print("[AmoebaLoop 6 阶段]")
    print("  SENSE → MATCH → SCALE+EXECUTE → EVALUATE+ADAPT\n")

    # 构造一个简单的 LoopContext 来驱动循环
    from loom import Agent, AgentConfig

    agent = Agent(provider=provider, config=AgentConfig(max_steps=3))
    cluster.get_node("coder").agent = agent

    ctx = LoopContext(
        messages=[UserMessage(content="implement a sorting function")],
        provider=provider,
        tools=[],
        tool_registry=None,
        max_steps=3,
        streaming=False,
        temperature=0.7,
        max_tokens=4096,
        agent_id="coder",
    )

    async for event in loop.execute(ctx):
        t = getattr(event, "type", "")
        if t == "text_delta":
            print(f"  {event.text.strip()}")
        elif t == "done":
            print(f"\n  完成: steps={event.steps}, duration={event.duration_ms}ms")


if __name__ == "__main__":
    asyncio.run(main())
