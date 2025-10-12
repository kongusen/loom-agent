# Loom 向量数据库配置指南

## 📋 目录

1. [支持的向量数据库](#支持的向量数据库)
2. [快速开始](#快速开始)
3. [向量数据库详细配置](#向量数据库详细配置)
4. [Embedding 服务配置](#embedding-服务配置)
5. [性能对比与选择建议](#性能对比与选择建议)
6. [生产环境部署](#生产环境部署)

---

## 支持的向量数据库

Loom 框架原生支持以下主流向量数据库：

| 数据库 | 类型 | 特点 | 适用场景 |
|--------|------|------|----------|
| **Pinecone** | 云服务 | ✅ 自动扩展<br/>✅ 低延迟<br/>✅ 完全托管 | 生产环境（云） |
| **Qdrant** | 本地/云 | ✅ 开源<br/>✅ 高性能 Rust 实现<br/>✅ 丰富过滤 | 自托管生产环境 |
| **Milvus** | 本地/云 | ✅ 开源<br/>✅ 海量数据支持<br/>✅ 分布式架构 | 大规模数据场景 |
| **ChromaDB** | 本地/远程 | ✅ 开源<br/>✅ 极简 API<br/>✅ 本地持久化 | 快速原型开发 |

---

## 快速开始

### 5 分钟上手（ChromaDB + 本地模型）

最快的方式是使用 ChromaDB（无需额外服务）+ Sentence Transformers（无需 API Key）：

```python
import asyncio
from loom.builtin.retriever.chroma_store import ChromaVectorStore
from loom.builtin.retriever.vector_store_config import ChromaConfig
from loom.builtin.embeddings import SentenceTransformersEmbedding
from loom.builtin.retriever.vector_store import VectorStoreRetriever
from loom.interfaces.retriever import Document

async def quick_start():
    # 1. 配置 ChromaDB（本地持久化）
    config = ChromaConfig.create_local(
        persist_directory="./my_vector_db",
        collection_name="documents"
    )

    # 2. 创建向量存储
    vector_store = ChromaVectorStore(config)
    await vector_store.initialize()

    # 3. 配置 Embedding（完全本地）
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
        Document(content="Your first document"),
        Document(content="Your second document"),
    ]
    await retriever.add_documents(docs)

    # 6. 检索
    results = await retriever.retrieve("first", top_k=1)
    print(results[0].content)

asyncio.run(quick_start())
```

**安装依赖**：
```bash
pip install chromadb sentence-transformers
```

---

## 向量数据库详细配置

### 1. Pinecone（云服务）

#### 特点
- 完全托管的云向量数据库
- 自动扩展和优化
- 低延迟查询
- 适合生产环境

#### 安装
```bash
pip install pinecone-client
```

#### 配置示例
```python
from loom.builtin.retriever.pinecone_store import PineconeVectorStore
from loom.builtin.retriever.vector_store_config import PineconeConfig

# 方式 1: 使用配置类
config = PineconeConfig.create(
    api_key="your-api-key",
    environment="us-west1-gcp",  # 或其他区域
    index_name="loom-docs",
    dimension=1536
)

# 方式 2: 直接传入字典
config = {
    "api_key": "your-api-key",
    "environment": "us-west1-gcp",
    "index_name": "loom-docs",
    "dimension": 1536,
    "metric": "cosine"  # cosine, euclidean, dot_product
}

vector_store = PineconeVectorStore(config)
await vector_store.initialize()
```

#### 获取 API Key
1. 访问 [Pinecone Console](https://app.pinecone.io/)
2. 创建项目
3. 复制 API Key 和 Environment

---

### 2. Qdrant（本地/云）

#### 特点
- 开源高性能向量数据库
- Rust 实现，速度快
- 支持本地部署和云服务
- 丰富的元数据过滤

#### 安装
```bash
pip install qdrant-client
```

#### 本地部署（Docker）
```bash
docker run -p 6333:6333 qdrant/qdrant
```

#### 配置示例
```python
from loom.builtin.retriever.qdrant_store import QdrantVectorStore
from loom.builtin.retriever.vector_store_config import QdrantConfig

# 本地 Qdrant
config = QdrantConfig.create(
    host="localhost",
    port=6333,
    collection_name="loom_docs",
    dimension=384
)

# Qdrant Cloud
config = QdrantConfig.create(
    host="your-cluster.qdrant.io",
    port=6333,
    api_key="your-api-key",
    https=True,
    collection_name="loom_docs"
)

vector_store = QdrantVectorStore(config)
await vector_store.initialize()
```

#### Qdrant Cloud
1. 访问 [Qdrant Cloud](https://cloud.qdrant.io/)
2. 创建集群
3. 获取连接信息

---

### 3. Milvus（本地/云）

#### 特点
- 开源分布式向量数据库
- 支持海量数据（10B+ 向量）
- 多种索引类型（IVF_FLAT, HNSW, etc.）
- 适合大规模生产环境

#### 安装
```bash
pip install pymilvus
```

#### 本地部署（Docker Compose）
```bash
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d
```

#### 配置示例
```python
from loom.builtin.retriever.milvus_store import MilvusVectorStore
from loom.builtin.retriever.vector_store_config import MilvusConfig

# 本地 Milvus
config = MilvusConfig.create(
    host="localhost",
    port=19530,
    collection_name="loom_docs",
    dimension=1536,
    index_type="IVF_FLAT"  # 或 "HNSW" 更快
)

# Zilliz Cloud (托管 Milvus)
config = MilvusConfig.create(
    host="your-cluster.zillizcloud.com",
    port=443,
    user="username",
    password="password",
    secure=True,
    collection_name="loom_docs"
)

vector_store = MilvusVectorStore(config)
await vector_store.initialize()
```

#### 索引类型选择
- **IVF_FLAT**: 平衡性能和召回率
- **HNSW**: 高性能，适合实时查询
- **IVF_SQ8**: 内存优化版本

---

### 4. ChromaDB（本地/远程）

#### 特点
- 开源嵌入式向量数据库
- 极简 API
- 支持本地持久化
- 适合快速原型开发

#### 安装
```bash
pip install chromadb
```

#### 配置示例
```python
from loom.builtin.retriever.chroma_store import ChromaVectorStore
from loom.builtin.retriever.vector_store_config import ChromaConfig

# 本地持久化模式
config = ChromaConfig.create_local(
    persist_directory="./chroma_db",
    collection_name="loom_docs"
)

# 内存模式（不持久化）
config = ChromaConfig.create_local(
    persist_directory=None,  # 内存模式
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
```

#### 启动 ChromaDB 服务器
```bash
chroma run --host localhost --port 8000
```

---

## Embedding 服务配置

### 1. OpenAI Embedding

#### 特点
- 高质量向量
- 多种模型选择
- 需要 API Key

#### 安装
```bash
pip install openai
```

#### 配置示例
```python
from loom.builtin.embeddings import OpenAIEmbedding

# text-embedding-3-small (1536 维, 最便宜)
embedding = OpenAIEmbedding(
    api_key="your-openai-api-key",
    model="text-embedding-3-small"
)

# text-embedding-3-large (3072 维, 最强)
embedding = OpenAIEmbedding(
    api_key="your-openai-api-key",
    model="text-embedding-3-large",
    dimensions=3072
)

# 使用代理
embedding = OpenAIEmbedding(
    api_key="your-api-key",
    model="text-embedding-3-small",
    base_url="https://your-proxy.com/v1"
)
```

#### 成本（2024 年价格）
- `text-embedding-3-small`: $0.02 / 1M tokens
- `text-embedding-3-large`: $0.13 / 1M tokens

---

### 2. Sentence Transformers（本地模型）

#### 特点
- 完全本地运行
- 无需 API Key
- 支持 GPU 加速
- 多语言模型

#### 安装
```bash
pip install sentence-transformers
```

#### 推荐模型

| 模型 | 维度 | 大小 | 速度 | 适用场景 |
|------|------|------|------|----------|
| all-MiniLM-L6-v2 | 384 | 80MB | 快 | 快速原型、英文 |
| all-mpnet-base-v2 | 768 | 420MB | 中 | 高质量、英文 |
| paraphrase-multilingual-MiniLM-L12-v2 | 384 | 420MB | 快 | 多语言 |
| paraphrase-multilingual-mpnet-base-v2 | 768 | 1GB | 中 | 高质量多语言 |

#### 配置示例
```python
from loom.builtin.embeddings import SentenceTransformersEmbedding

# 英文快速模型
embedding = SentenceTransformersEmbedding(
    model_name="all-MiniLM-L6-v2",
    device="cpu"  # 或 "cuda" 使用 GPU
)

# 多语言模型
embedding = SentenceTransformersEmbedding(
    model_name="paraphrase-multilingual-MiniLM-L12-v2",
    device="cpu"
)

# 使用 GPU 加速
embedding = SentenceTransformersEmbedding(
    model_name="all-mpnet-base-v2",
    device="cuda",  # 需要 CUDA
    batch_size=64   # 增加批处理大小
)
```

---

## 性能对比与选择建议

### 向量数据库对比

| 特性 | Pinecone | Qdrant | Milvus | ChromaDB |
|------|----------|--------|--------|----------|
| **部署方式** | 云服务 | 本地/云 | 本地/云 | 本地/远程 |
| **开源** | ❌ | ✅ | ✅ | ✅ |
| **性能** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **可扩展性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **易用性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **成本** | 按量付费 | 自托管/付费云 | 自托管/付费云 | 免费 |
| **适合数据量** | 任意 | 1M-100M | 10M-10B+ | <1M |

### Embedding 服务对比

| 特性 | OpenAI | Sentence Transformers |
|------|--------|----------------------|
| **部署方式** | API 调用 | 本地模型 |
| **成本** | 按 token 付费 | 免费 |
| **质量** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **速度** | 取决于网络 | 快（本地） |
| **隐私** | 数据传输到 OpenAI | 完全本地 |

### 场景选择建议

#### 场景 1: 快速原型开发
**推荐**: ChromaDB + Sentence Transformers
- ✅ 无需外部服务
- ✅ 完全免费
- ✅ 5 分钟上手

```python
config = ChromaConfig.create_local(persist_directory="./db")
embedding = SentenceTransformersEmbedding("all-MiniLM-L6-v2")
```

#### 场景 2: 生产环境（云部署）
**推荐**: Pinecone + OpenAI Embedding
- ✅ 完全托管
- ✅ 自动扩展
- ✅ 高可用

```python
config = PineconeConfig.create(api_key="...", index_name="prod")
embedding = OpenAIEmbedding(api_key="...", model="text-embedding-3-small")
```

#### 场景 3: 生产环境（自托管）
**推荐**: Qdrant + OpenAI Embedding
- ✅ 完全控制
- ✅ 高性能
- ✅ 成本优化

```python
config = QdrantConfig.create(host="your-qdrant-server", port=6333)
embedding = OpenAIEmbedding(api_key="...", model="text-embedding-3-small")
```

#### 场景 4: 海量数据（10M+ 向量）
**推荐**: Milvus + OpenAI Embedding
- ✅ 分布式架构
- ✅ 高性能索引
- ✅ 成熟生态

```python
config = MilvusConfig.create(host="...", index_type="HNSW")
embedding = OpenAIEmbedding(api_key="...", model="text-embedding-3-small")
```

#### 场景 5: 完全本地部署（隐私要求）
**推荐**: Qdrant + Sentence Transformers
- ✅ 无外部依赖
- ✅ 数据不出本地
- ✅ 高性能

```python
config = QdrantConfig.create(host="localhost", port=6333)
embedding = SentenceTransformersEmbedding("all-mpnet-base-v2", device="cuda")
```

---

## 生产环境部署

### 1. Docker Compose 快速部署

#### Qdrant
```yaml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
```

#### Milvus
```bash
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml
docker-compose up -d
```

### 2. 环境变量配置

创建 `.env` 文件：
```bash
# 向量数据库
VECTOR_STORE_TYPE=qdrant
VECTOR_STORE_HOST=localhost
VECTOR_STORE_PORT=6333
VECTOR_STORE_COLLECTION=loom_docs

# Embedding
EMBEDDING_TYPE=openai
OPENAI_API_KEY=your-api-key
EMBEDDING_MODEL=text-embedding-3-small
```

加载配置：
```python
import os
from dotenv import load_dotenv

load_dotenv()

config = {
    "type": os.getenv("VECTOR_STORE_TYPE"),
    "host": os.getenv("VECTOR_STORE_HOST"),
    "port": int(os.getenv("VECTOR_STORE_PORT")),
    "collection_name": os.getenv("VECTOR_STORE_COLLECTION"),
}
```

### 3. 监控与日志

#### 添加日志
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 在检索前后添加日志
logger.info(f"检索查询: {query}")
results = await retriever.retrieve(query, top_k=5)
logger.info(f"检索到 {len(results)} 个结果")
```

#### Prometheus 指标（示例）
```python
from prometheus_client import Counter, Histogram

retrieval_counter = Counter('rag_retrievals_total', 'Total RAG retrievals')
retrieval_latency = Histogram('rag_retrieval_latency_seconds', 'RAG retrieval latency')

with retrieval_latency.time():
    results = await retriever.retrieve(query)
retrieval_counter.inc()
```

---

## 常见问题

### Q1: 如何选择向量维度？

**推荐维度**:
- **384**: Sentence Transformers MiniLM 系列（快速）
- **768**: Sentence Transformers MPNet 系列（高质量）
- **1536**: OpenAI text-embedding-3-small（平衡）
- **3072**: OpenAI text-embedding-3-large（最强）

**注意**: 向量数据库的维度配置必须与 Embedding 模型一致！

### Q2: 向量数据库如何选择索引类型？

**Milvus 索引选择**:
- **IVF_FLAT**: 默认，平衡性能和召回率
- **HNSW**: 高性能，适合实时查询（占内存更多）
- **IVF_SQ8**: 量化版本，节省内存

### Q3: 如何处理多语言文档？

**推荐**:
使用多语言 Embedding 模型：
```python
embedding = SentenceTransformersEmbedding(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)
```

或在元数据中标记语言并过滤：
```python
Document(content="...", metadata={"language": "zh"})
results = await retriever.retrieve(query, filters={"language": "zh"})
```

### Q4: 向量数据库连接失败怎么办？

**检查清单**:
1. 确认数据库服务已启动 (`docker ps`)
2. 检查端口是否正确（Qdrant: 6333, Milvus: 19530）
3. 检查防火墙规则
4. 查看数据库日志 (`docker logs <container>`)

### Q5: 如何优化检索性能？

**优化建议**:
1. **使用 GPU 加速 Embedding** (`device="cuda"`)
2. **增加批处理大小** (`batch_size=64`)
3. **选择高性能索引** (Milvus HNSW)
4. **调整 top_k 值**（减少不必要的结果）
5. **使用元数据过滤**（减少搜索空间）

---

## 进一步学习

### 示例代码
- `examples/vector_store_quickstart.py` - 向量数据库快速配置示例
- `examples/rag_basic_example.py` - RAG 完整示例

### 相关文档
- `LOOM_RAG_GUIDE.md` - RAG 完整指南
- `LOOM_UNIFIED_DEVELOPER_GUIDE.md` - Loom 框架完整文档

### 官方文档
- [Pinecone Docs](https://docs.pinecone.io/)
- [Qdrant Docs](https://qdrant.tech/documentation/)
- [Milvus Docs](https://milvus.io/docs)
- [ChromaDB Docs](https://docs.trychroma.com/)

---

Happy building with Loom! 🚀
