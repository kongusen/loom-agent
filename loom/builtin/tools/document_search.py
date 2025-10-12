"""文档搜索工具 - 主动检索版本"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool

try:
    from loom.interfaces.retriever import BaseRetriever
except ImportError:
    BaseRetriever = None  # type: ignore


class DocumentSearchInput(BaseModel):
    """文档搜索输入参数"""

    query: str = Field(description="Search query for documents")
    top_k: int = Field(default=3, description="Number of documents to retrieve")


class DocumentSearchTool(BaseTool):
    """
    文档搜索工具 - 作为普通工具供 Agent 主动调用

    与 ContextRetriever 的区别:
    - ContextRetriever: 自动检索（每次查询前）- 核心组件
    - DocumentSearchTool: 主动检索（LLM 决定何时）- 工具

    适用场景:
    - Agent 需要动态决定何时检索文档
    - 可能需要多次检索（不同查询）
    - 与其他工具配合使用

    示例:
        retriever = VectorStoreRetriever(vector_store)
        search_tool = DocumentSearchTool(retriever)

        agent = Agent(
            llm=llm,
            tools=[search_tool, Calculator(), ...]
        )

        # Agent 会自己决定是否需要搜索文档
        result = await agent.run("Calculate 10*20 and search for Python docs")
    """

    name = "search_documents"
    description = (
        "Search for relevant documents from the knowledge base. "
        "Use this when you need specific information that might be in the documents. "
        "Returns document content with relevance scores."
    )
    args_schema = DocumentSearchInput
    is_concurrency_safe = True

    def __init__(self, retriever: "BaseRetriever"):
        """
        Parameters:
            retriever: 检索器实例 (例如 VectorStoreRetriever)
        """
        if BaseRetriever is None:
            raise ImportError("Please install retriever dependencies")

        self.retriever = retriever

    async def run(self, query: str, top_k: int = 3, **kwargs: Any) -> str:
        """
        执行文档搜索

        Parameters:
            query: 搜索查询
            top_k: 返回文档数量

        Returns:
            格式化的文档搜索结果
        """
        try:
            docs = await self.retriever.retrieve(query, top_k=top_k)

            if not docs:
                return f"No relevant documents found for query: '{query}'"

            # 格式化返回结果
            lines = [f"Found {len(docs)} relevant document(s) for: '{query}'\n"]

            for i, doc in enumerate(docs, 1):
                lines.append(f"**Document {i}**")

                # 元数据
                if doc.metadata:
                    source = doc.metadata.get("source", "Unknown")
                    lines.append(f"Source: {source}")

                # 相关性分数
                if doc.score is not None:
                    lines.append(f"Relevance: {doc.score:.2%}")

                # 内容 (截断长文档)
                content = doc.content
                if len(content) > 500:
                    content = content[:500] + "...\n[Content truncated for brevity]"

                lines.append(f"\n{content}\n")

            return "\n".join(lines)

        except Exception as e:
            return f"Error searching documents: {type(e).__name__}: {str(e)}"
