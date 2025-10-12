"""
RAG Tool Example - 使用 DocumentSearchTool 实现 LLM 控制的检索

这个示例展示了如何将文档检索作为工具提供给 Agent：
- Agent 自主决定何时需要检索文档
- 可以与其他工具配合使用（计算器、搜索等）
- 适用于复杂的多步骤任务

适用场景：
- Agent 需要灵活决定何时检索
- 结合多种工具完成复杂任务
- 可能需要多次检索不同内容
"""

import asyncio
from loom.components.agent import Agent
from loom.builtin.retriever.in_memory import InMemoryRetriever
from loom.builtin.tools.document_search import DocumentSearchTool
from loom.builtin.tools.calculator import Calculator
from loom.interfaces.retriever import Document

# 假设已有 LLM 配置
from loom.llms.openai_llm import OpenAILLM


async def main():
    """Tool-based RAG 示例"""

    # ====== Step 1: 准备知识库 ======
    print("📚 Step 1: 准备技术文档知识库...")

    retriever = InMemoryRetriever()

    # 添加技术文档
    docs = [
        Document(
            content="Python 3.12 的新特性包括：更好的错误消息、性能提升 10-60%、新的类型注解语法 (PEP 695)。",
            metadata={"source": "python_3.12_release.md", "category": "python"}
        ),
        Document(
            content="JavaScript ES2024 引入了 Promise.withResolvers()、Object.groupBy() 等新 API。",
            metadata={"source": "js_es2024.md", "category": "javascript"}
        ),
        Document(
            content="Loom Framework 提供了工具系统（BaseTool）、记忆管理（BaseMemory）和 RAG 能力。",
            metadata={"source": "loom_docs.md", "category": "loom"}
        ),
        Document(
            content="Rust 1.75 改进了错误处理、async 性能和编译速度。",
            metadata={"source": "rust_1.75.md", "category": "rust"}
        ),
        Document(
            content="机器学习中的梯度下降算法用于优化模型参数，学习率通常设置为 0.001-0.1 之间。",
            metadata={"source": "ml_basics.md", "category": "ml"}
        ),
    ]

    await retriever.add_documents(docs)
    print(f"✅ 已添加 {len(retriever)} 个文档\n")

    # ====== Step 2: 创建工具 ======
    print("🔧 Step 2: 创建工具集...")

    # 文档搜索工具
    doc_search = DocumentSearchTool(retriever)

    # 计算器工具（用于演示多工具协作）
    calculator = Calculator()

    tools = [doc_search, calculator]
    print(f"✅ 创建了 {len(tools)} 个工具: {[t.name for t in tools]}\n")

    # ====== Step 3: 创建 Agent ======
    print("🤖 Step 3: 创建 Agent（带工具）...")

    llm = OpenAILLM(model="gpt-4", temperature=0.7)

    agent = Agent(
        llm=llm,
        tools=tools,  # 🔑 关键：提供工具列表（包括 DocumentSearchTool）
        system_instructions=(
            "你是一个技术助手。当需要查询技术文档时，使用 search_documents 工具。"
            "当需要计算时，使用 calculator 工具。合理组合工具完成任务。"
        ),
    )
    print("✅ Agent 创建完成\n")

    # ====== Step 4: 测试查询 ======
    print("=" * 60)
    print("💬 Step 4: 测试多工具协作\n")

    # 测试用例：需要 Agent 自主决定何时使用哪个工具
    test_cases = [
        {
            "query": "Python 3.12 有哪些新特性？",
            "expected_tool": "search_documents",
            "description": "纯文档检索"
        },
        {
            "query": "如果学习率是 0.01，训练 1000 轮，总的学习步数是多少？然后告诉我梯度下降的学习率范围。",
            "expected_tool": "calculator + search_documents",
            "description": "计算 + 检索"
        },
        {
            "query": "Loom Framework 和 Rust 1.75 各自的特点是什么？对比一下。",
            "expected_tool": "search_documents (multiple)",
            "description": "多次检索"
        },
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test['description']}")
        print(f"Query: {test['query']}")
        print("-" * 60)

        response = await agent.run(test['query'])

        print(f"📝 Response:\n{response}\n")
        print("=" * 60 + "\n")

    # ====== Step 5: 查看工具调用统计 ======
    print("📊 工具调用统计:")
    metrics = agent.get_metrics()
    print(f"  - 总工具调用次数: {metrics.tool_calls}")
    print(f"  - LLM 调用次数: {metrics.llm_calls}")
    print(f"  - 总迭代次数: {metrics.total_iterations}")


if __name__ == "__main__":
    asyncio.run(main())
