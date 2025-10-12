"""RAG Pattern - 完整的 Retrieval-Augmented Generation 编排"""

from __future__ import annotations

from typing import List, Optional

from loom.components.agent import Agent
from loom.interfaces.retriever import BaseRetriever, Document


class RAGPattern:
    """
    RAG 编排模式 - 检索增强生成

    完整的 RAG Pipeline:
    1. 检索 (Retrieve) - 从知识库检索相关文档
    2. 排序 (Rerank) - 可选的重排序步骤
    3. 生成 (Generate) - 基于检索到的上下文生成答案

    适用场景:
    - 需要完整控制 RAG 流程
    - 需要 Re-ranking
    - 需要多轮迭代

    示例:
        rag = RAGPattern(
            agent=agent,
            retriever=retriever,
            reranker=cross_encoder_rerank,
            top_k=10,
            rerank_top_k=3
        )

        result = await rag.run("What is Loom framework?")
    """

    def __init__(
        self,
        agent: Agent,
        retriever: BaseRetriever,
        reranker: Optional[callable] = None,
        top_k: int = 5,
        rerank_top_k: int = 3,
    ):
        """
        Parameters:
            agent: Agent 实例
            retriever: 检索器实例
            reranker: 可选的重排序函数 (query, docs) -> reranked_docs
            top_k: 初始检索文档数量
            rerank_top_k: 重排序后保留的文档数量
        """
        self.agent = agent
        self.retriever = retriever
        self.reranker = reranker
        self.top_k = top_k
        self.rerank_top_k = rerank_top_k

    async def run(self, query: str) -> str:
        """
        执行完整的 RAG 流程

        Parameters:
            query: 用户查询

        Returns:
            生成的答案
        """
        # Step 1: 检索相关文档
        docs = await self.retriever.retrieve(query, top_k=self.top_k)

        if not docs:
            # 没有检索到文档,直接让 Agent 回答
            return await self.agent.run(query)

        # Step 2: Re-ranking (可选)
        if self.reranker:
            docs = await self.reranker(query, docs)
            docs = docs[:self.rerank_top_k]

        # Step 3: 构建增强查询
        augmented_query = self._build_augmented_query(query, docs)

        # Step 4: Agent 生成答案
        return await self.agent.run(augmented_query)

    def _build_augmented_query(self, query: str, docs: List[Document]) -> str:
        """
        构建增强查询 - 将检索到的文档与查询组合

        Parameters:
            query: 原始查询
            docs: 检索到的文档列表

        Returns:
            增强后的查询字符串
        """
        if not docs:
            return query

        context_parts = []
        for i, doc in enumerate(docs, 1):
            # 格式化文档
            doc_text = f"[Document {i}]"
            if doc.metadata and doc.metadata.get("source"):
                doc_text += f"\nSource: {doc.metadata['source']}"
            doc_text += f"\n{doc.content}"

            context_parts.append(doc_text)

        context = "\n\n".join(context_parts)

        return f"""Based on the following context, please answer the question accurately and concisely.

Context:
{context}

Question: {query}

Answer:"""


class MultiQueryRAG(RAGPattern):
    """
    多查询 RAG - 生成多个查询变体并合并结果

    适用场景:
    - 复杂查询需要多角度检索
    - 提高召回率

    示例:
        rag = MultiQueryRAG(
            agent=agent,
            retriever=retriever,
            query_count=3
        )

        result = await rag.run("How does context engineering work?")
        # 会生成 3 个查询变体,分别检索后合并
    """

    def __init__(
        self,
        agent: Agent,
        retriever: BaseRetriever,
        reranker: Optional[callable] = None,
        top_k: int = 5,
        rerank_top_k: int = 3,
        query_count: int = 3,
    ):
        super().__init__(agent, retriever, reranker, top_k, rerank_top_k)
        self.query_count = query_count

    async def run(self, query: str) -> str:
        """执行多查询 RAG 流程"""
        # Step 1: 生成查询变体
        queries = await self._generate_query_variants(query)

        # Step 2: 并发检索
        all_docs: List[Document] = []
        for q in queries:
            docs = await self.retriever.retrieve(q, top_k=self.top_k // len(queries))
            all_docs.extend(docs)

        # Step 3: 去重与排序
        unique_docs = self._deduplicate_docs(all_docs)

        # Step 4: Re-ranking (可选)
        if self.reranker:
            unique_docs = await self.reranker(query, unique_docs)

        # Step 5: 生成答案
        augmented_query = self._build_augmented_query(query, unique_docs[:self.rerank_top_k])
        return await self.agent.run(augmented_query)

    async def _generate_query_variants(self, query: str) -> List[str]:
        """
        生成查询变体

        简单策略:
        - 原始查询
        - 改写查询 (更具体)
        - 相关问题
        """
        variants = [query]

        # 使用 Agent 生成变体查询
        prompt = f"""Generate {self.query_count - 1} alternative search queries for: "{query}"

Return only the queries, one per line, without numbering or explanation."""

        try:
            response = await self.agent.run(prompt)
            lines = [line.strip() for line in response.split("\n") if line.strip()]
            variants.extend(lines[:self.query_count - 1])
        except Exception:
            # 生成失败,只使用原始查询
            pass

        return variants[:self.query_count]

    def _deduplicate_docs(self, docs: List[Document]) -> List[Document]:
        """
        去重文档

        简单策略: 基于内容去重
        """
        seen_content = set()
        unique_docs = []

        for doc in docs:
            # 使用内容的前 100 个字符作为唯一标识
            key = doc.content[:100]

            if key not in seen_content:
                seen_content.add(key)
                unique_docs.append(doc)

        return unique_docs


class HierarchicalRAG(RAGPattern):
    """
    层次化 RAG - 先检索文档,再检索段落

    适用场景:
    - 文档很长,需要两级检索
    - 需要更精确的定位

    流程:
    1. 检索相关文档 (粗粒度)
    2. 在检索到的文档内检索段落 (细粒度)
    3. 基于段落生成答案
    """

    def __init__(
        self,
        agent: Agent,
        document_retriever: BaseRetriever,
        paragraph_retriever: Optional[BaseRetriever] = None,
        doc_top_k: int = 5,
        para_top_k: int = 3,
    ):
        super().__init__(agent, document_retriever, top_k=doc_top_k)
        self.paragraph_retriever = paragraph_retriever or document_retriever
        self.para_top_k = para_top_k

    async def run(self, query: str) -> str:
        """执行层次化 RAG"""
        # Step 1: 检索文档
        docs = await self.retriever.retrieve(query, top_k=self.top_k)

        if not docs:
            return await self.agent.run(query)

        # Step 2: 在检索到的文档内检索段落
        # 简化实现: 直接使用检索到的文档
        paragraphs = docs[:self.para_top_k]

        # Step 3: 生成答案
        augmented_query = self._build_augmented_query(query, paragraphs)
        return await self.agent.run(augmented_query)
