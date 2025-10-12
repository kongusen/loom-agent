"""基于向量存储的检索器实现"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loom.interfaces.retriever import BaseRetriever, Document
from loom.interfaces.vector_store import BaseVectorStore
from loom.interfaces.embedding import BaseEmbedding


class VectorStoreRetriever(BaseRetriever):
    """
    向量存储检索器 - 基于语义相似度检索

    将向量存储和 Embedding 模型组合，提供语义检索能力。

    特点:
    - ✅ 语义相似度检索
    - ✅ 支持多种向量数据库
    - ✅ 支持多种 Embedding 模型
    - ✅ 自动向量化

    示例:
        from loom.builtin.retriever.vector_store import VectorStoreRetriever
        from loom.builtin.retriever.chroma_store import ChromaVectorStore
        from loom.builtin.embeddings import OpenAIEmbedding

        vector_store = ChromaVectorStore(config)
        await vector_store.initialize()

        embedding = OpenAIEmbedding(api_key="...")

        retriever = VectorStoreRetriever(
            vector_store=vector_store,
            embedding=embedding
        )

        # 添加文档（自动向量化）
        await retriever.add_documents([
            Document(content="Loom is an AI agent framework"),
            Document(content="Loom supports RAG capabilities"),
        ])

        # 检索（自动向量化查询）
        results = await retriever.retrieve("What is Loom?", top_k=2)
    """

    def __init__(
        self,
        vector_store: BaseVectorStore,
        embedding: BaseEmbedding,
    ):
        """
        Parameters:
            vector_store: 向量存储实例（Pinecone, Qdrant, Milvus, ChromaDB）
            embedding: Embedding 模型实例（OpenAI, Sentence Transformers）
        """
        self.vector_store = vector_store
        self.embedding = embedding

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        基于语义相似度检索文档

        Parameters:
            query: 查询文本
            top_k: 返回文档数量
            filters: 元数据过滤条件（可选）

        Returns:
            Document 列表，按相似度分数降序排列
        """
        # Step 1: 将查询向量化
        query_vector = await self.embedding.embed_query(query)

        # Step 2: 在向量存储中搜索
        results = await self.vector_store.search(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters
        )

        # Step 3: 提取文档（已包含 score）
        documents = [doc for doc, score in results]

        return documents

    async def add_documents(self, documents: List[Document]) -> None:
        """
        添加文档到向量存储（自动向量化）

        Parameters:
            documents: 文档列表
        """
        if not documents:
            return

        # Step 1: 提取文档内容
        texts = [doc.content for doc in documents]

        # Step 2: 批量向量化
        vectors = await self.embedding.embed_documents(texts)

        # Step 3: 添加到向量存储
        await self.vector_store.add_vectors(vectors, documents)

    async def delete_documents(self, doc_ids: List[str]) -> None:
        """
        删除文档

        Parameters:
            doc_ids: 文档 ID 列表
        """
        await self.vector_store.delete(doc_ids)

    async def clear(self) -> None:
        """清空所有文档"""
        await self.vector_store.clear()

    async def close(self) -> None:
        """关闭连接"""
        await self.vector_store.close()
