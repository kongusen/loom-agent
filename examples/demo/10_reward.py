"""10 — 奖励与生命周期：通过真实执行结果驱动 EMA 能力评估。"""

import asyncio
import time

from _provider import create_provider

from loom import Agent, AgentConfig, ClusterConfig, LifecycleManager, RewardBus
from loom.types import AgentNode, CapabilityProfile, RewardRecord, TaskAd


async def main():
    provider = create_provider()
    rb = RewardBus(alpha=0.3)
    lm = LifecycleManager(ClusterConfig(max_depth=3, mitosis_threshold=0.6))

    # ── 1. 真实执行 + 奖励反馈 ──
    print("[1] 真实执行 → 奖励反馈")
    node = AgentNode(
        id="coder",
        capabilities=CapabilityProfile(scores={"code": 0.5}),
        agent=Agent(
            provider=provider, config=AgentConfig(system_prompt="你是编程专家", max_steps=2)
        ),
        last_active_at=time.time(),
    )
    task = TaskAd(domain="code", token_budget=1000)

    result = await node.agent.run("用一行Python代码实现列表反转")
    success = len(result.content) > 10
    rb.evaluate(node, task, success=success, token_cost=100)
    print(f"  执行结果: {result.content[:80]}")
    print(f"  成功={success}, code能力: {node.capabilities.scores['code']:.3f}")

    # ── 2. EMA 收敛演示 ──
    print("\n[2] 连续成功 → EMA 收敛")
    for _ in range(5):
        rb.evaluate(node, task, success=True, token_cost=100)
    print(f"  5次成功后: code={node.capabilities.scores['code']:.3f}")

    # ── 3. 健康检查 ──
    print("\n[3] 健康检查")
    node.reward_history = [RewardRecord(reward=0.8, domain="code")]
    print(f"  状态: {lm.check_health(node).status}")


if __name__ == "__main__":
    asyncio.run(main())
