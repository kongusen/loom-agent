"""上下文检索器 - AgentExecutor 的核心组件"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loom.interfaces.retriever import BaseRetriever, Document


class ContextRetriever:
    """
    上下文检索器 - 自动为查询检索相关文档

    作为 AgentExecutor 的核心组件,在 LLM 调用前自动检索相关文档并注入上下文。

    使用场景:
    - 知识库问答
    - 文档助手
    - 需要外部知识的任务

    示例:
        retriever = VectorStoreRetriever(vector_store)
        context_retriever = ContextRetriever(
            retriever=retriever,
            top_k=3,
            auto_retrieve=True
        )

        agent = Agent(llm=llm, context_retriever=context_retriever)
        # 每次查询都会自动检索相关文档
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        top_k: int = 3,
        similarity_threshold: float = 0.0,
        auto_retrieve: bool = True,
        inject_as: str = "system",  # "system" or "user_prefix"
    ) -> None:
        """
        Parameters:
            retriever: 检索器实例
            top_k: 检索文档数量
            similarity_threshold: 相关性阈值 (0-1),低于此值的文档会被过滤
            auto_retrieve: 是否自动检索 (False 则需要手动调用)
            inject_as: 注入方式 ("system" 作为独立系统消息, "user_prefix" 作为用户消息前缀)
        """
        self.retriever = retriever
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.auto_retrieve = auto_retrieve
        self.inject_as = inject_as

    async def retrieve_for_query(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        为查询检索相关文档

        Parameters:
            query: 用户查询
            top_k: 覆盖默认的 top_k
            filters: 元数据过滤条件

        Returns:
            相关文档列表 (已过滤低相关性文档)
        """
        if not self.auto_retrieve:
            return []

        k = top_k if top_k is not None else self.top_k

        try:
            docs = await self.retriever.retrieve(
                query=query,
                top_k=k,
                filters=filters,
            )

            # 过滤低相关性文档
            if self.similarity_threshold > 0:
                docs = [
                    doc for doc in docs
                    if doc.score is None or doc.score >= self.similarity_threshold
                ]

            return docs

        except Exception as e:
            # 检索失败不应该阻塞主流程
            print(f"Warning: Document retrieval failed: {e}")
            return []

    def format_documents(
        self,
        documents: List[Document],
        max_length: int = 1000,
    ) -> str:
        """
        格式化文档为字符串 (用于注入上下文)

        Parameters:
            documents: 文档列表
            max_length: 单个文档最大长度

        Returns:
            格式化的文档字符串
        """
        if not documents:
            return ""

        lines = ["## Retrieved Context\n"]
        lines.append(f"Found {len(documents)} relevant document(s):\n")

        for i, doc in enumerate(documents, 1):
            lines.append(f"### Document {i}")

            # 元数据
            if doc.metadata:
                source = doc.metadata.get("source", "Unknown")
                lines.append(f"**Source**: {source}")

            if doc.score is not None:
                lines.append(f"**Relevance**: {doc.score:.2%}")

            # 内容 (截断)
            content = doc.content
            if len(content) > max_length:
                content = content[:max_length] + "...\n[truncated]"

            lines.append(f"\n{content}\n")

        lines.append("---\n")
        lines.append("Please answer the question based on the above context.\n")

        return "\n".join(lines)

    def format_as_user_prefix(
        self,
        documents: List[Document],
        user_query: str,
        max_length: int = 1000,
    ) -> str:
        """
        将文档格式化为用户消息的前缀

        适用于不想增加额外 system 消息的场景

        Returns:
            "Context: ...\n\nQuestion: {user_query}"
        """
        if not documents:
            return user_query

        doc_text = self.format_documents(documents, max_length)
        return f"{doc_text}\nQuestion: {user_query}"

    def get_metadata_summary(self, documents: List[Document]) -> Dict[str, Any]:
        """
        获取检索文档的元数据摘要

        用于日志和调试

        Returns:
            {"count": 3, "avg_score": 0.85, "sources": [...]}
        """
        if not documents:
            return {"count": 0}

        scores = [doc.score for doc in documents if doc.score is not None]
        sources = list(set(
            doc.metadata.get("source", "Unknown")
            for doc in documents
            if doc.metadata
        ))

        return {
            "count": len(documents),
            "avg_score": sum(scores) / len(scores) if scores else None,
            "sources": sources,
        }
