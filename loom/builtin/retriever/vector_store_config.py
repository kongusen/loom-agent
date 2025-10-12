"""向量数据库配置管理 - 统一的配置接口"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class VectorStoreConfig(BaseModel):
    """向量数据库配置基类"""
    store_type: str = Field(description="向量数据库类型: pinecone, qdrant, milvus, chroma")
    api_key: Optional[str] = Field(default=None, description="API Key（如果需要）")
    host: Optional[str] = Field(default=None, description="数据库地址")
    port: Optional[int] = Field(default=None, description="数据库端口")
    collection_name: str = Field(default="loom_documents", description="集合/索引名称")
    dimension: int = Field(default=1536, description="向量维度")
    metric: str = Field(default="cosine", description="相似度度量: cosine, euclidean, dot_product")
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="额外参数")


class PineconeConfig(VectorStoreConfig):
    """Pinecone 配置"""
    store_type: str = "pinecone"
    environment: str = Field(description="Pinecone 环境: us-west1-gcp, eu-west1-gcp, etc.")
    index_name: str = Field(description="索引名称")
    namespace: Optional[str] = Field(default=None, description="命名空间（可选）")

    @classmethod
    def create(
        cls,
        api_key: str,
        environment: str,
        index_name: str,
        namespace: Optional[str] = None,
        dimension: int = 1536,
    ) -> "PineconeConfig":
        """快速创建 Pinecone 配置"""
        return cls(
            api_key=api_key,
            environment=environment,
            index_name=index_name,
            namespace=namespace,
            dimension=dimension,
        )


class QdrantConfig(VectorStoreConfig):
    """Qdrant 配置"""
    store_type: str = "qdrant"
    host: str = Field(default="localhost", description="Qdrant 服务地址")
    port: int = Field(default=6333, description="Qdrant 端口")
    grpc_port: Optional[int] = Field(default=None, description="gRPC 端口（可选）")
    prefer_grpc: bool = Field(default=False, description="优先使用 gRPC")
    https: bool = Field(default=False, description="是否使用 HTTPS")

    @classmethod
    def create(
        cls,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "loom_documents",
        dimension: int = 1536,
        api_key: Optional[str] = None,
        https: bool = False,
    ) -> "QdrantConfig":
        """快速创建 Qdrant 配置"""
        return cls(
            host=host,
            port=port,
            collection_name=collection_name,
            dimension=dimension,
            api_key=api_key,
            https=https,
        )


class MilvusConfig(VectorStoreConfig):
    """Milvus 配置"""
    store_type: str = "milvus"
    host: str = Field(default="localhost", description="Milvus 服务地址")
    port: int = Field(default=19530, description="Milvus 端口")
    user: Optional[str] = Field(default=None, description="用户名")
    password: Optional[str] = Field(default=None, description="密码")
    secure: bool = Field(default=False, description="是否使用安全连接")
    index_type: str = Field(default="IVF_FLAT", description="索引类型: IVF_FLAT, HNSW, etc.")
    index_params: Dict[str, Any] = Field(default_factory=dict, description="索引参数")

    @classmethod
    def create(
        cls,
        host: str = "localhost",
        port: int = 19530,
        collection_name: str = "loom_documents",
        dimension: int = 1536,
        user: Optional[str] = None,
        password: Optional[str] = None,
        index_type: str = "IVF_FLAT",
    ) -> "MilvusConfig":
        """快速创建 Milvus 配置"""
        return cls(
            host=host,
            port=port,
            collection_name=collection_name,
            dimension=dimension,
            user=user,
            password=password,
            index_type=index_type,
        )


class ChromaConfig(VectorStoreConfig):
    """ChromaDB 配置"""
    store_type: str = "chroma"
    host: Optional[str] = Field(default=None, description="ChromaDB 服务地址（远程模式）")
    port: Optional[int] = Field(default=8000, description="ChromaDB 端口（远程模式）")
    persist_directory: Optional[str] = Field(default=None, description="持久化目录（本地模式）")
    client_type: str = Field(default="local", description="客户端类型: local, http")

    @classmethod
    def create_local(
        cls,
        persist_directory: str = "./chroma_db",
        collection_name: str = "loom_documents",
        dimension: int = 1536,
    ) -> "ChromaConfig":
        """创建本地 ChromaDB 配置"""
        return cls(
            persist_directory=persist_directory,
            collection_name=collection_name,
            dimension=dimension,
            client_type="local",
        )

    @classmethod
    def create_remote(
        cls,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "loom_documents",
        dimension: int = 1536,
    ) -> "ChromaConfig":
        """创建远程 ChromaDB 配置"""
        return cls(
            host=host,
            port=port,
            collection_name=collection_name,
            dimension=dimension,
            client_type="http",
        )


class EmbeddingConfig(BaseModel):
    """Embedding 模型配置"""
    provider: str = Field(description="提供商: openai, huggingface, cohere, sentence_transformers")
    model_name: str = Field(description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API Key（如果需要）")
    dimension: int = Field(default=1536, description="向量维度")
    batch_size: int = Field(default=32, description="批处理大小")
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="额外参数")

    @classmethod
    def openai(
        cls,
        api_key: str,
        model_name: str = "text-embedding-3-small",
        dimension: int = 1536,
    ) -> "EmbeddingConfig":
        """OpenAI Embedding 配置"""
        return cls(
            provider="openai",
            model_name=model_name,
            api_key=api_key,
            dimension=dimension,
        )

    @classmethod
    def huggingface(
        cls,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        dimension: int = 384,
        api_key: Optional[str] = None,
    ) -> "EmbeddingConfig":
        """HuggingFace Embedding 配置"""
        return cls(
            provider="huggingface",
            model_name=model_name,
            api_key=api_key,
            dimension=dimension,
        )

    @classmethod
    def sentence_transformers(
        cls,
        model_name: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
    ) -> "EmbeddingConfig":
        """Sentence Transformers 本地模型配置"""
        return cls(
            provider="sentence_transformers",
            model_name=model_name,
            dimension=dimension,
        )

    @classmethod
    def cohere(
        cls,
        api_key: str,
        model_name: str = "embed-english-v3.0",
        dimension: int = 1024,
    ) -> "EmbeddingConfig":
        """Cohere Embedding 配置"""
        return cls(
            provider="cohere",
            model_name=model_name,
            api_key=api_key,
            dimension=dimension,
        )
