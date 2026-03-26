"""Demo 08: 真实场景综合演示

展示 Loom v0.7.0 所有核心机制：
- L0: 基础循环
- L1: 内存持久化、Skill 系统
- L2: 场景约束、边界检测、工作状态
- Tools: 自定义工具注册
- Knowledge: RAG 知识检索
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

from loom.agent import Agent
from loom.config import AgentConfig
from loom.providers.openai import OpenAIProvider
from loom.types import ToolDefinition, ToolContext, MemoryEntry
from loom.types.scene import ScenePackage
from loom.tools.schema import PydanticSchema


# 自定义工具：代码分析
class AnalyzeParams(BaseModel):
    code_type: str

async def analyze_code(params: AnalyzeParams, ctx: ToolContext) -> str:
    return f"分析 {params.code_type} 代码：建议使用类型注解、遵循 PEP8、编写测试"

analyze_tool = ToolDefinition(
    name="analyze_code",
    description="分析代码质量",
    parameters=PydanticSchema(AnalyzeParams),
    execute=analyze_code
)


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

    # === 注册自定义工具 ===
    agent.tools.register(analyze_tool)

    # 设置资源配额（触发边界检测）
    agent.resource_guard._max_tokens = 50000

    print("=" * 60)
    print("场景：Python 代码审查助手（完整演示）")
    print("=" * 60)

    # === L1: 内存系统 ===
    print("\n[1] 使用内存系统")
    # 添加消息到 L1 滑动窗口
    from loom.types import UserMessage
    await agent.memory.add_message(UserMessage(content="记住：优先使用类型注解"))
    print(f"✓ L1 历史消息数: {len(agent.memory.get_history())}")

    # 手动添加到 L2 工作记忆
    entry = MemoryEntry(
        content="Python 最佳实践：使用 dataclass、类型注解、文档字符串",
        tokens=20,
        importance=0.8
    )
    await agent.memory.l2.store(entry)
    print("✓ 已存储最佳实践到 L2 工作记忆")

    # === L2: 场景约束 ===
    print("\n[2] 设置场景约束")
    limited_scene = ScenePackage(
        id="code_review",
        tools=["done", "analyze_code"],
        constraints={"max_steps": 5}
    )
    agent.scene_mgr.register(limited_scene)
    agent.scene_mgr.switch("code_review")
    print("✓ 已切换到受限模式，允许 done 和 analyze_code 工具")

    # === L2: 工作状态 ===
    print("\n[3] 设置工作状态")
    agent.working_state.goal = "分析 Python 代码最佳实践"
    agent.working_state.plan = "1. 列举关键原则\n2. 说明常见问题\n3. 给出建议"
    agent.working_state.next_action = "开始分析"
    print(f"✓ 目标: {agent.working_state.goal}")
    print(f"✓ 计划: {agent.working_state.plan.replace(chr(10), ' | ')}")

    # === L2: 边界检测 ===
    print("\n[4] 检查边界状态")
    boundary = agent.boundary_detector.detect()
    if boundary:
        print(f"⚠ 检测到边界: {boundary[0]}")
    else:
        print("✓ 无边界触发")

    decay = agent.partition_mgr.compute_decay()
    print(f"✓ 上下文腐烂系数: {decay:.3f}")

    # === L0: 执行任务 ===
    print("\n[5] 执行分析任务（使用自定义工具）")
    print("-" * 60)

    result = await agent.run(
        "使用 analyze_code 工具分析 Python 代码"
    )

    print("-" * 60)
    print(f"\n结果:\n{result.content}")
    print(f"\n执行步数: {result.steps}")
    print(f"使用 tokens: {agent.resource_guard._used_tokens}")

    # === 总结 ===
    print("\n" + "=" * 60)
    print("演示完成 - 已展示所有 v0.7.0 核心机制:")
    print("✓ L0: 基础循环执行")
    print("✓ L1: 内存系统 (L1/L2 层级)")
    print("✓ L2: 场景约束、边界检测、工作状态")
    print("✓ Tools: 自定义工具注册和使用")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
