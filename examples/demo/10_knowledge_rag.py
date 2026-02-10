"""
10_knowledge_rag.py - 知识库 RAG 与 Context 集成

演示：
- GraphRAGKnowledgeBase 创建与使用
- RAGKnowledgeSource 上下文源
- ContextOrchestrator 上下文编排
- Session 集成 RAG 知识库
"""

import asyncio
from loom.api import (
    ContextController,
    Session,
    Task,
)
from loom.context import (
    ContextOrchestrator,
)
from loom.context.sources import (
    L1RecentSource,
    RAGKnowledgeSource,
    UserInputSource,
)
from loom.memory import EstimateCounter
from loom.providers.knowledge.rag import (
    Document,
    GraphRAGKnowledgeBase,
    RAGConfig,
)


async def main():
    print("=" * 60)
    print("知识库 RAG 与 Context 集成 Demo")
    print("=" * 60)

    # 1. 创建 GraphRAG 知识库
    kb = await demo_create_knowledge_base()

    # 2. 演示 RAG 查询
    await demo_rag_query(kb)

    # 3. 演示 RAGKnowledgeSource 上下文源
    await demo_rag_context_source(kb)

    # 4. 演示 ContextOrchestrator 集成
    await demo_context_orchestrator(kb)

    # 5. 演示 Session 集成
    await demo_session_integration(kb)

    print("\n" + "=" * 60)
    print("Demo 完成!")
    print("=" * 60)


async def demo_create_knowledge_base() -> GraphRAGKnowledgeBase:
    """创建并填充 GraphRAG 知识库"""
    print("\n" + "-" * 40)
    print("[1] 创建 GraphRAG 知识库")
    print("-" * 40)

    # 使用默认配置创建知识库
    config = RAGConfig(
        strategy="graph_first",
        chunk_size=256,
        chunk_overlap=50,
    )
    kb = GraphRAGKnowledgeBase.from_config(config=config)
    print("    创建 GraphRAGKnowledgeBase (graph_first 策略)")

    # 添加文档
    documents = [
        Document(
            id="doc-loom-intro",
            content="""
            Loom Agent 是一个分形架构的 AI Agent 框架。
            它支持多层级任务分解，每个节点都可以递归地创建子节点。
            核心特点包括：事件驱动、记忆层级、工具系统、技能热加载。
            """,
            metadata={"category": "introduction", "version": "0.5"},
        ),
        Document(
            id="doc-memory",
            content="""
            Loom 的记忆系统采用 L1-L4 四层架构：
            - L1: 最近任务（8K tokens）
            - L2: 重要任务（16K tokens）
            - L3: 聚合摘要（32K tokens）
            - L4: 持久化存储（向量检索）
            Session 负责管理单个会话的记忆，ContextController 负责跨会话共享。
            """,
            metadata={"category": "memory", "version": "0.5"},
        ),
        Document(
            id="doc-context",
            content="""
            Context 模块基于 Anthropic Context Engineering 思想：
            - Token-First Design: 所有操作以 token 为单位
            - Quality over Quantity: 质量优于数量
            - Just-in-Time Context: 按需加载
            ContextOrchestrator 负责编排多个上下文源，构建 LLM 消息。
            """,
            metadata={"category": "context", "version": "0.5"},
        ),
        Document(
            id="doc-rag",
            content="""
            RAG 框架提供完整的检索增强生成能力：
            - GraphRAGKnowledgeBase: 图增强知识库
            - 支持 graph_first、vector_first、hybrid 三种策略
            - 内置实体抽取和关系构建
            - 可通过 RAGKnowledgeSource 集成到 Context 系统
            """,
            metadata={"category": "rag", "version": "0.5"},
        ),
    ]

    await kb.add_documents(documents, extract_entities=True)
    print(f"    添加 {len(documents)} 个文档")

    return kb


async def demo_rag_query(kb: GraphRAGKnowledgeBase):
    """演示 RAG 查询"""
    print("\n" + "-" * 40)
    print("[2] RAG 查询")
    print("-" * 40)

    queries = ["记忆系统", "Context 设计原则", "RAG 策略"]

    for query in queries:
        results = await kb.query(query, limit=2)
        print(f"\n    查询: '{query}'")
        for r in results:
            content_preview = r.content[:50].replace("\n", " ").strip()
            print(f"      - [{r.source}] {content_preview}... (相关度: {r.relevance:.2f})")


async def demo_rag_context_source(kb: GraphRAGKnowledgeBase):
    """演示 RAGKnowledgeSource 上下文源"""
    print("\n" + "-" * 40)
    print("[3] RAGKnowledgeSource 上下文源")
    print("-" * 40)

    # 创建 RAG 上下文源
    rag_source = RAGKnowledgeSource(
        knowledge_base=kb,
        relevance_threshold=0.3,
    )
    print(f"    创建 RAGKnowledgeSource (阈值: 0.3)")
    print(f"    源名称: {rag_source.source_name}")

    # 使用 token 计数器
    token_counter = EstimateCounter()

    # 收集上下文
    query = "Loom 的记忆系统是如何工作的？"
    blocks = await rag_source.collect(
        query=query,
        token_budget=2000,
        token_counter=token_counter,
        min_relevance=0.3,
    )

    print(f"\n    查询: '{query}'")
    print(f"    收集到 {len(blocks)} 个上下文块:")
    for block in blocks:
        content_preview = block.content[:60].replace("\n", " ").strip()
        print(f"      - {content_preview}...")
        print(f"        tokens: {block.token_count}, priority: {block.priority:.2f}")


async def demo_context_orchestrator(kb: GraphRAGKnowledgeBase):
    """演示 ContextOrchestrator 集成"""
    print("\n" + "-" * 40)
    print("[4] ContextOrchestrator 集成")
    print("-" * 40)

    # 创建 token 计数器
    token_counter = EstimateCounter()

    # 创建多个上下文源
    sources = [
        UserInputSource("用户想了解 Loom 的 RAG 功能"),
        RAGKnowledgeSource(kb, relevance_threshold=0.3),
    ]

    # 创建编排器
    orchestrator = ContextOrchestrator(
        token_counter=token_counter,
        sources=sources,
        model_context_window=8000,
        output_reserve_ratio=0.25,
    )
    print("    创建 ContextOrchestrator")
    print(f"    上下文源: {[s.source_name for s in sources]}")

    # 获取预算信息
    budget_info = orchestrator.get_budget_info("你是一个知识助手。")
    print(f"\n    预算信息:")
    print(f"      总预算: {budget_info['total']} tokens")
    print(f"      可用预算: {budget_info['available']} tokens")
    print(f"      分配: {budget_info['allocation']}")

    # 构建上下文
    messages = await orchestrator.build_context(
        query="RAG 框架有哪些检索策略？",
        system_prompt="你是一个知识助手，基于知识库回答问题。",
        min_relevance=0.3,
    )

    print(f"\n    构建的消息数: {len(messages)}")
    for i, msg in enumerate(messages):
        role = msg["role"]
        content_preview = msg["content"][:80].replace("\n", " ").strip()
        print(f"      [{i+1}] {role}: {content_preview}...")


async def demo_session_integration(kb: GraphRAGKnowledgeBase):
    """演示 Session 集成 RAG"""
    print("\n" + "-" * 40)
    print("[5] Session 集成 RAG")
    print("-" * 40)

    # 创建 ContextController 和 Session
    controller = ContextController()
    session = Session(session_id="rag-session")
    controller.register_session(session)
    print("    创建 Session: rag-session")

    # 添加一些对话任务
    tasks_data = [
        ("node.message", "用户: Loom 的记忆系统有几层？"),
        ("node.response", "助手: Loom 采用 L1-L4 四层记忆架构..."),
        ("node.message", "用户: RAG 是什么？"),
    ]

    for action, content in tasks_data:
        task = Task(action=action, parameters={"content": content})
        session.add_task(task)

    print(f"    添加 {len(tasks_data)} 个对话任务")

    # 创建 token 计数器
    token_counter = EstimateCounter()

    # 创建包含 L1 和 RAG 的上下文源
    sources = [
        L1RecentSource(session.memory, session.session_id),
        RAGKnowledgeSource(kb, relevance_threshold=0.3),
    ]

    # 创建编排器
    orchestrator = ContextOrchestrator(
        token_counter=token_counter,
        sources=sources,
        model_context_window=8000,
    )

    # 构建上下文
    messages = await orchestrator.build_context(
        query="RAG 框架的检索策略",
        system_prompt="你是一个知识助手。",
        min_relevance=0.3,
    )

    print(f"\n    整合后的上下文消息数: {len(messages)}")
    print("    消息来源:")

    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"]
        # 判断来源
        if "[Knowledge:" in content:
            source = "RAG"
        elif "用户:" in content or "助手:" in content:
            source = "L1"
        else:
            source = "System"
        content_preview = content[:50].replace("\n", " ").strip()
        print(f"      [{source}] {role}: {content_preview}...")


if __name__ == "__main__":
    asyncio.run(main())
