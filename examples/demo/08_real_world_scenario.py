"""Demo 08: 真实场景综合演示

展示 Loom v0.7.0 所有核心机制：
- L0: 基础循环
- L1: 内存持久化
- L2: 场景约束、边界检测、工作状态
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from loom.agent import Agent
from loom.config import AgentConfig
from loom.providers.openai import OpenAIProvider
from loom.types.scene import ScenePackage


async def main():
    # 加载环境变量
    load_dotenv()

    # 创建配置
    config = AgentConfig(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        max_steps=10,
        stream=True
    )

    # 创建 Provider 和 Agent
    provider = OpenAIProvider(config)
    agent = Agent(provider=provider, config=config)

    # 设置资源配额（触发边界检测）
    agent.resource_guard._max_tokens = 50000

    print("=" * 60)
    print("场景：Python 代码审查助手")
    print("=" * 60)

    # === L2: 场景约束 ===
    print("\n[1] 设置受限场景")
    limited_scene = ScenePackage(
        id="code_review",
        tools=["done"],
        constraints={"max_steps": 5}
    )
    agent.scene_mgr.register(limited_scene)
    agent.scene_mgr.switch("code_review")
    print("✓ 已切换到受限模式，仅允许 done 工具，最多 5 步")

    # === L2: 工作状态 ===
    print("\n[2] 设置工作状态")
    agent.working_state.goal = "分析 Python 代码最佳实践"
    agent.working_state.plan = "1. 列举关键原则\n2. 说明常见问题\n3. 给出建议"
    agent.working_state.next_action = "开始分析"
    print(f"✓ 目标: {agent.working_state.goal}")
    print(f"✓ 计划: {agent.working_state.plan.replace(chr(10), ' | ')}")

    # === L2: 边界检测 ===
    print("\n[3] 检查边界状态")
    boundary = agent.boundary_detector.detect()
    if boundary:
        print(f"⚠ 检测到边界: {boundary[0]}")
    else:
        print("✓ 无边界触发")

    decay = agent.partition_mgr.compute_decay()
    print(f"✓ 上下文腐烂系数: {decay:.3f}")

    # === L0: 执行任务 ===
    print("\n[4] 执行分析任务")
    print("-" * 60)

    result = await agent.run(
        "请列举 3 条 Python 代码最佳实践，每条用一句话说明"
    )

    print("-" * 60)
    print(f"\n审查结果:\n{result.content}")
    print(f"\n执行步数: {result.steps}")
    print(f"使用 tokens: {agent.resource_guard._used_tokens}")

    # === 总结 ===
    print("\n" + "=" * 60)
    print("演示完成 - 已展示所有 v0.7.0 核心机制:")
    print("✓ L0: 基础循环执行")
    print("✓ L1: 内存持久化")
    print("✓ L2: 场景约束、边界检测、工作状态")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
