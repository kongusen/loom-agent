"""Qdrant 向量存储适配器"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import uuid

from loom.interfaces.retriever import Document
from loom.interfaces.vector_store import BaseVectorStore

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


class QdrantVectorStore(BaseVectorStore):
    """
    Qdrant 向量存储适配器

    特点:
    - ✅ 开源向量数据库
    - ✅ 支持本地部署和云服务
    - ✅ 高性能 Rust 实现
    - ✅ 丰富的过滤功能
    - ✅ 支持 gRPC 和 HTTP

    示例:
        from loom.builtin.retriever.qdrant_store import QdrantVectorStore
        from loom.builtin.retriever.vector_store_config import QdrantConfig

        # 本地 Qdrant
        config = QdrantConfig.create(
            host="localhost",
            port=6333,
            collection_name="loom_docs"
        )

        # Qdrant Cloud
        config = QdrantConfig.create(
            host="your-cluster.qdrant.io",
            api_key="your-api-key",
            https=True
        )

        vector_store = QdrantVectorStore(config)
        await vector_store.initialize()
    """

    def __init__(self, config: Dict[str, Any] | Any):
        """
        Parameters:
            config: QdrantConfig 对象或配置字典
        """
        if not QDRANT_AVAILABLE:
            raise ImportError(
                "Qdrant client is not installed. "
                "Install with: pip install qdrant-client"
            )

        # 支持字典或 Pydantic 模型
        if hasattr(config, "model_dump"):
            self.config = config.model_dump()
        else:
            self.config = config

        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 6333)
        self.collection_name = self.config.get("collection_name", "loom_documents")
        self.dimension = self.config.get("dimension", 1536)
        self.metric = self.config.get("metric", "cosine")
        self.api_key = self.config.get("api_key")
        self.https = self.config.get("https", False)
        self.prefer_grpc = self.config.get("prefer_grpc", False)

        self.client: Optional[QdrantClient] = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化 Qdrant 连接和集合"""
        if self._initialized:
            return

        # 初始化客户端
        self.client = QdrantClient(
            host=self.host,
            port=self.port,
            api_key=self.api_key,
            https=self.https,
            prefer_grpc=self.prefer_grpc,
        )

        # 检查集合是否存在
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            # 创建集合
            distance_map = {
                "cosine": Distance.COSINE,
                "euclidean": Distance.EUCLID,
                "dot_product": Distance.DOT,
            }

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.dimension,
                    distance=distance_map.get(self.metric, Distance.COSINE)
                )
            )

        self._initialized = True

    async def add_vectors(
        self,
        vectors: List[List[float]],
        documents: List[Document]
    ) -> None:
        """
        添加向量到 Qdrant

        Parameters:
            vectors: 向量列表
            documents: 对应的文档列表
        """
        if not self._initialized:
            await self.initialize()

        # 构建 Qdrant Point 格式
        points = []
        for i, (vector, doc) in enumerate(zip(vectors, documents)):
            # 生成或使用文档 ID
            point_id = doc.doc_id or str(uuid.uuid4())

            # 构建 payload（元数据 + 内容）
            payload = {
                "content": doc.content,
                **(doc.metadata or {})
            }

            # 添加分数（如果有）
            if doc.score is not None:
                payload["score"] = doc.score

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
            )

        # 批量上传
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
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

        # 构建过滤器
        qdrant_filter = None
        if filters:
            qdrant_filter = self._build_qdrant_filter(filters)

        # 执行查询
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qdrant_filter
        )

        # 转换结果
        documents_with_scores = []
        for hit in results:
            # 提取内容和元数据
            payload = hit.payload
            content = payload.pop("content", "")
            score = payload.pop("score", None)

            doc = Document(
                content=content,
                metadata=payload,
                score=hit.score,
                doc_id=str(hit.id)
            )
            documents_with_scores.append((doc, hit.score))

        return documents_with_scores

    async def delete(self, doc_ids: List[str]) -> None:
        """
        删除文档

        Parameters:
            doc_ids: 文档 ID 列表
        """
        if not self._initialized:
            await self.initialize()

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=doc_ids
        )

    async def clear(self) -> None:
        """清空集合"""
        if not self._initialized:
            await self.initialize()

        # 删除并重建集合
        self.client.delete_collection(collection_name=self.collection_name)
        await self.initialize()

    def _build_qdrant_filter(self, filters: Dict[str, Any]) -> Filter:
        """
        构建 Qdrant 过滤器

        示例:
            {"category": "python", "price": {"$gte": 100}}
            →
            Filter(
                must=[
                    FieldCondition(key="category", match=MatchValue(value="python")),
                    FieldCondition(key="price", range=Range(gte=100))
                ]
            )
        """
        conditions = []

        for key, value in filters.items():
            if isinstance(value, dict):
                # 复杂查询（范围/比较）
                # 简化实现：仅支持基本相等匹配
                # 生产环境可扩展支持 $gte, $lte, $in 等
                pass
            else:
                # 简单相等查询
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )

        return Filter(must=conditions) if conditions else None

    async def close(self) -> None:
        """关闭连接"""
        if self.client:
            self.client.close()
        self._initialized = False
