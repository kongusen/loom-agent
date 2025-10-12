# Loom RAG 完整指南

## 📋 目录

1. [RAG 概述](#rag-概述)
2. [三层 RAG 架构](#三层-rag-架构)
3. [快速开始](#快速开始)
4. [核心组件：ContextRetriever](#核心组件contextretriever)
5. [工具版本：DocumentSearchTool](#工具版本documentsearchtool)
6. [高级模式：RAGPattern](#高级模式ragpattern)
7. [检索器实现](#检索器实现)
8. [最佳实践](#最佳实践)
9. [常见问题](#常见问题)

---

## RAG 概述

**RAG (Retrieval-Augmented Generation)** 是一种通过检索外部知识库来增强 LLM 生成能力的技术。

### 为什么需要 RAG？

- **解决知识时效性问题**：LLM 训练数据有截止日期
- **注入私有知识**：企业内部文档、代码库、专业领域知识
- **减少幻觉**：基于事实文档生成答案
- **可追溯性**：提供信息来源

### Loom 的 RAG 设计理念

Loom 提供了 **三层 RAG 架构**，满足不同场景需求：

```
┌─────────────────────────────────────────────────┐
│  Layer 3: RAG Patterns (高级编排)               │
│  - RAGPattern, MultiQueryRAG, HierarchicalRAG   │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Layer 2: Tool (工具检索)                       │
│  - DocumentSearchTool (LLM 决定何时检索)        │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Layer 1: Core Component (自动检索)             │
│  - ContextRetriever (每次查询自动检索)          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Foundation: Retriever Interface                │
│  - BaseRetriever, Document, BaseVectorStore     │
└─────────────────────────────────────────────────┘
```

---

## 三层 RAG 架构

### 1️⃣ 核心组件 - ContextRetriever

**特点**：
- ✅ 自动检索（每次查询前）
- ✅ 零侵入集成到 Agent
- ✅ 适用于知识库问答

**何时使用**：
- 所有查询都需要检索支持
- 知识库是主要信息来源
- 希望对用户透明

**示例**：
```python
context_retriever = ContextRetriever(
    retriever=retriever,
    top_k=3,
    inject_as="system"
)

agent = Agent(
    llm=llm,
    context_retriever=context_retriever  # 自动启用 RAG
)

# 每次查询都会自动检索相关文档
response = await agent.run("Loom 是什么？")
```

### 2️⃣ 工具版本 - DocumentSearchTool

**特点**：
- ✅ LLM 决定何时检索
- ✅ 可与其他工具组合
- ✅ 灵活的检索时机

**何时使用**：
- 并非所有查询都需要检索
- 需要多次检索不同内容
- 与其他工具配合使用

**示例**：
```python
doc_search = DocumentSearchTool(retriever)

agent = Agent(
    llm=llm,
    tools=[doc_search, Calculator(), WebSearch()]  # 多工具
)

# Agent 自己决定是否需要检索文档
response = await agent.run("计算 10*20 并查询 Loom 的 RAG 能力")
```

### 3️⃣ 高级模式 - RAGPattern

**特点**：
- ✅ 完整控制 RAG 流程
- ✅ 支持 Re-ranking
- ✅ 多查询、层次化检索

**何时使用**：
- 需要自定义 RAG 流程
- 需要 Re-ranking 提升精度
- 复杂的检索策略

**示例**：
```python
# 基础 RAG
rag = RAGPattern(
    agent=agent,
    retriever=retriever,
    reranker=my_reranker,  # 可选的重排序
    top_k=10,
    rerank_top_k=3
)

# 多查询 RAG
multi_rag = MultiQueryRAG(
    agent=agent,
    retriever=retriever,
    query_count=3  # 生成 3 个查询变体
)

# 层次化 RAG
hierarchical_rag = HierarchicalRAG(
    agent=agent,
    document_retriever=doc_retriever,
    paragraph_retriever=para_retriever
)
```

---

## 快速开始

### 5 分钟快速上手

```python
import asyncio
from loom.components.agent import Agent
from loom.builtin.retriever.in_memory import InMemoryRetriever
from loom.core.context_retriever import ContextRetriever
from loom.interfaces.retriever import Document
from loom.llms.openai_llm import OpenAILLM

async def main():
    # 1. 创建检索器并添加文档
    retriever = InMemoryRetriever()
    await retriever.add_documents([
        Document(
            content="Loom 是一个 AI Agent 开发框架",
            metadata={"source": "intro.md"}
        ),
        Document(
            content="Loom 支持 RAG、工具和记忆管理",
            metadata={"source": "features.md"}
        ),
    ])

    # 2. 创建 ContextRetriever
    context_retriever = ContextRetriever(
        retriever=retriever,
        top_k=2
    )

    # 3. 创建 Agent
    agent = Agent(
        llm=OpenAILLM(model="gpt-4"),
        context_retriever=context_retriever
    )

    # 4. 查询（自动检索）
    response = await agent.run("Loom 有什么功能？")
    print(response)

asyncio.run(main())
```

---

## 核心组件：ContextRetriever

### 完整配置

```python
from loom.core.context_retriever import ContextRetriever

context_retriever = ContextRetriever(
    retriever=my_retriever,           # BaseRetriever 实例
    top_k=3,                          # 检索文档数量
    similarity_threshold=0.7,         # 相似度阈值 (0-1)
    auto_retrieve=True,               # 是否自动检索
    inject_as="system",               # 注入方式: "system" 或 "user_prefix"
)
```

### 注入方式对比

#### 1. System Message 注入 (`inject_as="system"`)

**优点**：
- 文档作为系统背景知识
- 不影响用户消息结构
- 适合知识库问答

**示例**：
```python
context_retriever = ContextRetriever(
    retriever=retriever,
    inject_as="system"
)

# 实际消息序列:
# [
#   {"role": "system", "content": "You are an assistant..."},
#   {"role": "system", "content": "[Document 1] ...\n[Document 2] ..."},  # 注入
#   {"role": "user", "content": "What is Loom?"}
# ]
```

#### 2. User Prefix 注入 (`inject_as="user_prefix"`)

**优点**：
- 文档与查询紧密关联
- 更明确的上下文关系
- 适合需要明确引用文档的场景

**示例**：
```python
context_retriever = ContextRetriever(
    retriever=retriever,
    inject_as="user_prefix"
)

# 实际消息:
# {"role": "user", "content": "Context:\n[Document 1] ...\n\nQuestion: What is Loom?"}
```

### 相似度阈值

```python
# 严格过滤（只保留高度相关的文档）
context_retriever = ContextRetriever(
    retriever=retriever,
    similarity_threshold=0.8  # 只保留 score >= 0.8 的文档
)

# 宽松过滤（关键词匹配，无阈值）
context_retriever = ContextRetriever(
    retriever=retriever,
    similarity_threshold=0.0  # 保留所有匹配的文档
)
```

### 检索指标

```python
agent = Agent(
    llm=llm,
    context_retriever=context_retriever
)

response = await agent.run("Query")

# 查看检索次数
metrics = agent.get_metrics()
print(f"检索次数: {metrics.retrievals}")
print(f"LLM 调用: {metrics.llm_calls}")
```

---

## 工具版本：DocumentSearchTool

### 基本使用

```python
from loom.builtin.tools.document_search import DocumentSearchTool

# 创建工具
doc_search = DocumentSearchTool(retriever)

# 添加到 Agent 工具列表
agent = Agent(
    llm=llm,
    tools=[doc_search, other_tools...]
)

# Agent 会自己决定何时调用
response = await agent.run("Search for Python docs and calculate 10*20")
```

### 工具参数

```python
class DocumentSearchInput(BaseModel):
    query: str = Field(description="Search query for documents")
    top_k: int = Field(default=3, description="Number of documents to retrieve")
```

LLM 会根据需要填充这些参数：

```json
{
  "tool_call": {
    "name": "search_documents",
    "arguments": {
      "query": "Loom RAG capabilities",
      "top_k": 5
    }
  }
}
```

### 输出格式

```
Found 3 relevant document(s) for: 'Loom RAG'

**Document 1**
Source: loom_rag.md
Relevance: 95.00%

Loom 支持三层 RAG 架构：核心组件、工具和高级模式...

**Document 2**
Source: features.md
Relevance: 87.00%

RAG 能力包括自动检索和工具检索...
```

### 与其他工具组合

```python
from loom.builtin.tools.calculator import Calculator
from loom.builtin.tools.web_search import WebSearch

agent = Agent(
    llm=llm,
    tools=[
        DocumentSearchTool(local_retriever),  # 本地文档
        WebSearch(),                          # 网络搜索
        Calculator(),                         # 计算
    ]
)

# Agent 会智能选择工具
response = await agent.run(
    "查询 Loom 的 RAG 文档，搜索最新的 RAG 论文，计算检索时间"
)
```

---

## 高级模式：RAGPattern

### 1. RAGPattern - 基础 RAG 流程

**完整流程**：
1. 检索 (Retrieve) - 获取 top_k 文档
2. 重排序 (Rerank) - 可选，提升精度
3. 生成 (Generate) - 基于文档生成答案

**示例**：
```python
from loom.patterns.rag import RAGPattern

# 定义 reranker（可选）
async def my_reranker(query: str, docs: List[Document]) -> List[Document]:
    # 使用 Cross-Encoder 或其他模型重新打分
    # ...
    return reranked_docs

rag = RAGPattern(
    agent=agent,
    retriever=retriever,
    reranker=my_reranker,  # 可选
    top_k=10,              # 初始检索 10 个
    rerank_top_k=3         # 重排序后保留 3 个
)

response = await rag.run("What is Loom?")
```

### 2. MultiQueryRAG - 多查询变体

**原理**：生成多个查询变体，分别检索后合并结果，提高召回率。

**适用场景**：
- 复杂/模糊的查询
- 需要多角度理解
- 提高召回率

**示例**：
```python
from loom.patterns.rag import MultiQueryRAG

multi_rag = MultiQueryRAG(
    agent=agent,
    retriever=retriever,
    query_count=3,    # 生成 3 个查询变体
    top_k=9,          # 每个查询检索 3 个 (9/3=3)
    rerank_top_k=5    # 合并去重后保留 5 个
)

# 原始查询: "上下文工程和提示工程的区别？"
# 生成变体:
#   1. "上下文工程和提示工程的区别？"
#   2. "What is context engineering vs prompt engineering?"
#   3. "上下文工程的优势是什么？"

response = await multi_rag.run("上下文工程和提示工程的区别？")
```

### 3. HierarchicalRAG - 层次化检索

**原理**：先检索相关文档（粗粒度），再在文档内检索段落（细粒度）。

**适用场景**：
- 文档很长
- 需要精确定位
- 两级索引结构

**示例**：
```python
from loom.patterns.rag import HierarchicalRAG

hierarchical_rag = HierarchicalRAG(
    agent=agent,
    document_retriever=doc_retriever,      # 文档级检索器
    paragraph_retriever=para_retriever,    # 段落级检索器
    doc_top_k=5,                           # 检索 5 个文档
    para_top_k=3                           # 在文档内检索 3 个段落
)

response = await hierarchical_rag.run("Loom 的高级模式有哪些？")
```

---

## 检索器实现

### BaseRetriever 接口

```python
from loom.interfaces.retriever import BaseRetriever, Document

class MyRetriever(BaseRetriever):
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """检索相关文档"""
        # 实现检索逻辑
        return documents

    async def add_documents(self, documents: List[Document]) -> None:
        """添加文档到索引"""
        pass
```

### 内置检索器

#### 1. InMemoryRetriever（内存检索器）

**特点**：
- ✅ 无外部依赖
- ✅ 适合测试/开发
- ❌ 简单的关键词匹配（非向量检索）

**使用**：
```python
from loom.builtin.retriever.in_memory import InMemoryRetriever

retriever = InMemoryRetriever()

# 添加文档
await retriever.add_documents([
    Document(content="...", metadata={"source": "doc1.md"}),
    Document(content="...", metadata={"source": "doc2.md"}),
])

# 检索
docs = await retriever.retrieve("query", top_k=3)
```

#### 2. VectorStoreRetriever（向量检索器）

**特点**：
- ✅ 基于语义相似度
- ✅ 支持多种向量数据库
- ✅ 生产环境推荐

**使用**：
```python
from loom.builtin.retriever.vector_store import VectorStoreRetriever
from loom.interfaces.vector_store import BaseVectorStore, BaseEmbedding

# 实现向量存储和嵌入
vector_store = MyVectorStore()  # 例如 Pinecone, Milvus, ChromaDB
embedding = OpenAIEmbedding()   # 或 HuggingFaceEmbedding

retriever = VectorStoreRetriever(
    vector_store=vector_store,
    embedding=embedding
)

# 添加文档（自动向量化）
await retriever.add_documents([
    Document(content="...", metadata={"source": "doc1.md"}),
])

# 检索（语义相似度）
docs = await retriever.retrieve("query", top_k=5)
```

### 向量存储接口

```python
from loom.interfaces.vector_store import BaseVectorStore

class MyVectorStore(BaseVectorStore):
    async def add_vectors(
        self,
        vectors: List[List[float]],
        documents: List[Document]
    ) -> None:
        """添加向量到存储"""
        pass

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """搜索相似向量"""
        pass
```

### Embedding 接口

```python
from loom.interfaces.embedding import BaseEmbedding

class MyEmbedding(BaseEmbedding):
    async def embed_query(self, text: str) -> List[float]:
        """对查询文本进行向量化"""
        pass

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量向量化文档"""
        pass
```

---

## 最佳实践

### 1. 选择合适的 RAG 层级

```python
# ✅ 知识库问答 → ContextRetriever
context_retriever = ContextRetriever(retriever=retriever)
agent = Agent(llm=llm, context_retriever=context_retriever)

# ✅ 多工具场景 → DocumentSearchTool
doc_tool = DocumentSearchTool(retriever)
agent = Agent(llm=llm, tools=[doc_tool, calc, web_search])

# ✅ 复杂 RAG 流程 → RAGPattern
rag = MultiQueryRAG(agent, retriever, query_count=3)
response = await rag.run(query)
```

### 2. 文档分块策略

```python
# ❌ 不好：文档太长，超过 context window
Document(content="整本书的内容...", metadata={...})

# ✅ 好：合理分块
def chunk_document(text: str, chunk_size: int = 500) -> List[str]:
    """按字符数分块"""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

chunks = chunk_document(long_text)
documents = [
    Document(content=chunk, metadata={"source": "book.md", "chunk_id": i})
    for i, chunk in enumerate(chunks)
]
```

### 3. 元数据管理

```python
# ✅ 丰富的元数据便于过滤和追溯
Document(
    content="...",
    metadata={
        "source": "api_docs.md",
        "section": "authentication",
        "category": "backend",
        "last_updated": "2024-01-15",
        "author": "dev-team"
    }
)

# 带过滤的检索
docs = await retriever.retrieve(
    query="authentication",
    filters={"category": "backend"}  # 只检索后端文档
)
```

### 4. Re-ranking 策略

```python
# 简单 Re-ranker: 基于关键词密度
async def keyword_reranker(query: str, docs: List[Document]) -> List[Document]:
    query_terms = set(query.lower().split())
    for doc in docs:
        matches = sum(1 for word in doc.content.lower().split() if word in query_terms)
        doc.score = matches / len(doc.content.split())
    docs.sort(key=lambda d: d.score or 0, reverse=True)
    return docs

# 高级 Re-ranker: Cross-Encoder
from sentence_transformers import CrossEncoder

cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

async def cross_encoder_reranker(query: str, docs: List[Document]) -> List[Document]:
    pairs = [[query, doc.content] for doc in docs]
    scores = cross_encoder.predict(pairs)
    for doc, score in zip(docs, scores):
        doc.score = score
    docs.sort(key=lambda d: d.score or 0, reverse=True)
    return docs
```

### 5. 监控与调试

```python
# 1. 检索日志
class LoggingRetriever(BaseRetriever):
    def __init__(self, retriever: BaseRetriever):
        self.retriever = retriever

    async def retrieve(self, query: str, top_k: int = 5, **kwargs) -> List[Document]:
        docs = await self.retriever.retrieve(query, top_k, **kwargs)
        print(f"[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(docs)} docs with scores: {[d.score for d in docs]}")
        return docs

# 2. 流式事件监听
async for event in agent.stream("query"):
    if event.type == "retrieval_complete":
        print(f"检索完成，文档数: {event.metadata['doc_count']}")
    elif event.type == "text_delta":
        print(event.content, end="")

# 3. 指标收集
metrics = agent.get_metrics()
print(f"检索次数: {metrics.retrievals}")
print(f"平均检索时间: {metrics.avg_retrieval_time}")
```

---

## 常见问题

### Q1: ContextRetriever 和 DocumentSearchTool 有什么区别？

**ContextRetriever**（核心组件）：
- 每次查询**自动**检索
- 对用户透明
- 适合知识库问答

**DocumentSearchTool**（工具）：
- LLM **决定**何时检索
- 可以多次检索不同内容
- 适合复杂任务

### Q2: 如何选择 top_k？

经验值：
- **知识库问答**：top_k = 3-5
- **长文档检索**：top_k = 5-10（配合 Re-ranking）
- **多查询 RAG**：top_k = 每个查询 2-3 个

### Q3: 何时使用 Re-ranking？

**需要 Re-ranking**：
- 初始检索召回较多文档（top_k > 10）
- 需要提高精度
- 有专门的排序模型

**不需要 Re-ranking**：
- 文档数量少
- 向量检索已经很准确
- 性能优先

### Q4: 如何处理多语言文档？

```python
# 1. 使用多语言 Embedding 模型
from sentence_transformers import SentenceTransformer

multilingual_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 2. 在元数据中标记语言
Document(
    content="Loom is an AI agent framework",
    metadata={"language": "en"}
)

Document(
    content="Loom 是一个 AI Agent 框架",
    metadata={"language": "zh"}
)

# 3. 带语言过滤的检索
docs = await retriever.retrieve(
    query="What is Loom?",
    filters={"language": "en"}
)
```

### Q5: 如何集成外部向量数据库？

```python
from loom.interfaces.vector_store import BaseVectorStore

# 以 Pinecone 为例
import pinecone

class PineconeVectorStore(BaseVectorStore):
    def __init__(self, index_name: str):
        pinecone.init(api_key="...")
        self.index = pinecone.Index(index_name)

    async def add_vectors(self, vectors: List[List[float]], documents: List[Document]) -> None:
        vectors_to_upsert = [
            (doc.doc_id, vec, {"content": doc.content, **doc.metadata})
            for vec, doc in zip(vectors, documents)
        ]
        self.index.upsert(vectors=vectors_to_upsert)

    async def search(self, query_vector: List[float], top_k: int = 5, **kwargs) -> List[Tuple[Document, float]]:
        results = self.index.query(query_vector, top_k=top_k, include_metadata=True)
        docs = [
            (
                Document(
                    content=match.metadata["content"],
                    metadata=match.metadata,
                    doc_id=match.id
                ),
                match.score
            )
            for match in results.matches
        ]
        return docs
```

### Q6: 如何实现增量更新文档？

```python
# 1. 文档带唯一 ID
Document(
    content="Updated content",
    doc_id="doc_123",  # 唯一标识
    metadata={"version": 2, "updated_at": "2024-01-15"}
)

# 2. 检索器支持更新
class MyRetriever(BaseRetriever):
    async def update_document(self, doc_id: str, new_doc: Document) -> None:
        # 删除旧版本
        await self.delete_document(doc_id)
        # 添加新版本
        await self.add_documents([new_doc])

# 3. 定期同步
async def sync_documents():
    updated_docs = fetch_updated_docs()  # 从数据库获取更新
    for doc in updated_docs:
        await retriever.update_document(doc.doc_id, doc)
```

---

## 进一步学习

### 示例代码
- `examples/rag_basic_example.py` - ContextRetriever 基础示例
- `examples/rag_tool_example.py` - DocumentSearchTool 示例
- `examples/rag_patterns_example.py` - 高级 RAG 模式示例

### 相关文档
- `LOOM_UNIFIED_DEVELOPER_GUIDE.md` - Loom 完整开发指南
- `loom/interfaces/retriever.py` - 检索器接口定义
- `loom/patterns/rag.py` - RAG 模式源码

---

## 总结

Loom 的三层 RAG 架构：

| 层级 | 组件 | 适用场景 | 特点 |
|------|------|----------|------|
| **Layer 1** | ContextRetriever | 知识库问答 | 自动检索，零侵入 |
| **Layer 2** | DocumentSearchTool | 多工具协作 | LLM 控制，灵活 |
| **Layer 3** | RAGPattern | 复杂 RAG 流程 | 完整控制，可扩展 |

选择建议：
- 🔰 **入门**：使用 ContextRetriever + InMemoryRetriever
- 🚀 **生产**：使用 ContextRetriever + VectorStoreRetriever
- 🎯 **进阶**：使用 RAGPattern + Re-ranking

Happy coding with Loom RAG! 🎉
