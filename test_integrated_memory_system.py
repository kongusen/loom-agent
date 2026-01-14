"""
集成测试：完整的记忆系统测试
测试阶段一（投影优化）和阶段二（L4压缩）的集成

场景：AI知识库助手
- 助手学习各种技术知识（积累L4 facts）
- 用户提出不同类型的问题（触发不同投影模式）
- 自动触发L4压缩（当facts超过阈值）
- 验证压缩后仍能正确回答问题
"""
import asyncio
import os

# 禁用tokenizers并行化警告
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from loom import LoomBuilder
from loom.llm import OpenAIProvider
from loom.kernel.core import UniversalEventBus, Dispatcher
from loom.protocol.cloudevents import CloudEvent
from loom.node.tool import ToolNode
from loom.protocol.mcp import MCPToolDefinition
from loom.memory.core import LoomMemory
from loom.memory.types import MemoryUnit, MemoryTier, MemoryType
from loom.projection.profiles import ProjectionMode

# 设置OpenAI凭证
os.environ["OPENAI_API_KEY"] = "sk-Fy6Y5WV5eugN61DhxH1AjI8th71OWfopqA2OCj5t93UIZ6aF"
os.environ["OPENAI_MODEL"] = "gpt-4o-mini"
os.environ["OPENAI_BASE_URL"] = "https://xiaoai.plus/v1"


class TestMonitor:
    """测试监控器 - 记录和验证测试过程"""

    def __init__(self):
        self.events = []
        self.l4_size_history = []
        self.projection_history = []
        self.compression_triggered = False

    def log_event(self, event_type: str, data: dict):
        """记录事件"""
        self.events.append({
            "type": event_type,
            "data": data
        })

    def log_l4_size(self, size: int):
        """记录L4大小"""
        self.l4_size_history.append(size)

    def log_projection(self, mode: str, facts_count: int):
        """记录投影信息"""
        self.projection_history.append({
            "mode": mode,
            "facts_count": facts_count
        })

    def mark_compression(self):
        """标记压缩已触发"""
        self.compression_triggered = True

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 80)
        print("📊 测试摘要")
        print("=" * 80)
        print(f"总事件数: {len(self.events)}")
        print(f"L4大小变化: {self.l4_size_history}")
        print(f"投影次数: {len(self.projection_history)}")
        print(f"压缩触发: {'✅ 是' if self.compression_triggered else '❌ 否'}")
        print("\n投影历史:")
        for i, proj in enumerate(self.projection_history):
            print(f"  {i+1}. 模式: {proj['mode']}, Facts数量: {proj['facts_count']}")


# 知识库数据 - 分为多个主题
KNOWLEDGE_BASE = {
    "python": [
        "Python is a high-level, interpreted programming language",
        "Python was created by Guido van Rossum in 1991",
        "Python supports multiple programming paradigms",
        "Python has a simple and readable syntax",
        "Python is widely used for web development",
        "Python is popular in data science and machine learning",
        "Python has a large standard library",
        "Python uses dynamic typing",
    ],
    "machine_learning": [
        "Machine learning is a subset of artificial intelligence",
        "Machine learning algorithms learn from data",
        "Supervised learning uses labeled training data",
        "Unsupervised learning finds patterns in unlabeled data",
        "Reinforcement learning learns through trial and error",
        "Deep learning uses neural networks with multiple layers",
        "Neural networks are inspired by biological neurons",
        "Gradient descent is used to optimize neural networks",
    ],
    "web_development": [
        "HTML is the standard markup language for web pages",
        "CSS is used for styling web pages",
        "JavaScript is the programming language of the web",
        "React is a popular JavaScript library for building UIs",
        "Node.js allows JavaScript to run on the server",
        "REST APIs use HTTP methods for communication",
        "GraphQL is an alternative to REST APIs",
        "WebSockets enable real-time bidirectional communication",
    ],
    "databases": [
        "SQL is a language for managing relational databases",
        "NoSQL databases are designed for specific data models",
        "MongoDB is a popular document-oriented database",
        "Redis is an in-memory key-value store",
        "PostgreSQL is an advanced open-source relational database",
        "Database indexing improves query performance",
        "ACID properties ensure database transaction reliability",
        "Database normalization reduces data redundancy",
    ]
}


async def setup_infrastructure():
    """设置基础设施：事件总线、调度器、LLM提供者"""
    print("\n" + "=" * 80)
    print("🔧 阶段0：设置基础设施")
    print("=" * 80)

    # 创建事件总线和调度器
    bus = UniversalEventBus()
    dispatcher = Dispatcher(bus)
    print("✅ 事件总线和调度器已创建")

    # 创建OpenAI Provider
    provider = OpenAIProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.environ["OPENAI_MODEL"],
        base_url=os.environ["OPENAI_BASE_URL"],
        stream=False
    )
    print(f"✅ LLM Provider已创建: {provider.config.generation.model}")

    # 创建测试监控器
    monitor = TestMonitor()
    print("✅ 测试监控器已创建")

    return bus, dispatcher, provider, monitor


async def create_knowledge_tool():
    """创建知识查询工具"""
    def search_knowledge(topic: str, query: str) -> str:
        """搜索知识库"""
        if topic in KNOWLEDGE_BASE:
            results = [fact for fact in KNOWLEDGE_BASE[topic] if query.lower() in fact.lower()]
            if results:
                return f"Found {len(results)} results: " + "; ".join(results[:3])
            return f"No results found for '{query}' in {topic}"
        return f"Topic '{topic}' not found"

    tool_def = MCPToolDefinition(
        name="search_knowledge",
        description="Search the knowledge base for information on a specific topic",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "enum": ["python", "machine_learning", "web_development", "databases"],
                    "description": "The topic to search in"
                },
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["topic", "query"]
        }
    )

    return tool_def, search_knowledge


async def stage1_populate_l4(memory: LoomMemory, monitor: TestMonitor):
    """阶段1：填充L4知识库"""
    print("\n" + "=" * 80)
    print("📚 阶段1：填充L4知识库")
    print("=" * 80)

    total_facts = 0
    for topic, facts in KNOWLEDGE_BASE.items():
        print(f"\n添加 {topic} 知识...")
        for i, fact in enumerate(facts):
            await memory.add(MemoryUnit(
                content=fact,
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=0.7 + (i * 0.03),
                metadata={"topic": topic}
            ))
            total_facts += 1

        current_size = len(memory._l4_global)
        monitor.log_l4_size(current_size)
        print(f"   ✅ 已添加 {len(facts)} 个facts，当前L4总数: {current_size}")

    print(f"\n✅ 阶段1完成：共添加 {total_facts} 个facts到L4")
    return total_facts


async def stage2_test_projection_modes(memory: LoomMemory, monitor: TestMonitor):
    """阶段2：测试投影优化（不同模式）"""
    print("\n" + "=" * 80)
    print("🔍 阶段2：测试投影优化")
    print("=" * 80)

    # 测试用例：不同类型的指令
    test_cases = [
        ("查询", "minimal", "简短查询"),
        ("Analyze neural networks in detail", "analytical", "分析性任务"),
        ("Fix the error in the code", "debug", "调试任务"),
        ("继续之前的讨论", "contextual", "上下文相关"),
        ("Process user data and generate report", "standard", "标准任务"),
    ]

    for instruction, expected_mode, description in test_cases:
        print(f"\n📝 测试: {description}")
        print(f"   指令: '{instruction}'")
        print(f"   预期模式: {expected_mode}")

        # 检测模式
        detected_mode = memory._detect_mode(instruction)
        print(f"   ✅ 检测到模式: {detected_mode.value}")

        # 创建投影
        projection = await memory.create_projection(
            instruction=instruction,
            total_budget=2000
        )

        facts_count = len(projection.relevant_facts) if projection.relevant_facts else 0
        print(f"   📊 选择的facts数量: {facts_count}")

        # 记录到监控器
        monitor.log_projection(detected_mode.value, facts_count)

        # 验证模式是否正确
        if detected_mode.value == expected_mode:
            print(f"   ✅ 模式检测正确")
        else:
            print(f"   ⚠️  模式检测不匹配（预期: {expected_mode}, 实际: {detected_mode.value}）")

    print(f"\n✅ 阶段2完成：测试了 {len(test_cases)} 个投影模式")


async def stage3_trigger_l4_compression(memory: LoomMemory, provider, monitor: TestMonitor):
    """阶段3：触发L4压缩"""
    print("\n" + "=" * 80)
    print("🗜️  阶段3：触发L4压缩")
    print("=" * 80)

    # 检查当前L4大小
    current_size = len(memory._l4_global)
    print(f"\n当前L4大小: {current_size} facts")

    # 启用L4压缩（设置低阈值以便测试）
    print("\n🔧 启用L4压缩...")
    memory.enable_l4_compression(
        llm_provider=provider,
        threshold=20,  # 低阈值，方便触发
        similarity_threshold=0.75,
        min_cluster_size=3
    )
    print(f"✅ L4压缩已启用")
    print(f"   - 阈值: {memory.l4_compressor.threshold}")
    print(f"   - 相似度阈值: {memory.l4_compressor.similarity_threshold}")
    print(f"   - 最小聚类大小: {memory.l4_compressor.min_cluster_size}")

    # 检查是否需要压缩
    should_compress = await memory.l4_compressor.should_compress(memory._l4_global)
    print(f"\n需要压缩: {should_compress}")

    if should_compress:
        print(f"\n🗜️  开始L4压缩...")
        print(f"   压缩前: {len(memory._l4_global)} 个facts")

        # 执行压缩
        await memory._compress_l4()
        monitor.mark_compression()

        print(f"   压缩后: {len(memory._l4_global)} 个facts")
        compression_rate = (1 - len(memory._l4_global) / current_size) * 100
        print(f"   压缩率: {compression_rate:.1f}%")

        monitor.log_l4_size(len(memory._l4_global))
    else:
        print("⚠️  L4大小未超过阈值，未触发压缩")

    print(f"\n✅ 阶段3完成")


async def stage4_test_agent_with_memory(bus, dispatcher, provider, memory, monitor):
    """阶段4：测试Agent使用压缩后的记忆"""
    print("\n" + "=" * 80)
    print("🤖 阶段4：测试Agent使用压缩后的记忆")
    print("=" * 80)

    # 创建工具
    tool_def, search_func = await create_knowledge_tool()
    tool_node = ToolNode(
        node_id="knowledge-tool",
        dispatcher=dispatcher,
        tool_def=tool_def,
        func=search_func
    )
    print("✅ 知识查询工具已创建")

    # 创建Agent
    agent = (LoomBuilder()
        .with_id('knowledge-assistant')
        .with_llm(provider)
        .with_dispatcher(dispatcher)
        .with_tools([tool_node])
        .with_memory(memory)
        .with_agent(
            role='Knowledge Assistant',
            system_prompt='You are a helpful knowledge assistant. Use the search_knowledge tool to find information.'
        )
        .build())
    print(f"✅ Agent已创建: {agent.node_id}")

    # 测试问题
    questions = [
        "What is Python used for?",
        "Explain machine learning",
        "Tell me about databases"
    ]

    for i, question in enumerate(questions):
        print(f"\n📨 问题 {i+1}: {question}")

        event = CloudEvent(
            type="node.request",
            source="user",
            data={"content": question}
        )

        result = await agent.process(event)
        print(f"🤖 回答: {result[:200]}...")

    print(f"\n✅ 阶段4完成：测试了 {len(questions)} 个问题")


async def main():
    """主测试流程"""
    print("\n" + "=" * 80)
    print("🚀 集成测试：完整的记忆系统")
    print("=" * 80)
    print("测试目标：")
    print("  1. 阶段一：投影优化（模式检测、预算控制、语义相关性）")
    print("  2. 阶段二：L4压缩（聚类 + LLM总结）")
    print("=" * 80)

    try:
        # 阶段0：设置基础设施
        bus, dispatcher, provider, monitor = await setup_infrastructure()

        # 创建LoomMemory
        print("\n🔧 创建LoomMemory...")
        memory = LoomMemory("knowledge-assistant")
        print("✅ LoomMemory已创建")

        # 阶段1：填充L4知识库
        total_facts = await stage1_populate_l4(memory, monitor)

        # 阶段2：测试投影优化
        await stage2_test_projection_modes(memory, monitor)

        # 阶段3：触发L4压缩
        await stage3_trigger_l4_compression(memory, provider, monitor)

        # 阶段4：测试Agent使用压缩后的记忆
        await stage4_test_agent_with_memory(bus, dispatcher, provider, memory, monitor)

        # 打印测试摘要
        monitor.print_summary()

        print("\n" + "=" * 80)
        print("✅ 所有测试完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
