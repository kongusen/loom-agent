"""Demo 03: 边界检测 - L2 能力

展示边界检测和响应机制。
"""

import asyncio
from loom.agent import Agent
from loom.providers.llm.openai import OpenAIProvider


async def main():
    provider = OpenAIProvider(api_key="your-key")
    agent = Agent(provider=provider)

    # 设置较小的资源配额
    agent.resource_guard._max_tokens = 5000

    print("=== 边界检测 ===")
    
    # 检查边界
    boundary = agent.boundary_detector.detect()
    if boundary:
        print(f"触发边界: {boundary[0]}")
    else:
        print("无边界触发")

    # 查看上下文压力
    decay = agent.partition_mgr.compute_decay()
    print(f"腐烂系数 ρ: {decay:.2f}")


if __name__ == "__main__":
    asyncio.run(main())
