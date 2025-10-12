"""Pinecone 向量存储适配器"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from loom.interfaces.retriever import Document
from loom.interfaces.vector_store import BaseVectorStore

try:
    import pinecone
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False


class PineconeVectorStore(BaseVectorStore):
    """
    Pinecone 向量存储适配器

    特点:
    - ✅ 云原生向量数据库
    - ✅ 自动扩展
    - ✅ 低延迟查询
    - ✅ 支持元数据过滤

    示例:
        from loom.builtin.retriever.pinecone_store import PineconeVectorStore
        from loom.builtin.retriever.vector_store_config import PineconeConfig

        config = PineconeConfig.create(
            api_key="your-api-key",
            environment="us-west1-gcp",
            index_name="loom-docs"
        )

        vector_store = PineconeVectorStore(config)
        await vector_store.initialize()
    """

    def __init__(self, config: Dict[str, Any] | Any):
        """
        Parameters:
            config: PineconeConfig 对象或配置字典
        """
        if not PINECONE_AVAILABLE:
            raise ImportError(
                "Pinecone is not installed. "
                "Install with: pip install pinecone-client"
            )

        # 支持字典或 Pydantic 模型
        if hasattr(config, "model_dump"):
            self.config = config.model_dump()
        else:
            self.config = config

        self.api_key = self.config["api_key"]
        self.index_name = self.config.get("index_name", self.config.get("collection_name"))
        self.namespace = self.config.get("namespace")
        self.dimension = self.config.get("dimension", 1536)
        self.metric = self.config.get("metric", "cosine")

        self.pc: Optional[Pinecone] = None
        self.index = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化 Pinecone 连接和索引"""
        if self._initialized:
            return

        # 初始化 Pinecone 客户端
        self.pc = Pinecone(api_key=self.api_key)

        # 检查索引是否存在
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            # 创建索引（Serverless 规格）
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric=self.metric,
                spec=ServerlessSpec(
                    cloud=self.config.get("cloud", "aws"),
                    region=self.config.get("region", "us-west-2")
                )
            )

        # 连接到索引
        self.index = self.pc.Index(self.index_name)
        self._initialized = True

    async def add_vectors(
        self,
        vectors: List[List[float]],
        documents: List[Document]
    ) -> None:
        """
        添加向量到 Pinecone

        Parameters:
            vectors: 向量列表
            documents: 对应的文档列表
        """
        if not self._initialized:
            await self.initialize()

        # 构建 Pinecone 向量格式
        vectors_to_upsert = []
        for i, (vector, doc) in enumerate(zip(vectors, documents)):
            # 生成或使用文档 ID
            doc_id = doc.doc_id or f"doc_{i}"

            # 构建元数据
            metadata = {
                "content": doc.content,
                **(doc.metadata or {})
            }

            vectors_to_upsert.append({
                "id": doc_id,
                "values": vector,
                "metadata": metadata
            })

        # 批量上传（Pinecone 推荐批量大小 100）
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            self.index.upsert(
                vectors=batch,
                namespace=self.namespace
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

        # 构建过滤器（Pinecone 格式）
        pinecone_filter = None
        if filters:
            pinecone_filter = self._build_pinecone_filter(filters)

        # 执行查询
        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            namespace=self.namespace,
            filter=pinecone_filter
        )

        # 转换结果
        documents_with_scores = []
        for match in results.matches:
            # 提取内容和元数据
            content = match.metadata.pop("content", "")
            metadata = match.metadata

            doc = Document(
                content=content,
                metadata=metadata,
                score=match.score,
                doc_id=match.id
            )
            documents_with_scores.append((doc, match.score))

        return documents_with_scores

    async def delete(self, doc_ids: List[str]) -> None:
        """
        删除文档

        Parameters:
            doc_ids: 文档 ID 列表
        """
        if not self._initialized:
            await self.initialize()

        self.index.delete(
            ids=doc_ids,
            namespace=self.namespace
        )

    async def clear(self) -> None:
        """清空索引"""
        if not self._initialized:
            await self.initialize()

        # Pinecone 需要删除并重建索引来清空
        self.index.delete(delete_all=True, namespace=self.namespace)

    def _build_pinecone_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建 Pinecone 元数据过滤器

        Pinecone 过滤语法:
        {
            "field": {"$eq": "value"},
            "numeric_field": {"$gte": 10}
        }
        """
        pinecone_filter = {}

        for key, value in filters.items():
            if isinstance(value, dict):
                # 支持复杂查询（例如 {"price": {"$gte": 100}}）
                pinecone_filter[key] = value
            else:
                # 简单相等查询
                pinecone_filter[key] = {"$eq": value}

        return pinecone_filter

    async def close(self) -> None:
        """关闭连接"""
        # Pinecone 客户端自动管理连接
        self._initialized = False
