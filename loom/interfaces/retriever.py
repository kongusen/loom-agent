"""检索器接口 - RAG 系统的基础抽象"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Document(BaseModel):
    """
    文档数据模型

    表示从知识库检索到的文档片段
    """

    content: str = Field(description="文档内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="文档元数据")
    score: Optional[float] = Field(default=None, description="相关性分数 (0-1)")
    doc_id: Optional[str] = Field(default=None, description="文档唯一标识")

    def __str__(self) -> str:
        source = self.metadata.get("source", "Unknown")
        return f"Document(source={source}, score={self.score}, len={len(self.content)})"

    def format(self, max_length: int = 500) -> str:
        """格式化文档用于显示"""
        lines = []
        if self.metadata.get("source"):
            lines.append(f"**Source**: {self.metadata['source']}")
        if self.score is not None:
            lines.append(f"**Relevance**: {self.score:.2%}")

        content = self.content
        if len(content) > max_length:
            content = content[:max_length] + "..."
        lines.append(content)

        return "\n".join(lines)


class BaseRetriever(ABC):
    """
    检索器基础接口

    所有检索器必须实现此接口:
    - VectorStoreRetriever (向量检索)
    - BM25Retriever (关键词检索)
    - HybridRetriever (混合检索)
    """

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        检索相关文档

        Parameters:
            query: 查询字符串
            top_k: 返回文档数量
            filters: 过滤条件 (例如: {"source": "doc.pdf"})

        Returns:
            按相关性排序的文档列表
        """
        pass

    @abstractmethod
    async def add_documents(
        self,
        documents: List[Document],
    ) -> None:
        """
        添加文档到检索系统

        Parameters:
            documents: 要添加的文档列表
        """
        pass

    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        便捷方法: 添加文本列表

        Parameters:
            texts: 文本列表
            metadatas: 对应的元数据列表
        """
        if metadatas is None:
            metadatas = [{} for _ in texts]

        documents = [
            Document(content=text, metadata=meta)
            for text, meta in zip(texts, metadatas)
        ]

        await self.add_documents(documents)


class BaseVectorStore(ABC):
    """
    向量存储基础接口

    用于底层向量数据库的抽象:
    - ChromaDB
    - FAISS
    - Pinecone
    - Weaviate
    """

    @abstractmethod
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        基于向量相似度搜索

        Parameters:
            query: 查询字符串 (会被自动向量化)
            k: 返回结果数量
            filters: 元数据过滤条件

        Returns:
            按相似度排序的文档列表
        """
        pass

    @abstractmethod
    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        添加文本到向量存储

        Parameters:
            texts: 文本列表
            metadatas: 元数据列表

        Returns:
            文档 ID 列表
        """
        pass

    @abstractmethod
    async def delete(self, ids: List[str]) -> None:
        """删除文档"""
        pass


class BaseEmbedding(ABC):
    """
    嵌入模型接口

    用于将文本转换为向量
    """

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """生成查询向量"""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量生成文档向量"""
        pass
