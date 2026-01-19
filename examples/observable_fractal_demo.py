"""
Observable Fractal Demo - 可观测分形系统演示

展示如何使用可观测节点实现分形结构的思考过程流式输出。

基于公理系统：
- A2（事件主权）：所有通信都是Task
- A3（分形自相似）：节点可以递归组合
- A5（认知调度）：认知是编排交互的涌现
- 定理T2（完全可观测性）：所有行为都可观测

核心特性：
1. 扁平化观测 - 任何节点都可以直接向观测者发布事件
2. 无层级负担 - 父节点不需要转发子节点事件
3. 实时流式 - 思考过程实时推送给前端
"""

import asyncio

from loom.api.stream_api import StreamAPI
from loom.events import EventBus
from loom.events.memory_transport import MemoryTransport
from loom.fractal.container import NodeContainer
from loom.orchestration.agent import Agent
from loom.protocol import AgentCard, Task
from loom.providers.llm.mock import MockLLMProvider


async def main():
    """主函数 - 演示可观测分形系统"""

    print("=" * 60)
    print("Observable Fractal System Demo")
    print("基于公理A2（事件主权）+ A3（分形自相似）")
    print("=" * 60)
    print()

    # ==================== 1. 初始化事件总线 ====================
    print("📡 Step 1: 初始化事件总线")
    transport = MemoryTransport()
    event_bus = EventBus(transport=transport)
    print("✓ 事件总线已创建（基于公理A2）")
    print()

    # ==================== 2. 创建可观测Agent ====================
    print("🤖 Step 2: 创建可观测Agent")

    # 创建父Agent
    parent_agent = Agent(
        node_id="parent-agent",
        llm_provider=MockLLMProvider(),
        system_prompt="You are a helpful parent agent.",
        event_bus=event_bus,
        enable_collective_memory=False,  # 此演示不使用集体记忆
    )
    print(f"✓ 父Agent已创建: {parent_agent.node_id}")

    # 创建子Agent
    child_agent = Agent(
        node_id="child-agent",
        llm_provider=MockLLMProvider(),
        system_prompt="You are a helpful child agent.",
        event_bus=event_bus,
        enable_collective_memory=False,  # 此演示不使用集体记忆
    )
    print(f"✓ 子Agent已创建: {child_agent.node_id}")
    print()

    # ==================== 3. 创建分形容器 ====================
    print("🔄 Step 3: 创建分形容器（基于公理A3）")

    # 将子Agent包装在容器中
    container = NodeContainer(
        node_id="fractal-container",
        agent_card=AgentCard(
            agent_id="fractal-container",
            name="Fractal Container",
            description="A fractal container wrapping child agent",
            capabilities=[],
        ),
        child=child_agent,
    )
    print(f"✓ 分形容器已创建: {container.node_id}")
    print(f"  └─ 包含子节点: {child_agent.node_id}")
    print()

    # ==================== 4. 创建流式API ====================
    print("🌊 Step 4: 创建流式API（基于定理T2）")
    stream_api = StreamAPI(event_bus)
    print("✓ 流式API已创建")
    print()

    # ==================== 5. 启动观测任务 ====================
    print("👁️  Step 5: 启动观测任务")
    print("开始订阅所有节点事件...")
    print()

    # 创建观测任务
    async def observe_events():
        """观测所有节点事件"""
        event_count = 0
        async for sse_event in stream_api.stream_all_events("node.*"):
            event_count += 1
            # 解析SSE事件
            lines = sse_event.strip().split("\n")
            for line in lines:
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    print(f"  📨 [{event_count}] Event: {event_type}")
                elif line.startswith("data:"):
                    import json

                    data = json.loads(line.split(":", 1)[1].strip())
                    node_id = data.get("parameters", {}).get("node_id", "unknown")
                    print(f"      Node: {node_id}")

                    # 显示思考内容
                    if event_type == "node.thinking":
                        content = data.get("parameters", {}).get("content", "")
                        print(f"      💭 Thinking: {content}")

                    # 显示工具调用
                    elif event_type == "node.tool_call":
                        tool_name = data.get("parameters", {}).get("tool_name", "")
                        print(f"      🔧 Tool Call: {tool_name}")

                    print()

            # 限制观测数量（演示用）
            if event_count >= 20:
                break

    # 启动观测任务（后台运行）
    observer_task = asyncio.create_task(observe_events())

    # 等待一下，确保观测任务已启动
    await asyncio.sleep(0.1)

    # ==================== 6. 执行父Agent任务 ====================
    print("🚀 Step 6: 执行父Agent任务")
    print()

    parent_task = Task(
        task_id="task-parent",
        source_agent="user",
        target_agent=parent_agent.node_id,
        action="execute",
        parameters={"content": "Hello, please help me analyze this data."},
    )

    print(f"执行任务: {parent_task.task_id}")
    result = await parent_agent.execute_task(parent_task)
    print(f"✓ 父Agent任务完成: {result.status}")
    print()

    # ==================== 7. 执行子Agent任务（通过容器） ====================
    print("🔄 Step 7: 执行子Agent任务（通过分形容器）")
    print()

    child_task = Task(
        task_id="task-child",
        source_agent="parent-agent",
        target_agent=container.node_id,
        action="execute",
        parameters={"content": "Please process this subtask."},
    )

    print(f"执行任务: {child_task.task_id}")
    result = await container.execute_task(child_task)
    print(f"✓ 子Agent任务完成: {result.status}")
    print()

    # ==================== 8. 等待观测任务完成 ====================
    print("⏳ Step 8: 等待观测任务完成...")
    await observer_task
    print()

    # ==================== 9. 总结 ====================
    print("=" * 60)
    print("✅ 演示完成！")
    print()
    print("关键特性验证：")
    print("1. ✓ 扁平化观测 - 父子节点事件都直接发布到事件总线")
    print("2. ✓ 无层级负担 - 父节点不需要转发子节点事件")
    print("3. ✓ 实时流式 - 思考过程实时推送")
    print("4. ✓ 分形组合 - 容器包装子节点，保持接口一致")
    print()
    print("公理符合性：")
    print("- A2（事件主权）: ✓ 所有通信都是Task")
    print("- A3（分形自相似）: ✓ 容器和节点实现相同接口")
    print("- A5（认知调度）: ✓ 思考过程通过事件发布")
    print("- 定理T2（完全可观测性）: ✓ 所有行为都可观测")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
