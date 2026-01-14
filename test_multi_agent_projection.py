"""
测试多Agent上下文共享事件
"""
import asyncio
import os
from loom import LoomBuilder
from loom.llm import OpenAIProvider
from loom.kernel.core import UniversalEventBus, Dispatcher
from loom.protocol.cloudevents import CloudEvent

# 设置OpenAI凭证
os.environ["OPENAI_API_KEY"] = "sk-Fy6Y5WV5eugN61DhxH1AjI8th71OWfopqA2OCj5t93UIZ6aF"
os.environ["OPENAI_MODEL"] = "gpt-4o-mini"
os.environ["OPENAI_BASE_URL"] = "https://xiaoai.plus/v1"

# 上下文投影事件监听器
class ProjectionEventListener:
    """监听并显示上下文投影事件"""

    def __init__(self):
        self.projection_graph = {}  # parent -> [children]
        self.projection_data = []   # 投影记录

    async def on_projection_sent(self, event: CloudEvent):
        """处理投影发送事件"""
        data = event.data
        parent = data.get('parent_node')
        target = data.get('target_node')
        items = data.get('projected_items')
        has_plan = data.get('has_plan')
        facts = data.get('facts_count')

        print(f"📤 [{parent}] → [{target}]", flush=True)
        print(f"   投影项: {items} | 包含计划: {has_plan} | 事实数: {facts}", flush=True)

        # 记录投影关系
        if parent not in self.projection_graph:
            self.projection_graph[parent] = []
        self.projection_graph[parent].append(target)

        self.projection_data.append({
            'type': 'sent',
            'parent': parent,
            'target': target,
            'items': items
        })

    async def on_projection_received(self, event: CloudEvent):
        """处理投影接收事件"""
        data = event.data
        parent = data.get('parent_node')
        child = data.get('child_node')
        items = data.get('received_items')
        depth = data.get('depth')

        print(f"📥 [{child}] ← [{parent}]", flush=True)
        print(f"   接收项: {items} | 深度: {depth}", flush=True)

        self.projection_data.append({
            'type': 'received',
            'parent': parent,
            'child': child,
            'items': items
        })

    def visualize_graph(self):
        """可视化投影关系图"""
        print(f"\n{'='*60}")
        print("🌳 上下文投影关系图")
        print(f"{'='*60}")

        for parent, children in self.projection_graph.items():
            print(f"  {parent}")
            for child in children:
                print(f"    └─> {child}")

        print(f"\n📊 投影统计:")
        print(f"   总投影次数: {len(self.projection_data)}")
        print(f"   父节点数: {len(self.projection_graph)}")

async def test_multi_agent_projection():
    """测试多Agent上下文投影事件"""
    print("=" * 60)
    print("测试: 多Agent上下文共享事件")
    print("=" * 60)

    print("\n🔧 创建基础设施...")
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # 创建并注册投影事件监听器（使用通配符订阅）
    listener = ProjectionEventListener()
    await bus.subscribe("agent.context.projected/*", listener.on_projection_sent)
    await bus.subscribe("agent.context.projection_received/*", listener.on_projection_received)
    print("✅ 投影事件监听器已注册")

    # 创建Provider
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ["OPENAI_MODEL"],
        base_url=os.environ["OPENAI_BASE_URL"],
        stream=True
    )
    print(f"✅ Provider创建成功")

    # 测试场景：Crew模式 - 多个Agent协作
    print(f"\n{'='*60}")
    print(f"📋 测试场景: Crew协作模式")
    print(f"{'='*60}\n")

    # 创建Coordinator Agent
    coordinator = (LoomBuilder()
        .with_id('coordinator')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(
            role='Coordinator',
            system_prompt='You are a coordinator. Break down tasks and delegate to specialists.'
        )
        .build())
    print(f"✅ Coordinator创建成功\n")

    # 给coordinator一些上下文
    from loom.memory.types import MemoryUnit, MemoryTier, MemoryType

    # 添加一些重要事实到L4
    await coordinator.memory.add(MemoryUnit(
        content="Project Goal: Build an AI agent system with fractal architecture",
        tier=MemoryTier.L4_GLOBAL,
        type=MemoryType.FACT,
        importance=0.9
    ))

    await coordinator.memory.add(MemoryUnit(
        content="Key Requirement: Support multi-agent collaboration",
        tier=MemoryTier.L4_GLOBAL,
        type=MemoryType.FACT,
        importance=0.85
    ))

    # 添加计划到L2
    await coordinator.memory.add(MemoryUnit(
        content="Plan: 1) Design architecture 2) Implement core 3) Test system",
        tier=MemoryTier.L2_WORKING,
        type=MemoryType.PLAN,
        importance=0.8
    ))

    print("📝 已为Coordinator添加上下文（计划 + 事实）\n")

    # 创建子Agent（模拟思考过程，会触发投影）
    # 注意：_spawn_thought 是内部方法，这里我们直接测试投影机制
    # 实际使用中，投影会在Crew或分形委托时自动发生

    print("🔄 模拟创建子Agent（触发上下文投影）...\n")

    # 手动创建投影并发布事件（模拟_spawn_thought的行为）
    projection = await coordinator.memory.create_projection(
        instruction="Analyze the architecture design requirements"
    )

    units = projection.to_memory_units()

    # 发布投影事件
    await dispatcher.dispatch(CloudEvent.create(
        source="node/coordinator",
        type="agent.context.projected",
        data={
            "target_node": "specialist-1",
            "parent_node": "coordinator",
            "projected_items": len(units),
            "has_plan": projection.parent_plan is not None,
            "facts_count": len(projection.relevant_facts) if projection.relevant_facts else 0,
            "instruction_summary": "Analyze the architecture design requirements"
        }
    ))

    # 创建子Agent并应用投影
    specialist = (LoomBuilder()
        .with_id('specialist-1')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_agent(
            role='Architecture Specialist',
            system_prompt='You are an architecture specialist.'
        )
        .build())

    # 应用投影
    specialist._apply_projection(projection)

    # 发布接收事件
    await dispatcher.dispatch(CloudEvent.create(
        source="node/specialist-1",
        type="agent.context.projection_received",
        data={
            "parent_node": "coordinator",
            "child_node": "specialist-1",
            "received_items": len(units),
            "has_plan": projection.parent_plan is not None,
            "facts_count": len(projection.relevant_facts) if projection.relevant_facts else 0,
            "depth": 1
        }
    ))

    # 等待事件处理
    await asyncio.sleep(0.2)

    # 验证specialist收到了投影的上下文
    # 使用内部索引获取所有记忆单元
    specialist_memory = list(specialist.memory._id_index.values())
    print(f"\n✅ Specialist接收到的上下文项数: {len(specialist_memory)}")

    # 显示投影的内容
    print(f"\n📦 投影内容详情:")
    for unit in specialist_memory:
        content_str = str(unit.content)[:60]
        print(f"   - [{unit.tier.value}] {unit.type.value}: {content_str}...")

    # 可视化投影关系
    listener.visualize_graph()

    return listener

# 运行测试
if __name__ == "__main__":
    asyncio.run(test_multi_agent_projection())
    print("\n✅ 多Agent上下文共享事件测试完成\n")
