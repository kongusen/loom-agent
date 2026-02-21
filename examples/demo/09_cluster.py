"""09 — 集群拍卖：智能选择最佳 Agent 执行任务。"""

import asyncio

from _provider import create_provider

from loom import Agent, AgentConfig, ClusterConfig, ClusterManager
from loom.types import AgentNode, CapabilityProfile, TaskAd


async def main():
    provider = create_provider()
    cm = ClusterManager(ClusterConfig())

    # ── 1. 注册不同能力的节点 ──
    print("[1] 注册集群节点")
    coder = AgentNode(
        id="coder",
        capabilities=CapabilityProfile(scores={"code": 0.9, "data": 0.3}),
        agent=Agent(
            provider=provider, config=AgentConfig(system_prompt="你是编程专家", max_steps=3)
        ),
    )
    analyst = AgentNode(
        id="analyst",
        capabilities=CapabilityProfile(scores={"code": 0.3, "data": 0.9}),
        agent=Agent(
            provider=provider, config=AgentConfig(system_prompt="你是数据分析师", max_steps=3)
        ),
    )
    cm.add_node(coder)
    cm.add_node(analyst)

    # ── 2. 竞标选择最佳节点 ──
    task = TaskAd(domain="code", description="实现快速排序")
    winner = cm.select_winner(task)
    print(f"  代码任务 → 胜出: {winner.id}")

    task2 = TaskAd(domain="data", description="分析销售趋势")
    winner2 = cm.select_winner(task2)
    print(f"  数据任务 → 胜出: {winner2.id}")

    # ── 3. 胜出节点用真实 LLM 执行任务 ──
    print("\n[2] 胜出节点执行任务")
    result = await winner.agent.run("用Python实现快速排序，要求简洁")
    print(f"  {winner.id} 回复: {result.content[:150]}")


if __name__ == "__main__":
    asyncio.run(main())
