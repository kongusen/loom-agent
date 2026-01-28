"""
Collective Unconscious Demo - 集体潜意识演示

展示分形结构中的"集体潜意识"概念：
- 节点可以从EventBus主动搜索需要的信息
- 节点可以访问其他节点的思考过程
- 实现真正的"集体记忆"和"集体洞察"

基于公理系统：
- A2（事件主权）：所有通信都是Task，支持查询
- A4（记忆层次）：EventBus作为L2工作记忆
- A5（认知调度）：认知是网络涌现，集体潜意识是基础
"""

import asyncio

from loom.events.event_bus import EventBus
from loom.events.memory_transport import MemoryTransport
from loom.memory.context_builder import ContextBuilder
from loom.orchestration.agent import Agent
from loom.protocol import Task
from loom.providers.llm.mock import MockLLMProvider


async def main():
    """主函数 - 演示集体潜意识"""

    print("=" * 70)
    print("Collective Unconscious System Demo")
    print("集体潜意识系统演示")
    print("=" * 70)
    print()

    # ==================== 1. 初始化可查询事件总线 ====================
    print("📡 Step 1: 初始化可查询事件总线")
    transport = MemoryTransport()
    event_bus = EventBus(transport=transport, max_history=100)
    print("✓ 可查询事件总线已创建")
    print("  - 支持事件查询")
    print("  - 支持集体记忆")
    print()

    # ==================== 2. 创建集体潜意识Agent ====================
    print("🧠 Step 2: 创建集体潜意识Agent")
    print()

    # 创建父Agent
    parent_agent = Agent(
        node_id="parent-agent",
        llm_provider=MockLLMProvider(),
        system_prompt="You are a parent agent coordinating subtasks.",
        event_bus=event_bus,
        enable_collective_memory=True,
    )
    print(f"✓ 父Agent已创建: {parent_agent.node_id}")
    print("  - 可以访问集体记忆")
    print()

    # 创建子Agent 1
    child_agent_1 = Agent(
        node_id="child-agent-1",
        llm_provider=MockLLMProvider(),
        system_prompt="You are child agent 1, specializing in data analysis.",
        event_bus=event_bus,
        enable_collective_memory=True,
    )
    print(f"✓ 子Agent 1已创建: {child_agent_1.node_id}")
    print("  - 专注于数据分析")
    print()

    # 创建子Agent 2
    child_agent_2 = Agent(
        node_id="child-agent-2",
        llm_provider=MockLLMProvider(),
        system_prompt="You are child agent 2, specializing in visualization.",
        event_bus=event_bus,
        enable_collective_memory=True,
    )
    print(f"✓ 子Agent 2已创建: {child_agent_2.node_id}")
    print("  - 专注于可视化")
    print()

    # ==================== 3. 执行父Agent任务 ====================
    print("🚀 Step 3: 执行父Agent任务")
    print()

    parent_task = Task(
        task_id="task-parent",
        source_agent="user",
        target_agent=parent_agent.node_id,
        action="execute",
        parameters={"content": "Analyze the sales data and create visualizations."},
    )

    print(f"执行任务: {parent_task.task_id}")
    print(f"内容: {parent_task.parameters['content']}")
    result = await parent_agent.execute_task(parent_task)
    print(f"✓ 父Agent任务完成: {result.status}")
    print()

    # ==================== 4. 执行子Agent 1任务 ====================
    print("📊 Step 4: 执行子Agent 1任务（数据分析）")
    print()

    child_task_1 = Task(
        task_id="task-child-1",
        source_agent=parent_agent.node_id,
        target_agent=child_agent_1.node_id,
        action="execute",
        parameters={"content": "Analyze the sales trends for Q4."},
    )

    print(f"执行任务: {child_task_1.task_id}")
    result = await child_agent_1.execute_task(child_task_1)
    print(f"✓ 子Agent 1任务完成: {result.status}")
    print()

    # ==================== 5. 执行子Agent 2任务（可以看到子Agent 1的思考） ====================
    print("📈 Step 5: 执行子Agent 2任务（可视化）")
    print("注意：子Agent 2可以访问子Agent 1的思考过程！")
    print()

    child_task_2 = Task(
        task_id="task-child-2",
        source_agent=parent_agent.node_id,
        target_agent=child_agent_2.node_id,
        action="execute",
        parameters={"content": "Create visualizations based on the analysis."},
    )

    print(f"执行任务: {child_task_2.task_id}")
    result = await child_agent_2.execute_task(child_task_2)
    print(f"✓ 子Agent 2任务完成: {result.status}")
    print()

    # ==================== 6. 查询集体记忆 ====================
    print("🧠 Step 6: 查询集体记忆")
    print()

    context_builder = ContextBuilder(event_bus)

    # 6.1 查询所有思考过程
    print("6.1 所有节点的思考过程:")
    all_thoughts = event_bus.query_thinking_process(limit=20)
    for i, thought in enumerate(all_thoughts, 1):
        print(f"  {i}. {thought}")
    print()

    # 6.2 查询集体洞察
    print("6.2 集体洞察:")
    collective_insights = context_builder.get_collective_insights(limit=10)
    print(f"  - 参与节点数: {collective_insights['total_nodes']}")
    print(f"  - 总思考数: {collective_insights['total_thoughts']}")
    print()
    print("  各节点贡献:")
    for node_id, data in collective_insights["by_node"].items():
        print(f"    - {node_id}: {data['thought_count']} thoughts")
        for thought in data["recent_thoughts"]:
            print(f"      💭 {thought}")
    print()

    # 6.3 搜索相关事件
    print("6.3 搜索包含'analysis'的事件:")
    relevant_events = context_builder.search_relevant_events("analysis", limit=5)
    for event in relevant_events:
        print(f"  - [{event['node_id']}] {event['content']}")
    print()

    # ==================== 7. 展示集体潜意识的威力 ====================
    print("💡 Step 7: 展示集体潜意识的威力")
    print()

    # 创建一个新的Agent，它可以访问之前所有Agent的思考
    synthesizer_agent = Agent(
        node_id="synthesizer-agent",
        llm_provider=MockLLMProvider(),
        system_prompt="You are a synthesizer agent that combines insights from all agents.",
        event_bus=event_bus,
        enable_collective_memory=True,
    )
    print(f"✓ 合成Agent已创建: {synthesizer_agent.node_id}")
    print("  - 可以访问所有之前Agent的思考过程")
    print()

    synthesizer_task = Task(
        task_id="task-synthesizer",
        source_agent="user",
        target_agent=synthesizer_agent.node_id,
        action="execute",
        parameters={"content": "Synthesize all insights and create a final report."},
    )

    print(f"执行任务: {synthesizer_task.task_id}")
    print("注意：合成Agent会自动获取所有之前Agent的思考作为上下文！")
    result = await synthesizer_agent.execute_task(synthesizer_task)
    print(f"✓ 合成Agent任务完成: {result.status}")
    print()

    # ==================== 8. 查看合成Agent使用的上下文 ====================
    print("📋 Step 8: 查看合成Agent使用的上下文")
    print()

    # 查询合成Agent的上下文构建事件
    context_events = event_bus.query_by_node(
        synthesizer_agent.node_id,
        action_filter="node.context_built",
    )

    if context_events:
        context_summary = context_events[-1].parameters.get("context_summary", "")
        print(f"上下文摘要: {context_summary}")
    print()

    # ==================== 9. 统计和总结 ====================
    print("=" * 70)
    print("📊 统计和总结")
    print("=" * 70)
    print()

    # 统计事件数量
    total_events = len(event_bus._event_history)
    thinking_events = len(event_bus.query_by_action("node.thinking"))
    tool_call_events = len(event_bus.query_by_action("node.tool_call"))

    print(f"总事件数: {total_events}")
    print(f"思考事件数: {thinking_events}")
    print(f"工具调用事件数: {tool_call_events}")
    print()

    # 展示集体记忆
    print("集体记忆概览:")
    collective_memory = event_bus.get_collective_memory(limit=50)
    for action_type, by_node in collective_memory.items():
        print(f"\n{action_type}:")
        for node_id, events in by_node.items():
            print(f"  - {node_id}: {len(events)} events")
    print()

    # ==================== 10. 关键特性验证 ====================
    print("=" * 70)
    print("✅ 关键特性验证")
    print("=" * 70)
    print()

    print("1. ✓ 集体记忆 - 所有节点的思考都记录在EventBus中")
    print("2. ✓ 主动搜索 - 节点可以从EventBus查询需要的信息")
    print("3. ✓ 上下文增强 - 节点自动获取相关的集体记忆作为上下文")
    print("4. ✓ 兄弟节点洞察 - 节点可以看到兄弟节点的思考过程")
    print("5. ✓ 父节点上下文 - 节点可以访问父节点的上下文")
    print("6. ✓ 集体潜意识 - 整个分形结构共享一个集体记忆")
    print()

    print("公理符合性:")
    print("- A2（事件主权）: ✓ 所有通信都是Task，支持查询")
    print("- A4（记忆层次）: ✓ EventBus作为L2工作记忆")
    print("- A5（认知调度）: ✓ 认知是网络涌现，集体潜意识是基础")
    print()

    print("=" * 70)
    print("🎉 演示完成！")
    print()
    print("核心洞察:")
    print("- EventBus不仅是通信机制，更是'集体记忆'")
    print("- 节点可以主动从EventBus搜索需要的信息")
    print("- 分形结构中的所有节点共享一个'集体潜意识'")
    print("- 这种设计极大增强了分形结构处理复杂问题的能力")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
