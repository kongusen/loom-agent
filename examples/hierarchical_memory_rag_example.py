"""
HierarchicalMemory + RAG 集成示例

演示分层记忆系统的核心功能：
1. 4层记忆管理（Ephemeral/Working/Session/Long-term）
2. 语义检索（RAG）
3. 自动晋升机制
4. 工具记忆管理
5. 与 ContextAssembler 集成

Requirements:
    pip install loom-agent openai
    export OPENAI_API_KEY=your_api_key_here
"""

import asyncio
import os
from loom.builtin.memory import HierarchicalMemory, MemoryEntry
from loom.builtin.embeddings import OpenAIEmbedding
from loom.builtin.vector_store import InMemoryVectorStore
from loom.core.message import Message
from loom.core.context_assembler import EnhancedContextManager, create_enhanced_context_manager


# ============================================================================
# Example 1: 基础用法 - 零配置启动
# ============================================================================

async def example_1_basic_usage():
    """
    最简单的用法：无向量化能力，使用关键词检索降级
    """
    print("=" * 80)
    print("Example 1: 基础用法 - 零配置启动（关键词检索）")
    print("=" * 80)

    # 创建不带向量化的 HierarchicalMemory（关键词检索降级）
    memory = HierarchicalMemory(
        enable_persistence=False,
        auto_promote=True,
        working_memory_size=5,
    )

    # 添加一些对话消息到 Session Memory
    messages = [
        Message(role="user", content="我叫张三，是一名软件工程师"),
        Message(role="assistant", content="你好张三！很高兴认识你。"),
        Message(role="user", content="我喜欢Python和机器学习"),
        Message(role="assistant", content="太好了！Python在ML领域应用广泛。"),
    ]

    for msg in messages:
        async for event in memory.add_message_stream(msg):
            if event.data and "message" in event.data:
                print(f"  [Event] {event.type.value}: {event.data['message']}")

    # 查询记忆（关键词检索）
    print("\n查询: '张三是谁？'")
    result = await memory.retrieve(query="张三是谁？", top_k=3)
    print(f"检索结果:\n{result}")

    # 查看不同层级的记忆
    print("\n[Session Memory]")
    session_msgs = await memory.get_by_tier("session")
    for msg in session_msgs[-2:]:
        print(f"  - {msg.role}: {msg.content[:50]}...")

    print("\n[Working Memory]")
    working_msgs = await memory.get_by_tier("working")
    print(f"  共 {len(working_msgs)} 条重要记忆")


# ============================================================================
# Example 2: RAG 语义检索 - 向量化记忆
# ============================================================================

async def example_2_rag_semantic_search():
    """
    使用 OpenAI Embedding 进行语义检索
    """
    print("\n" + "=" * 80)
    print("Example 2: RAG 语义检索 - 向量化记忆")
    print("=" * 80)

    # 检查 API Key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY 未设置，跳过此示例")
        return

    # 创建带向量化能力的 HierarchicalMemory
    embedding = OpenAIEmbedding(model="text-embedding-3-small")
    vector_store = InMemoryVectorStore(dimension=1536, use_faiss=True)

    memory = HierarchicalMemory(
        embedding=embedding,
        vector_store=vector_store,
        enable_persistence=False,
        auto_promote=True,
        working_memory_size=3,  # 较小的容量，便于演示晋升
    )

    await vector_store.initialize()

    # 添加对话（会自动提取到 Working Memory）
    conversations = [
        ("user", "我最近在学习 Rust 编程语言，觉得它的所有权系统很有意思"),
        ("assistant", "Rust 的所有权系统确实是其核心特性，能在编译期保证内存安全。"),
        ("user", "对，而且没有垃圾回收器，性能很好"),
        ("assistant", "是的，Rust 在系统编程领域很受欢迎，比如用于操作系统、浏览器引擎等。"),
        ("user", "我也在关注 WebAssembly，Rust 对 WASM 支持很棒"),
        ("assistant", "没错，Rust 是 WebAssembly 的首选语言之一，生态很丰富。"),
    ]

    print("\n添加对话到记忆...")
    for role, content in conversations:
        msg = Message(role=role, content=content)
        async for event in memory.add_message_stream(msg):
            pass  # 静默处理事件

    # 手动添加一些长期记忆（用户画像）
    print("\n添加用户画像到长期记忆...")
    await memory.add_to_longterm(
        content="用户是一名对系统编程和性能优化感兴趣的开发者，正在学习 Rust 语言。",
        metadata={"category": "user_profile", "importance": "high"}
    )

    await memory.add_to_longterm(
        content="用户关注前沿技术，包括 WebAssembly、浏览器技术等。",
        metadata={"category": "user_interests"}
    )

    # 语义检索（向量搜索）
    print("\n" + "-" * 80)
    print("语义检索测试：")

    queries = [
        "用户喜欢什么编程语言？",
        "用户对性能优化有什么看法？",
        "用户的技术背景是什么？",
    ]

    for query in queries:
        print(f"\n查询: '{query}'")
        result = await memory.retrieve(query=query, top_k=2, tier="longterm")
        print(f"检索结果:\n{result}")

    # 查看不同层级的记忆统计
    print("\n" + "-" * 80)
    print("记忆层级统计:")
    for tier in ["ephemeral", "working", "session", "longterm"]:
        msgs = await memory.get_by_tier(tier)
        print(f"  [{tier.upper()}] {len(msgs)} 条记忆")


# ============================================================================
# Example 3: 工具记忆（Ephemeral Memory）
# ============================================================================

async def example_3_tool_memory():
    """
    演示工具调用的临时记忆管理
    """
    print("\n" + "=" * 80)
    print("Example 3: 工具记忆（Ephemeral Memory）- 用完就丢")
    print("=" * 80)

    memory = HierarchicalMemory(enable_persistence=False)

    # 模拟工具调用流程
    tool_id = "call_abc123"
    tool_name = "search_database"

    # 1. 工具调用开始 - 添加临时记忆
    print(f"\n[步骤 1] 工具调用开始: {tool_name}")
    await memory.add_ephemeral(
        key=f"tool_{tool_id}",
        content=f"Calling {tool_name} with args: {{'query': 'user profile'}}",
        metadata={"tool_name": tool_name, "status": "in_progress"}
    )

    # 查看 Ephemeral Memory
    ephemeral_msgs = await memory.get_by_tier("ephemeral")
    print(f"  临时记忆: {len(ephemeral_msgs)} 条")
    for msg in ephemeral_msgs:
        print(f"    - {msg.content}")

    # 2. 模拟工具执行
    print(f"\n[步骤 2] 工具执行中...")
    await asyncio.sleep(0.5)  # 模拟耗时操作

    # 3. 工具调用完成 - 保存最终结果到 Session Memory
    print(f"\n[步骤 3] 工具调用完成，保存结果到 Session Memory")
    result_msg = Message(
        role="tool",
        content="Found user: Zhang San, Engineer, Interests: Python, ML",
        name=tool_name,
    )
    async for event in memory.add_message_stream(result_msg):
        pass

    # 4. 清理临时记忆
    print(f"\n[步骤 4] 清理临时记忆")
    await memory.clear_ephemeral(key=f"tool_{tool_id}")

    ephemeral_msgs_after = await memory.get_by_tier("ephemeral")
    session_msgs = await memory.get_by_tier("session")

    print(f"  临时记忆: {len(ephemeral_msgs_after)} 条（已清空）")
    print(f"  会话记忆: {len(session_msgs)} 条（保留最终结果）")

    # 验证只有最终结果被保留
    print("\n最终保留的记忆:")
    for msg in session_msgs:
        print(f"  - [{msg.role}] {msg.content}")


# ============================================================================
# Example 4: 自动晋升机制
# ============================================================================

async def example_4_auto_promotion():
    """
    演示 Working Memory → Long-term Memory 自动晋升
    """
    print("\n" + "=" * 80)
    print("Example 4: 自动晋升机制 (Working → Long-term)")
    print("=" * 80)

    # 创建容量很小的 Working Memory，便于演示晋升
    if os.getenv("OPENAI_API_KEY"):
        embedding = OpenAIEmbedding(model="text-embedding-3-small")
        vector_store = InMemoryVectorStore(dimension=1536)
        await vector_store.initialize()
    else:
        print("⚠️  未设置 OPENAI_API_KEY，使用无向量化模式")
        embedding = None
        vector_store = None

    memory = HierarchicalMemory(
        embedding=embedding,
        vector_store=vector_store,
        enable_persistence=False,
        auto_promote=True,
        working_memory_size=2,  # 只保留最近 2 条
    )

    # 添加多条消息，触发自动晋升
    messages = [
        "用户提到他在使用 Docker 进行容器化部署",
        "用户说他的团队在用 Kubernetes 编排",
        "用户询问关于微服务架构的最佳实践",
        "用户表示对服务网格（Service Mesh）感兴趣",
        "用户想了解 Istio 的工作原理",
    ]

    for i, content in enumerate(messages, 1):
        print(f"\n添加第 {i} 条消息: {content[:40]}...")
        msg = Message(role="user", content=content)
        async for event in memory.add_message_stream(msg):
            pass

        # 查看各层级状态
        working = await memory.get_by_tier("working")
        longterm = await memory.get_by_tier("longterm")

        print(f"  Working Memory: {len(working)} 条")
        print(f"  Long-term Memory: {len(longterm)} 条")

        if len(longterm) > 0:
            print(f"    → 已晋升到长期记忆: {longterm[-1].content[:50]}...")

    # 最终状态
    print("\n" + "-" * 80)
    print("最终记忆分布:")
    print(f"  Working Memory: {len(await memory.get_by_tier('working'))} 条（最近）")
    print(f"  Long-term Memory: {len(await memory.get_by_tier('longterm'))} 条（历史）")


# ============================================================================
# Example 5: 与 ContextAssembler 集成
# ============================================================================

async def example_5_context_integration():
    """
    演示 HierarchicalMemory 与 EnhancedContextManager 集成
    """
    print("\n" + "=" * 80)
    print("Example 5: 与 ContextAssembler 集成")
    print("=" * 80)

    # 创建带向量化的 HierarchicalMemory
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY 未设置，跳过此示例")
        return

    embedding = OpenAIEmbedding(model="text-embedding-3-small")
    vector_store = InMemoryVectorStore(dimension=1536)
    await vector_store.initialize()

    memory = HierarchicalMemory(
        embedding=embedding,
        vector_store=vector_store,
        auto_promote=True,
    )

    # 添加一些历史对话
    print("\n构建历史对话...")
    history = [
        ("user", "我是一名 Python 开发者，主要做数据分析"),
        ("assistant", "很高兴认识你！Python 在数据分析领域应用广泛。"),
        ("user", "我常用 pandas 和 numpy"),
        ("assistant", "这两个是数据分析的核心库，非常实用。"),
    ]

    for role, content in history:
        msg = Message(role=role, content=content)
        async for event in memory.add_message_stream(msg):
            pass

    # 添加用户画像到长期记忆
    await memory.add_to_longterm(
        content="用户是 Python 数据分析师，熟悉 pandas、numpy 等库。",
        metadata={"category": "user_profile"}
    )

    # 创建 EnhancedContextManager（集成 Memory）
    print("\n创建 EnhancedContextManager...")
    context_manager = create_enhanced_context_manager(
        memory=memory,
        max_context_tokens=8000,
        enable_smart_assembly=True,
    )

    # 准备新的用户消息
    print("\n准备新消息的上下文...")
    new_message = Message(
        role="user",
        content="我想学习机器学习，有什么推荐的库吗？"
    )

    # prepare() 会自动调用 memory.retrieve() 检索相关长期记忆
    prepared_message = await context_manager.prepare(new_message)

    # 查看组装后的上下文结构
    print("\n上下文组装完成！")
    print("  包含内容:")
    print("    - 系统提示词（如果有）")
    print("    - 检索到的长期记忆（RAG）")
    print("    - 会话历史（Session Memory）")
    print("    - 当前用户消息")

    print(f"\n  总 Token 数估算: ~{len(prepared_message.content.split())} tokens")

    # 显示检索到的记忆（如果有）
    if "retrieved_memory" in prepared_message.content.lower():
        print("\n  ✓ 成功从长期记忆检索相关内容（RAG）")


# ============================================================================
# Example 6: 完整工作流
# ============================================================================

async def example_6_full_workflow():
    """
    完整的 Agent 工作流：对话 → 工具调用 → 记忆管理 → RAG 检索
    """
    print("\n" + "=" * 80)
    print("Example 6: 完整工作流")
    print("=" * 80)

    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY 未设置，跳过此示例")
        return

    # 初始化系统
    embedding = OpenAIEmbedding(model="text-embedding-3-small")
    vector_store = InMemoryVectorStore(dimension=1536)
    await vector_store.initialize()

    memory = HierarchicalMemory(
        embedding=embedding,
        vector_store=vector_store,
        auto_promote=True,
        working_memory_size=5,
    )

    print("\n[场景] 用户与 AI 助手的多轮对话 + 工具调用")

    # Round 1: 用户介绍自己
    print("\n--- Round 1: 用户介绍 ---")
    msg1 = Message(role="user", content="你好，我是李明，一名前端工程师")
    async for _ in memory.add_message_stream(msg1):
        pass

    msg2 = Message(role="assistant", content="你好李明！很高兴认识你。")
    async for _ in memory.add_message_stream(msg2):
        pass

    # 保存用户画像到长期记忆
    await memory.add_to_longterm("用户李明是一名前端工程师", metadata={"type": "profile"})

    # Round 2: 工具调用（查询天气）
    print("\n--- Round 2: 工具调用 ---")
    msg3 = Message(role="user", content="北京今天天气怎么样？")
    async for _ in memory.add_message_stream(msg3):
        pass

    # 模拟工具调用流程
    tool_id = "call_weather_001"
    print("  [工具] 调用 get_weather 查询北京天气...")

    # 添加临时记忆
    await memory.add_ephemeral(
        key=f"tool_{tool_id}",
        content="Calling get_weather(city='Beijing')",
        metadata={"tool": "get_weather", "status": "running"}
    )

    await asyncio.sleep(0.3)  # 模拟 API 调用

    # 保存工具结果到 Session Memory
    tool_result = Message(
        role="tool",
        content="北京今天晴，温度 15-25°C，空气质量良好",
        name="get_weather"
    )
    async for _ in memory.add_message_stream(tool_result):
        pass

    # 清理临时记忆
    await memory.clear_ephemeral(key=f"tool_{tool_id}")

    msg4 = Message(role="assistant", content="北京今天天气不错，晴天，温度适宜。")
    async for _ in memory.add_message_stream(msg4):
        pass

    # Round 3: 相关查询（触发 RAG 检索）
    print("\n--- Round 3: RAG 检索 ---")
    query = "这个人是做什么工作的？"
    print(f"  查询: '{query}'")

    result = await memory.retrieve(query=query, top_k=2, tier="longterm")
    print(f"  检索结果: {result[:100]}...")

    # 最终统计
    print("\n" + "-" * 80)
    print("最终记忆统计:")
    for tier in ["ephemeral", "working", "session", "longterm"]:
        count = len(await memory.get_by_tier(tier))
        print(f"  [{tier.upper():12}] {count:2} 条")

    print("\n✓ 完整工作流执行完成！")


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """运行所有示例"""
    print("\n" + "🧠" * 40)
    print("HierarchicalMemory + RAG 集成示例")
    print("🧠" * 40)

    # 运行所有示例
    await example_1_basic_usage()
    await example_2_rag_semantic_search()
    await example_3_tool_memory()
    await example_4_auto_promotion()
    await example_5_context_integration()
    await example_6_full_workflow()

    print("\n" + "=" * 80)
    print("所有示例运行完成！")
    print("=" * 80)
    print("\n关键要点总结:")
    print("  1. 零配置：无需向量化也能使用（关键词检索降级）")
    print("  2. RAG 集成：语义检索增强上下文")
    print("  3. 分层管理：4 层记忆自动流转")
    print("  4. 工具记忆：用完就丢，只保留结果")
    print("  5. 自动晋升：Working → Long-term 智能晋升")
    print("  6. 无缝集成：与 ContextAssembler 完美配合")
    print()


if __name__ == "__main__":
    asyncio.run(main())
