"""
RAG Basic Example - 使用 ContextRetriever 实现自动检索

这个示例展示了如何使用 Loom 框架的核心 RAG 能力：
- ContextRetriever 自动检索相关文档
- 文档作为上下文注入到 Agent
- Agent 基于检索到的文档生成答案

适用场景：
- 知识库问答
- 文档搜索与总结
- 需要自动检索支持的对话系统
"""

import asyncio
from loom.components.agent import Agent
from loom.builtin.retriever.in_memory import InMemoryRetriever
from loom.core.context_retriever import ContextRetriever
from loom.interfaces.retriever import Document

# 假设已有 LLM 配置（需要根据实际情况初始化）
from loom.llms.openai_llm import OpenAILLM  # 或者其他 LLM


async def main():
    """基础 RAG 示例"""

    # ====== Step 1: 准备知识库 ======
    print("📚 Step 1: 准备知识库...")

    # 创建检索器
    retriever = InMemoryRetriever()

    # 添加文档到知识库
    docs = [
        Document(
            content="Loom Framework 是一个用于构建 AI Agent 的轻量级框架。它提供了核心的 Agent 执行能力、工具系统、记忆管理和事件流。",
            metadata={"source": "loom_intro.md", "section": "overview"}
        ),
        Document(
            content="Loom 支持 RAG（检索增强生成）能力。通过 ContextRetriever，Agent 可以自动检索相关文档作为上下文。",
            metadata={"source": "loom_features.md", "section": "rag"}
        ),
        Document(
            content="Agent 可以使用多种工具，包括计算器、搜索引擎、文档检索等。工具通过 BaseTool 接口统一管理。",
            metadata={"source": "loom_tools.md", "section": "tools"}
        ),
        Document(
            content="Loom 使用 Pydantic 进行类型验证，确保数据模型的安全性和可靠性。所有核心组件都有完整的类型注解。",
            metadata={"source": "loom_design.md", "section": "architecture"}
        ),
    ]

    await retriever.add_documents(docs)
    print(f"✅ 已添加 {len(retriever)} 个文档到知识库\n")

    # ====== Step 2: 配置 ContextRetriever ======
    print("🔧 Step 2: 配置 ContextRetriever...")

    context_retriever = ContextRetriever(
        retriever=retriever,
        top_k=2,  # 检索 top 2 最相关的文档
        similarity_threshold=0.0,  # 关键词匹配，无阈值限制
        auto_retrieve=True,  # 自动检索
        inject_as="system",  # 作为系统消息注入
    )
    print("✅ ContextRetriever 配置完成\n")

    # ====== Step 3: 创建 Agent ======
    print("🤖 Step 3: 创建 Agent...")

    # 初始化 LLM
    llm = OpenAILLM(
        model="gpt-4",
        temperature=0.7,
    )

    # 创建 Agent（注入 context_retriever）
    agent = Agent(
        llm=llm,
        context_retriever=context_retriever,  # 🔑 关键：注入 ContextRetriever
        system_instructions="你是一个 Loom 框架的助手。基于检索到的文档准确回答用户问题。",
    )
    print("✅ Agent 创建完成\n")

    # ====== Step 4: 查询测试 ======
    print("=" * 60)
    print("💬 Step 4: 测试 RAG 查询\n")

    queries = [
        "Loom 是什么？",
        "Loom 支持哪些核心功能？",
        "Loom 使用了什么技术进行类型验证？",
    ]

    for i, query in enumerate(queries, 1):
        print(f"Query {i}: {query}")
        print("-" * 60)

        # Agent 会自动检索相关文档并生成答案
        response = await agent.run(query)

        print(f"📝 Answer:\n{response}\n")
        print("=" * 60 + "\n")

    # ====== Step 5: 查看检索指标 ======
    print("📊 检索指标:")
    metrics = agent.get_metrics()
    print(f"  - 总检索次数: {getattr(metrics, 'retrievals', 0)}")
    print(f"  - LLM 调用次数: {metrics.llm_calls}")


if __name__ == "__main__":
    asyncio.run(main())
