"""
向量数据库快速配置示例

展示如何快速连接和切换不同的向量数据库：
- Pinecone (云服务)
- Qdrant (本地/云)
- Milvus (本地/云)
- ChromaDB (本地/远程)

以及不同的 Embedding 服务：
- OpenAI
- Sentence Transformers (本地)
"""

import asyncio
from loom.components.agent import Agent
from loom.builtin.retriever.vector_store import VectorStoreRetriever
from loom.interfaces.retriever import Document

# 假设已有 LLM
from loom.llms.openai_llm import OpenAILLM


# ============================================================
# 示例 1: Pinecone + OpenAI Embedding
# ============================================================
async def example_pinecone():
    """Pinecone 云服务 + OpenAI Embedding"""
    print("=" * 60)
    print("示例 1: Pinecone + OpenAI Embedding")
    print("=" * 60 + "\n")

    from loom.builtin.retriever.pinecone_store import PineconeVectorStore
    from loom.builtin.embeddings import OpenAIEmbedding
    from loom.builtin.retriever.vector_store_config import PineconeConfig

    # 1. 配置 Pinecone
    pinecone_config = PineconeConfig.create(
        api_key="your-pinecone-api-key",
        environment="us-west1-gcp",
        index_name="loom-docs",
        dimension=1536
    )

    # 2. 创建向量存储
    vector_store = PineconeVectorStore(pinecone_config)
    await vector_store.initialize()

    # 3. 配置 Embedding
    embedding = OpenAIEmbedding(
        api_key="your-openai-api-key",
        model="text-embedding-3-small"
    )

    # 4. 创建检索器
    retriever = VectorStoreRetriever(
        vector_store=vector_store,
        embedding=embedding
    )

    # 5. 添加文档
    docs = [
        Document(
            content="Loom 是一个轻量级 AI Agent 框架",
            metadata={"source": "intro.md", "category": "framework"}
        ),
        Document(
            content="Loom 支持 RAG、工具系统和记忆管理",
            metadata={"source": "features.md", "category": "features"}
        ),
    ]
    await retriever.add_documents(docs)

    # 6. 检索
    results = await retriever.retrieve("Loom 框架", top_k=2)
    print(f"✅ Pinecone 检索到 {len(results)} 个文档\n")

    for i, doc in enumerate(results, 1):
        print(f"  [{i}] {doc.content[:50]}... (score: {doc.score:.2f})")

    await vector_store.close()
    print()


# ============================================================
# 示例 2: Qdrant (本地) + Sentence Transformers
# ============================================================
async def example_qdrant_local():
    """Qdrant 本地部署 + Sentence Transformers 本地模型"""
    print("=" * 60)
    print("示例 2: Qdrant (本地) + Sentence Transformers")
    print("=" * 60 + "\n")

    from loom.builtin.retriever.qdrant_store import QdrantVectorStore
    from loom.builtin.embeddings import SentenceTransformersEmbedding
    from loom.builtin.retriever.vector_store_config import QdrantConfig

    # 1. 配置 Qdrant（本地 Docker）
    qdrant_config = QdrantConfig.create(
        host="localhost",
        port=6333,
        collection_name="loom_docs",
        dimension=384  # MiniLM 模型维度
    )

    # 2. 创建向量存储
    vector_store = QdrantVectorStore(qdrant_config)
    await vector_store.initialize()

    # 3. 配置 Embedding（完全本地，无需 API）
    embedding = SentenceTransformersEmbedding(
        model_name="all-MiniLM-L6-v2",  # 轻量级快速模型
        device="cpu"  # 或 "cuda"/"mps"
    )

    # 4. 创建检索器
    retriever = VectorStoreRetriever(
        vector_store=vector_store,
        embedding=embedding
    )

    # 5. 添加文档
    docs = [
        Document(
            content="Loom provides a three-layer RAG architecture",
            metadata={"source": "rag.md", "language": "en"}
        ),
        Document(
            content="RAG includes ContextRetriever, DocumentSearchTool, and RAGPattern",
            metadata={"source": "rag_layers.md", "language": "en"}
        ),
    ]
    await retriever.add_documents(docs)

    # 6. 检索
    results = await retriever.retrieve("RAG architecture", top_k=2)
    print(f"✅ Qdrant 检索到 {len(results)} 个文档\n")

    for i, doc in enumerate(results, 1):
        print(f"  [{i}] {doc.content[:50]}... (score: {doc.score:.2f})")

    await vector_store.close()
    print()


# ============================================================
# 示例 3: Milvus (本地) + OpenAI Embedding
# ============================================================
async def example_milvus():
    """Milvus 本地部署 + OpenAI Embedding"""
    print("=" * 60)
    print("示例 3: Milvus (本地) + OpenAI Embedding")
    print("=" * 60 + "\n")

    from loom.builtin.retriever.milvus_store import MilvusVectorStore
    from loom.builtin.embeddings import OpenAIEmbedding
    from loom.builtin.retriever.vector_store_config import MilvusConfig

    # 1. 配置 Milvus
    milvus_config = MilvusConfig.create(
        host="localhost",
        port=19530,
        collection_name="loom_docs",
        dimension=1536,
        index_type="IVF_FLAT"  # 或 "HNSW" 更快但占内存
    )

    # 2. 创建向量存储
    vector_store = MilvusVectorStore(milvus_config)
    await vector_store.initialize()

    # 3. 配置 Embedding
    embedding = OpenAIEmbedding(
        api_key="your-openai-api-key",
        model="text-embedding-3-small"
    )

    # 4. 创建检索器
    retriever = VectorStoreRetriever(
        vector_store=vector_store,
        embedding=embedding
    )

    # 5. 添加大量文档（Milvus 适合海量数据）
    docs = [
        Document(
            content=f"Loom document {i}: Loom is a framework for building AI agents",
            metadata={"doc_id": i, "category": "docs"}
        )
        for i in range(100)  # 模拟大量文档
    ]
    await retriever.add_documents(docs)

    # 6. 检索
    results = await retriever.retrieve("Loom framework", top_k=5)
    print(f"✅ Milvus 检索到 {len(results)} 个文档\n")

    for i, doc in enumerate(results, 1):
        print(f"  [{i}] {doc.content[:40]}... (score: {doc.score:.2f})")

    await vector_store.close()
    print()


# ============================================================
# 示例 4: ChromaDB (本地持久化) + Sentence Transformers
# ============================================================
async def example_chroma_local():
    """ChromaDB 本地持久化 + Sentence Transformers（适合原型开发）"""
    print("=" * 60)
    print("示例 4: ChromaDB (本地) + Sentence Transformers")
    print("=" * 60 + "\n")

    from loom.builtin.retriever.chroma_store import ChromaVectorStore
    from loom.builtin.embeddings import SentenceTransformersEmbedding
    from loom.builtin.retriever.vector_store_config import ChromaConfig

    # 1. 配置 ChromaDB（本地持久化）
    chroma_config = ChromaConfig.create_local(
        persist_directory="./chroma_db",
        collection_name="loom_docs",
        dimension=384
    )

    # 2. 创建向量存储
    vector_store = ChromaVectorStore(chroma_config)
    await vector_store.initialize()

    # 3. 配置 Embedding
    embedding = SentenceTransformersEmbedding(
        model_name="all-MiniLM-L6-v2"
    )

    # 4. 创建检索器
    retriever = VectorStoreRetriever(
        vector_store=vector_store,
        embedding=embedding
    )

    # 5. 添加文档
    docs = [
        Document(
            content="Loom supports multiple vector databases: Pinecone, Qdrant, Milvus, ChromaDB",
            metadata={"source": "vector_stores.md"}
        ),
        Document(
            content="ChromaDB is great for rapid prototyping with local persistence",
            metadata={"source": "chroma_intro.md"}
        ),
    ]
    await retriever.add_documents(docs)

    # 6. 检索
    results = await retriever.retrieve("vector databases", top_k=2)
    print(f"✅ ChromaDB 检索到 {len(results)} 个文档\n")

    for i, doc in enumerate(results, 1):
        print(f"  [{i}] {doc.content[:50]}... (score: {doc.score:.2f})")

    await vector_store.close()
    print()


# ============================================================
# 示例 5: 快速切换向量数据库（配置化）
# ============================================================
async def example_config_based_switch():
    """基于配置文件快速切换向量数据库"""
    print("=" * 60)
    print("示例 5: 配置化切换向量数据库")
    print("=" * 60 + "\n")

    # 配置字典（可以从 YAML/JSON 加载）
    config = {
        "vector_store": {
            "type": "qdrant",  # 可切换为: pinecone, milvus, chroma
            "host": "localhost",
            "port": 6333,
            "collection_name": "loom_docs",
            "dimension": 384
        },
        "embedding": {
            "type": "sentence_transformers",  # 可切换为: openai
            "model_name": "all-MiniLM-L6-v2"
        }
    }

    # 根据配置创建向量存储
    vector_store = create_vector_store(config["vector_store"])
    await vector_store.initialize()

    # 根据配置创建 Embedding
    embedding = create_embedding(config["embedding"])

    # 创建检索器
    retriever = VectorStoreRetriever(
        vector_store=vector_store,
        embedding=embedding
    )

    print(f"✅ 使用 {config['vector_store']['type']} + {config['embedding']['type']}\n")

    await vector_store.close()


def create_vector_store(config: dict):
    """根据配置创建向量存储"""
    store_type = config["type"]

    if store_type == "pinecone":
        from loom.builtin.retriever.pinecone_store import PineconeVectorStore
        return PineconeVectorStore(config)
    elif store_type == "qdrant":
        from loom.builtin.retriever.qdrant_store import QdrantVectorStore
        return QdrantVectorStore(config)
    elif store_type == "milvus":
        from loom.builtin.retriever.milvus_store import MilvusVectorStore
        return MilvusVectorStore(config)
    elif store_type == "chroma":
        from loom.builtin.retriever.chroma_store import ChromaVectorStore
        return ChromaVectorStore(config)
    else:
        raise ValueError(f"Unknown vector store type: {store_type}")


def create_embedding(config: dict):
    """根据配置创建 Embedding"""
    embedding_type = config["type"]

    if embedding_type == "openai":
        from loom.builtin.embeddings import OpenAIEmbedding
        return OpenAIEmbedding(
            api_key=config["api_key"],
            model=config.get("model_name", "text-embedding-3-small")
        )
    elif embedding_type == "sentence_transformers":
        from loom.builtin.embeddings import SentenceTransformersEmbedding
        return SentenceTransformersEmbedding(
            model_name=config.get("model_name", "all-MiniLM-L6-v2")
        )
    else:
        raise ValueError(f"Unknown embedding type: {embedding_type}")


# ============================================================
# 主函数
# ============================================================
async def main():
    """运行所有示例（需要先启动对应的数据库服务）"""
    print("\n🚀 Loom 向量数据库快速配置示例\n")

    # 注意：运行这些示例需要：
    # 1. Pinecone: API Key
    # 2. Qdrant: docker run -p 6333:6333 qdrant/qdrant
    # 3. Milvus: docker-compose up (官方 docker-compose.yml)
    # 4. ChromaDB: 无需额外服务（本地持久化）

    # 选择要运行的示例
    examples = [
        # example_pinecone,          # 需要 Pinecone API Key
        # example_qdrant_local,      # 需要 Qdrant 服务
        # example_milvus,            # 需要 Milvus 服务
        example_chroma_local,        # 无需额外服务
        example_config_based_switch,
    ]

    for example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"❌ {example_func.__name__} 失败: {e}\n")

    print("✅ 所有示例完成！\n")
    print("💡 快速选择建议:")
    print("  - 快速原型开发: ChromaDB + Sentence Transformers（完全本地）")
    print("  - 生产环境（云）: Pinecone + OpenAI Embedding")
    print("  - 生产环境（自托管）: Qdrant/Milvus + OpenAI/Sentence Transformers")
    print("  - 海量数据: Milvus + 高性能 Embedding")
    print()


if __name__ == "__main__":
    asyncio.run(main())
