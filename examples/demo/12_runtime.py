"""12 — Runtime：集群编排、任务提交、自动委派。"""

import asyncio

from _provider import create_provider

from loom import AgentConfig, Runtime
from loom.types import CapabilityProfile, TaskAd


async def main():
    provider = create_provider()

    rt = Runtime(
        provider=provider,
        config=AgentConfig(system_prompt="你是助手", max_steps=3),
    )

    # ── 1. 添加节点 ──
    print("[1] 添加集群节点")
    rt.add_agent(capabilities=CapabilityProfile(scores={"code": 0.9}))
    rt.add_agent(capabilities=CapabilityProfile(scores={"data": 0.8}))
    print(f"  节点数: {len(rt.cluster.nodes)}")

    # ── 2. 提交任务 ──
    print("\n[2] 提交代码任务")
    result = await rt.submit(TaskAd(domain="code", description="实现排序算法"))
    print(f"  结果: {result[:60]}")

    print("\n[3] 提交数据任务")
    result2 = await rt.submit(TaskAd(domain="data", description="分析销售数据"))
    print(f"  结果: {result2[:60]}")

    # ── 3. 健康检查 ──
    print("\n[4] 健康检查")
    reports = rt.health_check()
    for r in reports:
        print(f"  {r.node_id}: {r.status}")

    rt.dispose()


if __name__ == "__main__":
    asyncio.run(main())
