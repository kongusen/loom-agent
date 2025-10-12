"""
RAG Patterns Example - 高级 RAG 编排模式

这个示例展示了三种高级 RAG 模式：
1. RAGPattern - 基础检索增强生成（支持 Re-ranking）
2. MultiQueryRAG - 多查询 RAG（生成查询变体，提高召回率）
3. HierarchicalRAG - 层次化 RAG（文档 → 段落两级检索）

适用场景：
- 需要完整控制 RAG 流程
- 复杂查询需要多角度检索
- 长文档需要精确定位
"""

import asyncio
from loom.components.agent import Agent
from loom.builtin.retriever.in_memory import InMemoryRetriever
from loom.patterns.rag import RAGPattern, MultiQueryRAG, HierarchicalRAG
from loom.interfaces.retriever import Document

from loom.llms.openai_llm import OpenAILLM


# ====== 简单的 Re-ranker 示例 ======
async def simple_reranker(query: str, docs: list[Document]) -> list[Document]:
    """
    简单的重排序函数 - 基于关键词密度

    实际生产中，可以使用：
    - Cross-Encoder 模型
    - Cohere Rerank API
    - 自定义排序算法
    """
    query_terms = set(query.lower().split())

    # 重新计算分数（考虑关键词密度）
    for doc in docs:
        doc_terms = doc.content.lower().split()
        density = sum(1 for term in doc_terms if term in query_terms) / len(doc_terms)
        doc.score = density

    # 按新分数排序
    docs.sort(key=lambda d: d.score or 0, reverse=True)
    return docs


async def demo_basic_rag():
    """示例 1: 基础 RAG Pattern（带 Re-ranking）"""
    print("\n" + "=" * 60)
    print("📖 示例 1: RAGPattern - 基础检索增强生成")
    print("=" * 60 + "\n")

    # 准备数据
    retriever = InMemoryRetriever()
    docs = [
        Document(
            content="Loom Framework 是一个轻量级的 AI Agent 开发框架，专注于提供核心的 Agent 能力。",
            metadata={"source": "intro.md"}
        ),
        Document(
            content="Loom 支持工具系统、记忆管理、RAG 检索和事件流等核心功能。",
            metadata={"source": "features.md"}
        ),
        Document(
            content="Loom 的 RAG 能力包括自动检索（ContextRetriever）和工具检索（DocumentSearchTool）。",
            metadata={"source": "rag.md"}
        ),
        Document(
            content="Loom 使用 Pydantic 进行数据验证，确保类型安全。",
            metadata={"source": "design.md"}
        ),
    ]
    await retriever.add_documents(docs)

    # 创建 Agent 和 RAGPattern
    llm = OpenAILLM(model="gpt-4", temperature=0.7)
    agent = Agent(llm=llm)

    rag = RAGPattern(
        agent=agent,
        retriever=retriever,
        reranker=simple_reranker,  # 🔑 可选的 Re-ranking
        top_k=4,  # 初始检索 4 个文档
        rerank_top_k=2,  # 重排序后保留 2 个
    )

    # 查询
    query = "Loom 的 RAG 能力是什么？"
    print(f"Query: {query}\n")

    response = await rag.run(query)
    print(f"Response:\n{response}\n")


async def demo_multi_query_rag():
    """示例 2: 多查询 RAG"""
    print("\n" + "=" * 60)
    print("📖 示例 2: MultiQueryRAG - 多查询变体检索")
    print("=" * 60 + "\n")

    # 准备更复杂的数据
    retriever = InMemoryRetriever()
    docs = [
        Document(
            content="上下文工程（Context Engineering）是一种先进的提示管理技术。",
            metadata={"source": "context_eng.md"}
        ),
        Document(
            content="Context Engineering 包括文档检索、工具选择、记忆管理和智能上下文策展。",
            metadata={"source": "context_components.md"}
        ),
        Document(
            content="提示工程（Prompt Engineering）专注于优化输入提示以改善 LLM 输出。",
            metadata={"source": "prompt_eng.md"}
        ),
        Document(
            content="RAG（检索增强生成）通过检索外部知识库增强 LLM 的生成能力。",
            metadata={"source": "rag_intro.md"}
        ),
        Document(
            content="智能上下文管理可以自动选择最相关的文档、工具和历史对话。",
            metadata={"source": "smart_context.md"}
        ),
    ]
    await retriever.add_documents(docs)

    # 创建 MultiQueryRAG
    llm = OpenAILLM(model="gpt-4", temperature=0.7)
    agent = Agent(llm=llm)

    multi_rag = MultiQueryRAG(
        agent=agent,
        retriever=retriever,
        query_count=3,  # 🔑 生成 3 个查询变体
        top_k=6,  # 每个查询检索 2 个文档（6/3=2）
        rerank_top_k=3,  # 最终保留 3 个
    )

    # 复杂查询
    query = "上下文工程和提示工程有什么区别？"
    print(f"Query: {query}")
    print("（MultiQueryRAG 会生成 3 个查询变体，分别检索后合并）\n")

    response = await multi_rag.run(query)
    print(f"Response:\n{response}\n")


async def demo_hierarchical_rag():
    """示例 3: 层次化 RAG"""
    print("\n" + "=" * 60)
    print("📖 示例 3: HierarchicalRAG - 层次化检索")
    print("=" * 60 + "\n")

    # 模拟长文档（分成多个段落）
    retriever = InMemoryRetriever()
    docs = [
        Document(
            content="第一章：Loom 框架介绍。Loom 是一个轻量级 AI Agent 框架，提供核心的 Agent 执行能力。",
            metadata={"source": "chapter1.md", "type": "paragraph"}
        ),
        Document(
            content="第二章：核心组件。Loom 包括 LLM 接口、工具系统、记忆管理和事件流。",
            metadata={"source": "chapter2.md", "type": "paragraph"}
        ),
        Document(
            content="第三章：RAG 能力。Loom 的 RAG 实现分为三层：核心组件、工具和高级模式。",
            metadata={"source": "chapter3.md", "type": "paragraph"}
        ),
        Document(
            content="第四章：高级模式。包括 RAGPattern、MultiQueryRAG 和 HierarchicalRAG。",
            metadata={"source": "chapter4.md", "type": "paragraph"}
        ),
    ]
    await retriever.add_documents(docs)

    # 创建 HierarchicalRAG
    llm = OpenAILLM(model="gpt-4", temperature=0.7)
    agent = Agent(llm=llm)

    hierarchical_rag = HierarchicalRAG(
        agent=agent,
        document_retriever=retriever,  # 第一级：文档检索
        paragraph_retriever=retriever,  # 第二级：段落检索（这里简化为同一个）
        doc_top_k=4,  # 检索 4 个相关文档
        para_top_k=2,  # 在文档内检索 2 个段落
    )

    # 查询
    query = "Loom 的高级模式有哪些？"
    print(f"Query: {query}")
    print("（HierarchicalRAG 会先检索文档，再在文档内检索段落）\n")

    response = await hierarchical_rag.run(query)
    print(f"Response:\n{response}\n")


async def main():
    """运行所有示例"""
    print("\n🚀 高级 RAG 模式示例\n")

    await demo_basic_rag()
    await demo_multi_query_rag()
    await demo_hierarchical_rag()

    print("\n✅ 所有示例完成！\n")
    print("💡 总结:")
    print("  - RAGPattern: 适用于需要 Re-ranking 的场景")
    print("  - MultiQueryRAG: 适用于复杂查询，提高召回率")
    print("  - HierarchicalRAG: 适用于长文档的精确定位")
    print()


if __name__ == "__main__":
    asyncio.run(main())
