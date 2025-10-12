"""Milvus 向量存储适配器"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from loom.interfaces.retriever import Document
from loom.interfaces.vector_store import BaseVectorStore

try:
    from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False


class MilvusVectorStore(BaseVectorStore):
    """
    Milvus 向量存储适配器

    特点:
    - ✅ 开源向量数据库
    - ✅ 支持海量数据（10B+ 向量）
    - ✅ 高性能检索
    - ✅ 多种索引类型（IVF_FLAT, HNSW, etc.）
    - ✅ 分布式架构

    示例:
        from loom.builtin.retriever.milvus_store import MilvusVectorStore
        from loom.builtin.retriever.vector_store_config import MilvusConfig

        # 本地 Milvus
        config = MilvusConfig.create(
            host="localhost",
            port=19530,
            collection_name="loom_docs"
        )

        # Zilliz Cloud (托管 Milvus)
        config = MilvusConfig.create(
            host="your-cluster.zillizcloud.com",
            port=443,
            user="username",
            password="password",
            secure=True
        )

        vector_store = MilvusVectorStore(config)
        await vector_store.initialize()
    """

    def __init__(self, config: Dict[str, Any] | Any):
        """
        Parameters:
            config: MilvusConfig 对象或配置字典
        """
        if not MILVUS_AVAILABLE:
            raise ImportError(
                "Milvus client is not installed. "
                "Install with: pip install pymilvus"
            )

        # 支持字典或 Pydantic 模型
        if hasattr(config, "model_dump"):
            self.config = config.model_dump()
        else:
            self.config = config

        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 19530)
        self.collection_name = self.config.get("collection_name", "loom_documents")
        self.dimension = self.config.get("dimension", 1536)
        self.metric = self.config.get("metric", "cosine")
        self.user = self.config.get("user")
        self.password = self.config.get("password")
        self.secure = self.config.get("secure", False)
        self.index_type = self.config.get("index_type", "IVF_FLAT")
        self.index_params = self.config.get("index_params", {})

        self.collection: Optional[Collection] = None
        self._initialized = False
        self._connection_alias = "default"

    async def initialize(self) -> None:
        """初始化 Milvus 连接和集合"""
        if self._initialized:
            return

        # 连接到 Milvus
        connections.connect(
            alias=self._connection_alias,
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            secure=self.secure
        )

        # 检查集合是否存在
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
        else:
            # 创建集合
            self.collection = self._create_collection()

        # 加载集合到内存
        self.collection.load()

        self._initialized = True

    def _create_collection(self) -> Collection:
        """创建 Milvus 集合"""
        # 定义 Schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Loom document collection"
        )

        # 创建集合
        collection = Collection(
            name=self.collection_name,
            schema=schema
        )

        # 创建索引
        metric_map = {
            "cosine": "COSINE",
            "euclidean": "L2",
            "dot_product": "IP",
        }

        index_params = {
            "metric_type": metric_map.get(self.metric, "COSINE"),
            "index_type": self.index_type,
            "params": self.index_params or {"nlist": 128}
        }

        collection.create_index(
            field_name="vector",
            index_params=index_params
        )

        return collection

    async def add_vectors(
        self,
        vectors: List[List[float]],
        documents: List[Document]
    ) -> None:
        """
        添加向量到 Milvus

        Parameters:
            vectors: 向量列表
            documents: 对应的文档列表
        """
        if not self._initialized:
            await self.initialize()

        # 构建数据
        ids = []
        contents = []
        metadatas = []

        for i, doc in enumerate(documents):
            doc_id = doc.doc_id or f"doc_{i}"
            ids.append(doc_id)
            contents.append(doc.content)

            # 构建 JSON 元数据
            metadata = doc.metadata or {}
            if doc.score is not None:
                metadata["score"] = doc.score
            metadatas.append(metadata)

        # 插入数据
        data = [
            ids,
            vectors,
            contents,
            metadatas
        ]

        self.collection.insert(data)
        self.collection.flush()  # 确保数据持久化

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

        # 构建搜索参数
        search_params = {
            "metric_type": self.collection.indexes[0].params["metric_type"],
            "params": {"nprobe": 10}
        }

        # 构建过滤表达式
        expr = None
        if filters:
            expr = self._build_milvus_filter(filters)

        # 执行搜索
        results = self.collection.search(
            data=[query_vector],
            anns_field="vector",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["content", "metadata"]
        )

        # 转换结果
        documents_with_scores = []
        for hits in results:
            for hit in hits:
                content = hit.entity.get("content", "")
                metadata = hit.entity.get("metadata", {})

                doc = Document(
                    content=content,
                    metadata=metadata,
                    score=hit.score,
                    doc_id=hit.id
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

        # 构建删除表达式
        ids_str = ", ".join([f'"{doc_id}"' for doc_id in doc_ids])
        expr = f"id in [{ids_str}]"

        self.collection.delete(expr)

    async def clear(self) -> None:
        """清空集合"""
        if not self._initialized:
            await self.initialize()

        # 删除并重建集合
        self.collection.drop()
        self.collection = self._create_collection()
        self.collection.load()

    def _build_milvus_filter(self, filters: Dict[str, Any]) -> str:
        """
        构建 Milvus 过滤表达式

        示例:
            {"category": "python", "price": 100}
            →
            'metadata["category"] == "python" and metadata["price"] == 100'

        注意: Milvus 使用 JSON 字段查询语法
        """
        conditions = []

        for key, value in filters.items():
            if isinstance(value, str):
                conditions.append(f'metadata["{key}"] == "{value}"')
            elif isinstance(value, (int, float)):
                conditions.append(f'metadata["{key}"] == {value}')
            elif isinstance(value, bool):
                val_str = "true" if value else "false"
                conditions.append(f'metadata["{key}"] == {val_str}')

        return " and ".join(conditions) if conditions else None

    async def close(self) -> None:
        """关闭连接"""
        if self.collection:
            self.collection.release()
        connections.disconnect(alias=self._connection_alias)
        self._initialized = False
