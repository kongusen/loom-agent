# Loom RAG 示例

本目录包含 Loom 框架 RAG（检索增强生成）能力的完整示例。

## 📚 RAG 三层架构

Loom 提供三种 RAG 使用方式，适用于不同场景：

| 示例文件 | RAG 层级 | 使用方式 | 适用场景 |
|---------|---------|----------|----------|
| `rag_basic_example.py` | Layer 1: 核心组件 | ContextRetriever（自动检索） | 知识库问答、文档搜索 |
| `rag_tool_example.py` | Layer 2: 工具版本 | DocumentSearchTool（LLM 控制） | 多工具协作、复杂任务 |
| `rag_patterns_example.py` | Layer 3: 高级模式 | RAGPattern、MultiQueryRAG、HierarchicalRAG | 完整 RAG 流程、需要 Re-ranking |

## 🚀 快速开始

### 示例 1: 基础 RAG（自动检索）

**文件**: `rag_basic_example.py`

**特点**:
- ✅ 零侵入：只需配置 `context_retriever` 参数
- ✅ 自动检索：每次查询前自动检索相关文档
- ✅ 适合入门：最简单的 RAG 使用方式

**运行**:
```bash
python examples/rag_basic_example.py
```

**核心代码**:
```python
from loom.core.context_retriever import ContextRetriever

context_retriever = ContextRetriever(
    retriever=retriever,
    top_k=3,  # 检索 top 3 文档
    inject_as="system"  # 作为系统消息注入
)

agent = Agent(
    llm=llm,
    context_retriever=context_retriever  # 启用自动 RAG
)

# 每次查询都会自动检索
response = await agent.run("Loom 是什么？")
```

**工作流程**:
```
用户查询 → 自动检索文档 → 注入上下文 → LLM 生成答案
```

---

### 示例 2: 工具版 RAG（LLM 控制检索）

**文件**: `rag_tool_example.py`

**特点**:
- ✅ 灵活：LLM 自主决定何时检索
- ✅ 多工具协作：可与计算器、搜索引擎等工具配合
- ✅ 多次检索：可针对不同查询检索多次

**运行**:
```bash
python examples/rag_tool_example.py
```

**核心代码**:
```python
from loom.builtin.tools.document_search import DocumentSearchTool

doc_search = DocumentSearchTool(retriever)
calculator = Calculator()

agent = Agent(
    llm=llm,
    tools=[doc_search, calculator]  # DocumentSearchTool 作为工具
)

# Agent 自己决定何时使用哪个工具
response = await agent.run(
    "查询 Loom 的 RAG 能力，并计算 10*20"
)
```

**工作流程**:
```
用户查询 → LLM 决策 → 调用工具（search_documents/calculator/...） → 生成答案
```

**适用场景**:
- 并非所有查询都需要检索文档
- 需要结合多种工具完成任务
- 同一任务中可能需要检索多次不同内容

---

### 示例 3: 高级 RAG 模式

**文件**: `rag_patterns_example.py`

**特点**:
- ✅ 完整控制：自定义 RAG 流程的每个步骤
- ✅ Re-ranking：二次排序提升精度
- ✅ 高级策略：多查询、层次化检索

**运行**:
```bash
python examples/rag_patterns_example.py
```

#### 模式 1: RAGPattern（基础 RAG + Re-ranking）

```python
from loom.patterns.rag import RAGPattern

rag = RAGPattern(
    agent=agent,
    retriever=retriever,
    reranker=my_reranker,  # 可选的重排序函数
    top_k=10,              # 初始检索 10 个
    rerank_top_k=3         # 重排序后保留 3 个
)

response = await rag.run("query")
```

**工作流程**:
```
查询 → 检索 (top_k=10) → 重排序 → 保留 top 3 → 生成答案
```

#### 模式 2: MultiQueryRAG（多查询变体）

```python
from loom.patterns.rag import MultiQueryRAG

multi_rag = MultiQueryRAG(
    agent=agent,
    retriever=retriever,
    query_count=3  # 生成 3 个查询变体
)

response = await multi_rag.run("上下文工程和提示工程的区别？")
```

**工作流程**:
```
原始查询 → 生成 3 个变体查询 → 分别检索 → 合并去重 → 重排序 → 生成答案
```

**示例**:
- 原始查询: "上下文工程和提示工程的区别？"
- 变体 1: "上下文工程和提示工程的区别？"
- 变体 2: "What is context engineering vs prompt engineering?"
- 变体 3: "上下文工程的优势是什么？"

#### 模式 3: HierarchicalRAG（层次化检索）

```python
from loom.patterns.rag import HierarchicalRAG

hierarchical_rag = HierarchicalRAG(
    agent=agent,
    document_retriever=doc_retriever,      # 第一级：文档
    paragraph_retriever=para_retriever,    # 第二级：段落
    doc_top_k=5,
    para_top_k=3
)

response = await hierarchical_rag.run("Loom 的高级模式有哪些？")
```

**工作流程**:
```
查询 → 检索相关文档 (top 5) → 在文档内检索段落 (top 3) → 生成答案
```

---

## 🔧 配置与定制

### 1. 选择检索器

#### 内存检索器（开发/测试）
```python
from loom.builtin.retriever.in_memory import InMemoryRetriever

retriever = InMemoryRetriever()
await retriever.add_documents([
    Document(content="...", metadata={"source": "doc1.md"}),
])
```

**特点**:
- ✅ 无外部依赖
- ✅ 适合快速原型开发
- ❌ 简单关键词匹配（非语义检索）

#### 向量检索器（生产环境）
```python
from loom.builtin.retriever.vector_store import VectorStoreRetriever

retriever = VectorStoreRetriever(
    vector_store=vector_store,  # Pinecone/Milvus/ChromaDB
    embedding=embedding         # OpenAI/HuggingFace
)
```

**特点**:
- ✅ 语义相似度检索
- ✅ 支持多种向量数据库
- ✅ 生产环境推荐

### 2. 自定义 Re-ranker

```python
async def my_reranker(query: str, docs: List[Document]) -> List[Document]:
    """
    重排序函数 - 可使用 Cross-Encoder 或自定义算法
    """
    # 简单示例：基于关键词密度
    query_terms = set(query.lower().split())

    for doc in docs:
        doc_terms = doc.content.lower().split()
        density = sum(1 for t in doc_terms if t in query_terms) / len(doc_terms)
        doc.score = density

    docs.sort(key=lambda d: d.score or 0, reverse=True)
    return docs

# 高级示例：使用 Cross-Encoder
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

### 3. 文档分块策略

```python
def chunk_document(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    将长文档分块，便于检索

    Args:
        text: 原始文本
        chunk_size: 每块字符数
        overlap: 块之间的重叠字符数
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap  # 保留重叠部分

    return chunks

# 使用示例
long_text = "..." # 很长的文本
chunks = chunk_document(long_text, chunk_size=500)

documents = [
    Document(
        content=chunk,
        metadata={"source": "book.md", "chunk_id": i}
    )
    for i, chunk in enumerate(chunks)
]
```

---

## 📊 性能与监控

### 查看 RAG 指标

```python
agent = Agent(llm=llm, context_retriever=context_retriever)

response = await agent.run("query")

# 获取指标
metrics = agent.get_metrics()
print(f"检索次数: {metrics.retrievals}")
print(f"LLM 调用: {metrics.llm_calls}")
print(f"平均检索时间: {metrics.avg_retrieval_time}")
```

### 流式事件监听

```python
async for event in agent.stream("query"):
    if event.type == "retrieval_complete":
        doc_count = event.metadata['doc_count']
        print(f"✅ 检索完成，找到 {doc_count} 个文档")
    elif event.type == "text_delta":
        print(event.content, end="")
```

---

## 🎯 选择指南

### 如何选择 RAG 层级？

| 场景 | 推荐层级 | 理由 |
|------|---------|------|
| 知识库问答系统 | Layer 1: ContextRetriever | 每次查询都需要检索，自动化 |
| 多功能 Agent（聊天+搜索+计算） | Layer 2: DocumentSearchTool | LLM 灵活决定何时检索 |
| 需要 Re-ranking 提升精度 | Layer 3: RAGPattern | 完整控制检索流程 |
| 复杂/模糊查询 | Layer 3: MultiQueryRAG | 多角度检索提高召回率 |
| 长文档精确定位 | Layer 3: HierarchicalRAG | 两级检索（文档→段落） |

### 参数调优建议

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `top_k`（初始检索） | 3-5（知识库）<br/>5-10（长文档） | 根据文档长度调整 |
| `rerank_top_k`（重排序后） | 2-3 | 最终保留的文档数 |
| `similarity_threshold` | 0.7-0.8 | 向量检索相似度阈值 |
| `query_count`（多查询） | 3 | 查询变体数量 |

---

## 📖 进一步学习

### 完整文档
- `../loom/docs/LOOM_RAG_GUIDE.md` - RAG 完整指南（概念、架构、最佳实践）
- `../loom/docs/LOOM_UNIFIED_DEVELOPER_GUIDE.md` - Loom 框架整体开发指南

### 源码参考
- `loom/interfaces/retriever.py` - 检索器接口定义
- `loom/core/context_retriever.py` - ContextRetriever 实现
- `loom/builtin/tools/document_search.py` - DocumentSearchTool 实现
- `loom/patterns/rag.py` - 高级 RAG 模式实现

### 相关示例
- `loom_quickstart.py` - Loom 框架快速入门
- `code_agent_minimal.py` - 最小 Agent 示例

---

## 💡 常见问题

### Q: 三种 RAG 方式可以混合使用吗？

可以，但通常不推荐。建议根据场景选择一种：
- 如果 **所有查询都需要检索**，使用 ContextRetriever
- 如果 **部分查询需要检索**，使用 DocumentSearchTool
- 如果 **需要自定义 RAG 流程**，使用 RAGPattern

### Q: InMemoryRetriever 适合生产环境吗？

不适合。InMemoryRetriever 使用简单的关键词匹配，无法进行语义检索。

**生产环境推荐**:
- 使用 VectorStoreRetriever + 向量数据库（Pinecone/Milvus/ChromaDB）
- 使用高质量的 Embedding 模型（OpenAI/Cohere/多语言模型）

### Q: 如何提高检索精度？

1. **使用向量检索**：替换 InMemoryRetriever 为 VectorStoreRetriever
2. **添加 Re-ranker**：使用 Cross-Encoder 二次排序
3. **优化文档分块**：合理的 chunk_size 和 overlap
4. **丰富元数据**：添加 source、section、category 等元数据，便于过滤
5. **使用多查询 RAG**：MultiQueryRAG 生成查询变体，提高召回率

### Q: 检索到的文档太多怎么办？

- 降低 `top_k` 值（例如从 5 降到 3）
- 提高 `similarity_threshold`（例如从 0.5 提升到 0.8）
- 使用 Re-ranker 精选最相关的文档
- 使用层次化 RAG（HierarchicalRAG）精确定位

---

Happy coding with Loom RAG! 🎉
