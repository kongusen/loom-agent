"""ChromaDB 向量存储适配器"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import uuid

from loom.interfaces.retriever import Document
from loom.interfaces.vector_store import BaseVectorStore

try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class ChromaVectorStore(BaseVectorStore):
    """
    ChromaDB 向量存储适配器

    特点:
    - ✅ 开源嵌入式向量数据库
    - ✅ 极简 API
    - ✅ 支持本地持久化
    - ✅ 自带 Embedding 功能（可选）
    - ✅ 适合快速原型开发

    示例:
        from loom.builtin.retriever.chroma_store import ChromaVectorStore
        from loom.builtin.retriever.vector_store_config import ChromaConfig

        # 本地持久化模式
        config = ChromaConfig.create_local(
            persist_directory="./chroma_db",
            collection_name="loom_docs"
        )

        # 远程服务模式
        config = ChromaConfig.create_remote(
            host="localhost",
            port=8000,
            collection_name="loom_docs"
        )

        vector_store = ChromaVectorStore(config)
        await vector_store.initialize()
    """

    def __init__(self, config: Dict[str, Any] | Any):
        """
        Parameters:
            config: ChromaConfig 对象或配置字典
        """
        if not CHROMA_AVAILABLE:
            raise ImportError(
                "ChromaDB is not installed. "
                "Install with: pip install chromadb"
            )

        # 支持字典或 Pydantic 模型
        if hasattr(config, "model_dump"):
            self.config = config.model_dump()
        else:
            self.config = config

        self.collection_name = self.config.get("collection_name", "loom_documents")
        self.dimension = self.config.get("dimension", 1536)
        self.client_type = self.config.get("client_type", "local")
        self.persist_directory = self.config.get("persist_directory")
        self.host = self.config.get("host")
        self.port = self.config.get("port", 8000)

        self.client: Optional[Any] = None
        self.collection: Optional[Any] = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化 ChromaDB 连接和集合"""
        if self._initialized:
            return

        # 初始化客户端
        if self.client_type == "local":
            # 本地持久化模式
            if self.persist_directory:
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory
                )
            else:
                # 内存模式（不持久化）
                self.client = chromadb.Client()
        else:
            # 远程 HTTP 模式
            self.client = chromadb.HttpClient(
                host=self.host,
                port=self.port
            )

        # 获取或创建集合
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name
            )
        except Exception:
            # 集合不存在，创建新集合
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"dimension": self.dimension}
            )

        self._initialized = True

    async def add_vectors(
        self,
        vectors: List[List[float]],
        documents: List[Document]
    ) -> None:
        """
        添加向量到 ChromaDB

        Parameters:
            vectors: 向量列表
            documents: 对应的文档列表
        """
        if not self._initialized:
            await self.initialize()

        # 构建 ChromaDB 数据格式
        ids = []
        embeddings = []
        documents_text = []
        metadatas = []

        for i, (vector, doc) in enumerate(zip(vectors, documents)):
            # 生成或使用文档 ID
            doc_id = doc.doc_id or str(uuid.uuid4())

            ids.append(doc_id)
            embeddings.append(vector)
            documents_text.append(doc.content)

            # 构建元数据
            metadata = doc.metadata or {}
            if doc.score is not None:
                metadata["score"] = doc.score
            metadatas.append(metadata)

        # 批量添加（ChromaDB 自动处理批量）
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents_text,
            metadatas=metadatas
        )

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        搜索相似向量

        Parameters:
            query_vector: 查询向量
            top_k: 返回结果数量
            filters: 元数据过滤条件

        Returns:
            [(Document, score), ...] 列表
        """
        if not self._initialized:
            await self.initialize()

        # 构建 where 过滤条件（ChromaDB 格式）
        where = None
        if filters:
            where = self._build_chroma_filter(filters)

        # 执行查询
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        # 转换结果
        documents_with_scores = []

        if results["ids"]:
            for i, doc_id in enumerate(results["ids"][0]):
                content = results["documents"][0][i]
                metadata = results["metadatas"][0][i] or {}
                distance = results["distances"][0][i]

                # 转换距离到相似度分数（ChromaDB 返回的是距离）
                # 对于余弦距离，相似度 = 1 - distance
                score = 1.0 - distance

                doc = Document(
                    content=content,
                    metadata=metadata,
                    score=score,
                    doc_id=doc_id
                )
                documents_with_scores.append((doc, score))

        return documents_with_scores

    async def delete(self, doc_ids: List[str]) -> None:
        """
        删除文档

        Parameters:
            doc_ids: 文档 ID 列表
        """
        if not self._initialized:
            await self.initialize()

        self.collection.delete(ids=doc_ids)

    async def clear(self) -> None:
        """清空集合"""
        if not self._initialized:
            await self.initialize()

        # ChromaDB: 删除并重建集合
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"dimension": self.dimension}
        )

    def _build_chroma_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建 ChromaDB where 过滤器

        ChromaDB 过滤语法:
        {
            "field": "value",
            "numeric_field": {"$gte": 10}
        }

        支持的操作符: $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
        """
        where = {}

        for key, value in filters.items():
            if isinstance(value, dict):
                # 复杂查询（例如: {"price": {"$gte": 100}}）
                where[key] = value
            else:
                # 简单相等查询
                where[key] = value

        return where

    async def close(self) -> None:
        """关闭连接"""
        # ChromaDB 客户端自动管理连接
        self._initialized = False
