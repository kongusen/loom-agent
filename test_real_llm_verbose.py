"""
使用真实LLM测试 - 详细输出版本
显示Agent的思考过程和工具调用细节
"""
import asyncio
import os
from loom import LoomBuilder
from loom.llm import OpenAIProvider
from loom.kernel.core import UniversalEventBus, Dispatcher
from loom.protocol.cloudevents import CloudEvent
from loom.node.tool import ToolNode
from loom.protocol.mcp import MCPToolDefinition

# 设置OpenAI凭证
os.environ["OPENAI_API_KEY"] = "sk-Fy6Y5WV5eugN61DhxH1AjI8th71OWfopqA2OCj5t93UIZ6aF"
os.environ["OPENAI_MODEL"] = "gpt-4o-mini"
os.environ["OPENAI_BASE_URL"] = "https://xiaoai.plus/v1"

# 事件监听器
class VerboseEventListener:
    """详细输出的事件监听器"""

    def __init__(self):
        self.iteration = 0

    async def on_event(self, event: CloudEvent):
        """处理所有事件"""
        event_type = event.type

        if event_type == "agent.tool.call":
            # 工具调用事件
            data = event.data or {}
            tool_name = data.get("tool", "unknown")
            args = data.get("arguments", {})
            print(f"\n🔧 [工具调用] {tool_name}")
            print(f"   参数: {args}")

        elif event_type == "agent.tool.result":
            # 工具结果事件
            data = event.data or {}
            tool_name = data.get("tool", "unknown")
            result = data.get("result", "")
            print(f"✅ [工具结果] {tool_name}")
            print(f"   返回: {result}")

print("=" * 60)
print("测试: 真实LLM + 详细输出")
print("=" * 60)

async def test_with_verbose_output():
    """带详细输出的测试"""
    print("\n🔧 创建基础设施...")
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)

    # 创建事件监听器
    listener = VerboseEventListener()

    # 注册事件监听器
    async def event_handler(event: CloudEvent):
        await listener.on_event(event)

    # 订阅所有agent相关事件
    await bus.subscribe("agent.tool.call", event_handler)
    await bus.subscribe("agent.tool.result", event_handler)

    print("✅ 事件监听器已注册")

    # 创建OpenAI Provider
    print("\n🔧 创建OpenAI Provider...")
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ["OPENAI_MODEL"],
        base_url=os.environ["OPENAI_BASE_URL"],
        stream=False
    )
    print(f"✅ Provider创建成功: {provider.config.generation.model}")

    # 创建工具
    print("\n🔧 创建计算器工具...")
    def calculator(operation: str, a: float, b: float) -> float:
        """计算器工具"""
        print(f"   💡 [工具执行] calculator({operation}, {a}, {b})")
        if operation == "add":
            result = a + b
        elif operation == "multiply":
            result = a * b
        elif operation == "subtract":
            result = a - b
        elif operation == "divide":
            result = a / b if b != 0 else "Error"
        else:
            result = "Unknown operation"
        print(f"   💡 [工具返回] {result}")
        return result

    tool_def = MCPToolDefinition(
        name="calculator",
        description="A calculator that performs basic arithmetic operations",
        inputSchema={
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["add", "multiply", "subtract", "divide"]},
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["operation", "a", "b"]
        }
    )

    tool_node = ToolNode(
        node_id="calculator-tool",
        dispatcher=dispatcher,
        tool_def=tool_def,
        func=calculator
    )
    print(f"✅ 工具节点创建成功: {tool_node.node_id}")

    # 创建Agent
    print("\n🔧 创建Agent...")
    agent = (LoomBuilder()
        .with_id('verbose-agent')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([tool_node])
        .with_agent(
            role='Math Assistant',
            system_prompt='You are a helpful math assistant. Use the calculator tool to perform calculations.'
        )
        .build())
    print(f"✅ Agent创建成功: {agent.node_id}")
    print(f"   已注册工具: {list(agent.known_tools.keys())}")

    # 执行测试
    print("\n" + "=" * 60)
    print("📨 发送问题: What is 123 multiplied by 456?")
    print("=" * 60)

    event = CloudEvent(
        type="node.request",
        source="user",
        data={"content": "What is 123 multiplied by 456? Please use the calculator tool."}
    )

    print("\n🤔 [Agent开始思考...]")
    result = await agent.process(event)

    print("\n" + "=" * 60)
    print("🤖 [最终响应]")
    print("=" * 60)
    print(result)


async def test_stage1_projection():
    """测试阶段1：投影优化（预算控制、语义相关性评分、模式检测）"""
    print("\n" + "=" * 80)
    print("🧪 阶段1测试：投影优化")
    print("=" * 80)

    from loom.memory.core import LoomMemory
    from loom.memory.types import MemoryUnit, MemoryTier, MemoryType
    from loom.projection.profiles import ProjectionMode

    # 创建LoomMemory
    print("\n🔧 创建LoomMemory...")
    memory = LoomMemory("test-agent")
    print("✅ LoomMemory创建成功")

    # 添加一些L4 facts
    print("\n📝 添加L4 facts...")
    facts = [
        "Python is a high-level programming language",
        "Machine learning is a subset of artificial intelligence",
        "Neural networks are inspired by biological neurons",
        "Deep learning uses multiple layers of neural networks",
        "Natural language processing deals with text and speech",
        "Computer vision enables machines to interpret images",
        "Reinforcement learning learns through trial and error",
        "Supervised learning uses labeled training data"
    ]

    for i, fact in enumerate(facts):
        await memory.add(MemoryUnit(
            content=fact,
            tier=MemoryTier.L4_GLOBAL,
            type=MemoryType.FACT,
            importance=0.7 + (i * 0.03)
        ))
    print(f"✅ 已添加 {len(facts)} 个facts到L4")

    # 添加一个计划到L2
    print("\n📋 添加计划到L2...")
    await memory.add(MemoryUnit(
        content="Plan: Research AI technologies and explain key concepts",
        tier=MemoryTier.L2_WORKING,
        type=MemoryType.PLAN,
        importance=0.9
    ))
    print("✅ 计划已添加")

    # 测试不同模式的投影
    test_cases = [
        ("Explain neural networks", "预期: ANALYTICAL模式"),
        ("Fix the error", "预期: DEBUG模式"),
        ("继续之前的讨论", "预期: CONTEXTUAL模式"),
        ("查询", "预期: MINIMAL模式"),
        ("Analyze machine learning algorithms", "预期: ANALYTICAL模式")
    ]

    print("\n" + "=" * 80)
    print("🔍 测试模式检测和投影")
    print("=" * 80)

    for instruction, expected in test_cases:
        print(f"\n📨 指令: '{instruction}'")
        print(f"   {expected}")

        # 检测模式
        detected_mode = memory._detect_mode(instruction)
        print(f"   ✅ 检测到模式: {detected_mode.value}")

        # 创建投影
        projection = await memory.create_projection(
            instruction=instruction,
            total_budget=2000
        )

        print(f"   📊 投影结果:")
        print(f"      - 指令: {projection.instruction}")
        print(f"      - 包含计划: {projection.parent_plan is not None}")
        print(f"      - 相关facts数量: {len(projection.relevant_facts) if projection.relevant_facts else 0}")

        if projection.relevant_facts:
            print(f"      - Top 3 facts:")
            for i, fact in enumerate(projection.relevant_facts[:3]):
                content_preview = str(fact.content)[:50]
                print(f"        {i+1}. {content_preview}... (重要性: {fact.importance:.2f})")

    print("\n✅ 阶段1测试完成")


async def test_stage2_l4_compression():
    """测试阶段2：L4压缩（聚类 + LLM总结）"""
    print("\n" + "=" * 80)
    print("🧪 阶段2测试：L4压缩")
    print("=" * 80)

    from loom.memory.core import LoomMemory
    from loom.memory.types import MemoryUnit, MemoryTier, MemoryType
    from loom.llm import OpenAIProvider

    # 创建Provider
    print("\n🔧 创建OpenAI Provider...")
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ["OPENAI_MODEL"],
        base_url=os.environ["OPENAI_BASE_URL"],
        stream=False
    )
    print(f"✅ Provider创建成功: {provider.config.generation.model}")

    # 创建LoomMemory
    print("\n🔧 创建LoomMemory...")
    memory = LoomMemory("test-agent")
    print("✅ LoomMemory创建成功")

    # 启用L4压缩（设置低阈值以便测试）
    print("\n🔧 启用L4压缩...")
    memory.enable_l4_compression(
        llm_provider=provider,
        threshold=10,  # 低阈值，方便测试
        similarity_threshold=0.75,
        min_cluster_size=3
    )
    print("✅ L4压缩已启用")
    print(f"   - 阈值: {memory.l4_compressor.threshold}")
    print(f"   - 相似度阈值: {memory.l4_compressor.similarity_threshold}")
    print(f"   - 最小聚类大小: {memory.l4_compressor.min_cluster_size}")

    # 添加相似的facts（会被聚类）
    print("\n📝 添加相似的facts到L4...")
    similar_facts = [
        # 关于Python的facts（应该被聚类）
        "Python is a high-level programming language",
        "Python was created by Guido van Rossum",
        "Python is widely used for data science",
        "Python has a simple and readable syntax",

        # 关于机器学习的facts（应该被聚类）
        "Machine learning is a subset of AI",
        "Machine learning algorithms learn from data",
        "Machine learning can be supervised or unsupervised",

        # 关于神经网络的facts（应该被聚类）
        "Neural networks are inspired by the brain",
        "Neural networks consist of layers of neurons",
        "Deep neural networks have many hidden layers",

        # 其他独立的facts
        "JavaScript is used for web development",
        "SQL is used for database queries"
    ]

    for i, fact in enumerate(similar_facts):
        await memory.add(MemoryUnit(
            content=fact,
            tier=MemoryTier.L4_GLOBAL,
            type=MemoryType.FACT,
            importance=0.7 + (i * 0.02)
        ))

    print(f"✅ 已添加 {len(similar_facts)} 个facts到L4")
    print(f"   当前L4大小: {len(memory._l4_global)}")

    # 检查是否需要压缩
    print("\n🔍 检查是否需要压缩...")
    should_compress = await memory.l4_compressor.should_compress(memory._l4_global)
    print(f"   需要压缩: {should_compress}")

    if should_compress:
        print("\n🗜️  开始L4压缩...")
        print(f"   压缩前: {len(memory._l4_global)} 个facts")

        # 执行压缩
        await memory._compress_l4()

        print(f"   压缩后: {len(memory._l4_global)} 个facts")
        print(f"   压缩率: {(1 - len(memory._l4_global) / len(similar_facts)) * 100:.1f}%")

        # 显示压缩后的facts
        print("\n📋 压缩后的facts:")
        for i, fact in enumerate(memory._l4_global):
            content_preview = str(fact.content)[:80]
            metadata = fact.metadata or {}
            compressed_from = metadata.get("compressed_from", 0)

            if compressed_from > 0:
                print(f"   {i+1}. [压缩自{compressed_from}个] {content_preview}...")
            else:
                print(f"   {i+1}. [原始] {content_preview}...")

    print("\n✅ 阶段2测试完成")


# 运行测试
asyncio.run(test_with_verbose_output())
print("\n✅ 基础测试完成")

print("\n" + "=" * 80)
asyncio.run(test_stage1_projection())
print("\n✅ 阶段1测试完成")

print("\n" + "=" * 80)
asyncio.run(test_stage2_l4_compression())
print("\n✅ 阶段2测试完成")

