"""
自主Agent演示

展示新的自主Agent架构，四范式能力自动使用。
"""

import asyncio

from loom.orchestration.agent import Agent
from loom.protocol import Task
from loom.providers.llm.interface import LLMProvider, LLMResponse, StreamChunk


class MockLLMProvider(LLMProvider):
    """模拟LLM提供者，用于演示"""

    async def chat(self, _messages: list[dict], **_kwargs) -> LLMResponse:
        """同步chat（不使用）"""
        return LLMResponse(content="Mock response")

    async def stream_chat(self, _messages: list[dict], **kwargs):
        """流式chat - 模拟LLM的自主决策"""
        tools = kwargs.get("tools", [])

        # 模拟LLM的思考过程（自动反思）
        yield StreamChunk(type="text", content="让我思考一下这个任务...")
        await asyncio.sleep(0.1)

        # 检查是否有create_plan工具（模拟复杂任务检测）
        has_plan_tool = any(t.get("function", {}).get("name") == "create_plan" for t in tools)

        if has_plan_tool:
            # 模拟LLM决定使用规划能力
            yield StreamChunk(type="text", content="这是一个复杂任务，我需要制定计划。")
            await asyncio.sleep(0.1)

            # 自动调用create_plan元工具
            yield StreamChunk(
                type="tool_call_complete",
                content={
                    "name": "create_plan",
                    "arguments": {
                        "goal": "完成复杂任务",
                        "steps": [
                            "步骤1：分析需求",
                            "步骤2：设计方案",
                            "步骤3：实施方案",
                            "步骤4：验证结果",
                        ],
                        "reasoning": "任务较为复杂，需要系统化的规划",
                    },
                },
            )
            await asyncio.sleep(0.1)

        # 继续思考（持续反思）
        yield StreamChunk(type="text", content="根据计划，我将逐步执行...")
        await asyncio.sleep(0.1)

        # 完成
        yield StreamChunk(
            type="done",
            content="",
            metadata={"token_usage": {"total": 100}},
        )


async def demo_autonomous_agent():
    """演示自主Agent的工作方式"""

    print("=" * 60)
    print("自主Agent演示 - 四范式自动能力")
    print("=" * 60)
    print()

    # 1. 创建自主Agent
    print("1. 创建自主Agent...")
    agent = Agent(
        node_id="demo-agent",
        llm_provider=MockLLMProvider(),
        system_prompt="你是一个自主智能体演示",
        tools=[],  # 可以添加普通工具
        available_agents={},  # 可以添加其他agent用于委派
    )
    print(f"   ✓ Agent创建成功: {agent.node_id}")
    print(f"   ✓ 工具数量: {len(agent.all_tools)} (包含元工具)")
    print()

    # 2. 执行任务 - Agent自动使用能力
    print("2. 执行任务（Agent自动决策使用能力）...")
    task = Task(
        task_id="demo-task-001",
        source_agent="user",
        target_agent=agent.node_id,
        action="execute",
        parameters={"content": "请帮我完成一个复杂的数据分析任务"},
    )

    result_task = await agent.execute_task(task)

    print(f"   ✓ 任务状态: {result_task.status.value}")
    print("   ✓ 任务结果:")
    print(f"      - 内容: {result_task.result.get('content', '')[:100]}...")
    print(f"      - 工具调用: {len(result_task.result.get('tool_calls', []))} 次")
    print()

    # 3. 展示自动能力
    print("3. 自动能力展示:")
    print("   ✓ 反思能力: 持续的思考过程（通过streaming体现）")
    print("   ✓ 工具使用: LLM自动决策调用工具")
    print("   ✓ 规划能力: 检测到复杂任务自动调用create_plan")
    print("   ✓ 协作能力: 需要时自动调用delegate_task")
    print()

    # 4. 统计信息
    print("4. Agent统计信息:")
    stats = agent.get_stats()
    print(f"   - 执行次数: {stats['execution_count']}")
    print(f"   - 成功次数: {stats['success_count']}")
    print(f"   - 成功率: {stats['success_rate']:.1%}")
    print()

    print("=" * 60)
    print("演示完成！")
    print("=" * 60)


async def demo_comparison():
    """对比旧架构和新架构"""

    print("\n" + "=" * 60)
    print("架构对比")
    print("=" * 60)
    print()

    print("旧架构（显式调用）:")
    print("```python")
    print("# 需要显式调用每个能力")
    print("result = await agent.reflect(content, task_id)")
    print("result = await agent.use_tool(tool_name, args, task_id)")
    print("result = await agent.plan(goal, task_id)")
    print("result = await agent.delegate(subtask, target, task_id)")
    print("```")
    print()

    print("新架构（自动决策）:")
    print("```python")
    print("# Agent自动使用所有能力")
    print("result = await agent.execute_task(task)")
    print("# LLM根据任务自动决定:")
    print("# - 持续反思（思考过程）")
    print("# - 自动使用工具（tool calling）")
    print("# - 自动规划（create_plan元工具）")
    print("# - 自动委派（delegate_task元工具）")
    print("```")
    print()

    print("核心优势:")
    print("✓ 真正的自主性 - Agent自己决策")
    print("✓ 分形自相似 - 每个节点都具备完整能力")
    print("✓ 简化API - 用户只需execute_task")
    print("✓ 可观测性 - 通过事件看到所有决策")
    print()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(demo_autonomous_agent())
    asyncio.run(demo_comparison())
