"""
显式委托示例 (Explicit Delegation Demo)
展示如何使用 delegate_subtasks 工具进行任务分解和递归委托。
"""

import asyncio
from unittest.mock import AsyncMock

from loom.config.fractal import FractalConfig
from loom.infra.llm import MockLLMProvider
from loom.weave import create_agent


# 定义一个能"理解"委托指令的 Mock Provider
# 在真实场景中，这会是 GPT-4 或 Claude
class SmartMockProvider(MockLLMProvider):
    async def generate(self, prompt: str, **_kwargs) -> str:
        if "合成" in prompt or "Synthesize" in prompt:
            return "【综合报告】\n基于子任务结果，我们发现量子计算和核聚变都在快速发展..."
        return "I will execute this task."


async def main():
    print("🚀 启动显式委托演示...")

    # 1. 配置
    config = FractalConfig(
        enabled=True,
        enable_explicit_delegation=True,
        allow_recursive_delegation=True,
        max_recursive_depth=3,
        max_depth=3,
        synthesis_model="same_model",
    )

    # 2. 创建 Agent
    agent = create_agent(
        "research-lead",
        role="Research Coordinator",
        provider=SmartMockProvider(),
        fractal_config=config,
    )

    print(f"Agent {agent.node_id} 创建成功，工具列表: {list(agent.tool_registry._tools.keys())}")

    # 3. 模拟工具调用 (Programmatic Delegation)
    print("\n--- 场景 1: 程序化调用委托工具 ---")

    subtasks = [
        {
            "description": "研究量子计算硬件进展",
            "role": "specialist",
            "tools": ["web_search"],
            "max_tokens": 2000,
        },
        {"description": "研究量子算法应用", "role": "specialist", "max_tokens": 2000},
    ]

    # Manually call tool
    delegate_tool = agent.tool_registry.get_callable("delegate_subtasks")
    if delegate_tool:
        print("✅ 找到委托工具")
    # Mock 子节点执行，以避免真实的无限递归或复杂网络调用，只演示编排逻辑
    # 在真实运行中，orchestrator 会生成真实的 AgentNode 子节点
    # 这里我们 Hook 一下 orchestrator._execute_children 方便演示
    agent.orchestrator._execute_children = AsyncMock(
        return_value=[
            {"result": "量子硬件：超导量子比特取得突破...", "metadata": {}},
            {"result": "量子算法：Shor 算法有新优化...", "metadata": {}},
        ]
    )

    # Call the tool directly (it is an async function)
    result = await delegate_tool(
        subtasks=subtasks,
        execution_mode="sequential",
        synthesis_strategy="auto",
        reasoning="需要分步骤查询并汇总信息",
    )

    print(f"委托执行结果:\n{result}")

    print("\n--- 场景 2: 验证递归深度限制 ---")
    # 模拟在深度 2 的节点尝试委托 (配置允许深度 2，所以深度 0->1->2，深度 2 的节点能否继续？)
    # max_recursive_depth=2.
    # Root(0) -> Child(1) [OK] -> GrandChild(2) [OK] -> GreatGrand(3) [NO]

    spec = type("Spec", (), {"tools": None})()  # Mock object

    tools_depth_0 = agent.orchestrator._filter_tools_for_child(spec, 0)
    print(f"深度 0 子节点可用工具: {'delegate_subtasks' in tools_depth_0} (预期: True)")

    tools_depth_1 = agent.orchestrator._filter_tools_for_child(spec, 1)
    print(f"深度 1 子节点可用工具: {'delegate_subtasks' in tools_depth_1} (预期: True)")

    tools_depth_2 = agent.orchestrator._filter_tools_for_child(spec, 2)
    print(
        f"深度 2 子节点可用工具: {'delegate_subtasks' in tools_depth_2} (预期: False - 达到递归限制)"
    )

    print("\n✅ 演示完成")


if __name__ == "__main__":
    asyncio.run(main())
