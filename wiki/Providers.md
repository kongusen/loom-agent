# 提供者（Providers）

`loom/providers/` 实现了 LLM、知识库、MCP 和嵌入向量的提供者抽象，支持多种后端。

## 文件结构

```
loom/providers/
├── base.py              # 基础提供者抽象
├── llm/                 # LLM 提供者
│   ├── interface.py     # LLMProvider 抽象接口
│   ├── base_handler.py  # BaseHandler 通用处理逻辑
│   ├── retry_handler.py # RetryHandler 重试机制
│   ├── openai.py        # OpenAI
│   ├── openai_compatible.py # OpenAI 兼容接口
│   ├── anthropic.py     # Anthropic Claude
│   ├── deepseek.py      # DeepSeek
│   ├── qwen.py          # 通义千问
│   ├── gemini.py        # Google Gemini
│   ├── ollama.py        # Ollama (本地)
│   ├── kimi.py          # Kimi (月之暗面)
│   ├── doubao.py        # 豆包 (字节跳动)
│   ├── zhipu.py         # 智谱 AI
│   ├── vllm.py          # vLLM
│   ├── gpustack.py      # GPUStack
│   ├── custom.py        # 自定义提供者
│   └── mock.py          # Mock (测试用)
├── knowledge/           # 知识库提供者
│   ├── base.py          # KnowledgeBaseProvider 抽象
│   ├── memory.py        # 内存知识库
│   ├── vector.py        # 向量知识库
│   ├── graph.py         # 图谱知识库
│   └── rag/             # RAG 子系统
├── embedding/           # 嵌入向量提供者
│   └── openai.py        # OpenAI Embeddings
├── mcp/                 # MCP 提供者
│   ├── interface.py     # MCPClient 抽象
│   ├── stdio_client.py  # Stdio MCP 客户端
│   └── http_client.py   # HTTP MCP 客户端
└── vector_store.py      # 向量存储抽象
```

## LLM 提供者

### LLMProvider 接口

```python
class LLMProvider(ABC):
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse: ...

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]: ...
```

### 支持的 LLM

| 提供者 | 类 | 说明 |
|--------|-----|------|
| OpenAI | `OpenAIProvider` | GPT-4o, GPT-4o-mini 等 |
| Anthropic | `AnthropicProvider` | Claude 3.5, Claude 3 等 |
| DeepSeek | `DeepSeekProvider` | DeepSeek-V3, DeepSeek-R1 等 |
| Qwen | `QwenProvider` | 通义千问系列 |
| Gemini | `GeminiProvider` | Google Gemini 系列 |
| Ollama | `OllamaProvider` | 本地模型 |
| Kimi | `KimiProvider` | 月之暗面 |
| 豆包 | `DoubaoProvider` | 字节跳动 |
| 智谱 | `ZhipuProvider` | 智谱 AI |
| vLLM | `VLLMProvider` | vLLM 推理引擎 |
| GPUStack | `GPUStackProvider` | GPUStack 集群 |
| OpenAI 兼容 | `OpenAICompatibleProvider` | 任何 OpenAI 兼容 API |
| 自定义 | `CustomProvider` | 自定义实现 |
| Mock | `MockProvider` | 测试用 |

### 使用示例

```python
from loom.providers.llm.openai import OpenAIProvider
from loom.providers.llm.anthropic import AnthropicProvider
from loom.providers.llm.deepseek import DeepSeekProvider

# OpenAI
llm = OpenAIProvider(model="gpt-4o-mini", api_key="...")

# Anthropic
llm = AnthropicProvider(model="claude-3-5-sonnet-20241022", api_key="...")

# DeepSeek
llm = DeepSeekProvider(model="deepseek-chat", api_key="...")

# OpenAI 兼容（任何兼容 API）
from loom.providers.llm.openai_compatible import OpenAICompatibleProvider
llm = OpenAICompatibleProvider(
    base_url="http://localhost:8000/v1",
    model="my-model",
)
```

### RetryHandler

自动重试机制，处理 API 限流和临时错误：

- 指数退避重试
- 可配置最大重试次数
- 区分可重试和不可重试错误

## 知识库提供者

### KnowledgeBaseProvider 接口

```python
class KnowledgeBaseProvider(ABC):
    # ---- 元信息（用于自动生成统一检索工具描述）----

    @property
    def name(self) -> str:
        """知识库标识名（如 "product_docs"）"""

    @property
    def description(self) -> str:
        """知识库描述（如 "产品文档和API参考手册"）"""

    @property
    def search_hints(self) -> list[str]:
        """搜索提示（如 ["产品功能", "API用法", "错误排查"]）"""

    @property
    def supported_filters(self) -> list[str]:
        """支持的过滤维度（如 ["category", "version"]）"""

    # ---- 检索接口 ----

    async def query(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[KnowledgeItem]: ...

    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None: ...
```

### 元信息与主动检索

`search_hints`、`description`、`supported_filters` 三个属性是主动检索机制的核心配置点。框架通过 `UnifiedSearchToolBuilder` 将这些元信息聚合到 `query` 工具的描述中，LLM 据此自主决定何时调用检索：

```
KnowledgeBaseProvider
  ├─ name         → 工具 source 参数的 enum 值
  ├─ description  → 工具描述中的"可用知识源"列表
  ├─ search_hints → 工具描述中的"适用场景"提示
  └─ supported_filters → 工具 filters 参数的说明
```

详见 [Tools.md](Tools.md) 中的统一检索工具章节。

### KnowledgeItem

```python
@dataclass
class KnowledgeItem:
    id: str
    content: str           # 知识内容
    source: str            # 来源（文档、API、数据库等）
    relevance: float = 0.0 # 相关度分数（0.0-1.0）
    metadata: dict = {}    # 附加元数据
```

### RAG 子系统

`loom/providers/knowledge/rag/` 实现了完整的 RAG 管线，图和向量双通道构建与检索。

#### 设计原则

- LLM 和 Embedding 从 Agent 共享，不独立配置
- 实体/关系提取用 LLM + ExtractionConfig（Skill 模式：用户配置方向，框架提供提取逻辑）
- 图和向量库都要，chunk 向量化 + 实体/关系图谱化
- 三个内部 Store 保留为实现细节，外部统一为一个配置点
- InMemory 作为默认，用户可插拔自己的存储实现

#### 构建流程（Indexing）

```
文档输入
  ↓
Chunker → 文档分块 + 关键词提取（填充 chunk.keywords）
  ├─ SimpleChunker (按字符数切分)
  └─ SlidingWindowChunker (滑动窗口 + 重叠)
  ↓
Agent.embedding_provider → chunk 向量化
  ↓
LLMEntityExtractor（ExtractionConfig 配置提取方向）
  ├─ Agent.llm_provider → 结构化 prompt 提取实体和关系
  └─ ExtractionConfig → entity_types, relation_types, hints
  ↓
存储（三个内部 Store，chunk ↔ entity 双向关联）:
  ├─ ChunkStore (文本块 + 向量 + keywords + entity_ids)
  ├─ EntityStore (实体 + chunk_ids)
  └─ RelationStore (关系: source_id → target_id)
```

关键词提取（`extract_chunk_keywords`）是轻量文本处理，不调用 LLM。提取 CamelCase、snake_case、ALL_CAPS、dotted.path 等模式的标识符。

#### ExtractionConfig

用户通过 `ExtractionConfig` 配置提取方向，框架内置 `LLMEntityExtractor` 负责具体提取：

```python
from loom.providers.knowledge.rag import ExtractionConfig, RAGConfig

config = RAGConfig(
    extraction=ExtractionConfig(
        entity_types=["技术概念", "API端点", "数据模型"],
        relation_types=["DEPENDS_ON", "IMPLEMENTS", "USES"],
        hints="关注技术架构和API设计模式",
        max_entities_per_chunk=10,
        max_relations_per_chunk=10,
        enabled=True,  # False 时跳过提取，纯向量模式
    ),
)
```

#### 策略自动选择

`from_config()` 根据可用能力自动选择最优检索策略：

| 条件 | 策略 |
|------|------|
| 有 embedding + 有 llm_provider | 用户配置的策略（默认 hybrid） |
| 有 embedding + 无 llm_provider | 自动降级为 vector_first |
| 无 embedding + 有 llm_provider | graph_only |
| 无 embedding + 无 llm_provider | graph_only（纯关键词） |

#### 检索流程（Retrieval）

检索管线由三层组成：检索器（Retriever）→ 策略（Strategy）→ 观测（Observability）。

##### 检索器

三个独立检索器，各自负责一条检索通道：

| 检索器 | 输入 | 检索路径 | 输出 |
|--------|------|----------|------|
| `VectorRetriever` | query embedding | `chunk_store.search_by_vector()` 余弦相似度 | `[(chunk, score)]` |
| `GraphRetriever` | query text | `entity_store.search()` → `relation_store.get_n_hop()` → `entity.chunk_ids` → `chunk_store.get_by_ids()` | `(entities, relations, chunks)` |
| `KeywordRetriever` | query text | `chunk_store.search_by_keyword()` 关键词匹配 | `[chunk]` |

##### 策略

四种策略，`from_config()` 根据可用能力自动选择：

**VectorFirstStrategy** — 纯向量语义检索：

```text
query → VectorRetriever → 按相似度排序 → Top-K
```

**GraphFirstStrategy** — 图谱优先 + 语义重排序：

```text
query → GraphRetriever → 图谱命中 chunks
  ├─ 有结果 → VectorRetriever.embed(query) → 对 chunks 语义重排序 → Top-K
  └─ 无结果 → 降级为纯向量检索（fallback）
```

**HybridStrategy** — 三路并行融合（默认策略）：

```text
query
  ↓
1. 并行检索（asyncio.gather）:
  ├─ GraphRetriever → graph_chunks（位置分数 × graph_weight）
  └─ VectorRetriever → vector_chunks（相似度分数 × vector_weight）
  ↓
2. 图谱扩展（_expand_via_graph）:
  vector_chunks.entity_ids
    → entity_store.get_by_ids()     # 找到向量命中 chunk 关联的实体
    → relation_store.get_by_entity() # 1-hop 遍历邻居实体
    → neighbor_entity.chunk_ids      # 收集邻居实体的 chunk
    → chunk_store.get_by_ids()       # 获取扩展 chunk（排除已有的）
    → expansion_chunks（位置分数 × expansion_weight）
  ↓
3. 三路分数融合:
  同一个 chunk 被多条通道命中时，分数叠加
  graph_score + vector_score + expansion_score
  ↓
4. 排序取 Top-K → RetrievalResult
```

图谱扩展是 HybridStrategy 的核心增强：向量检索找到语义相关的 chunk 后，沿着 `chunk.entity_ids` 桥接到知识图谱，通过实体关系发现结构相关但语义不一定相似的 chunk。这实现了真正的图+向量联合查询。

**_GraphOnlyStrategy** — 纯图检索（无 embedding 时的降级策略）：

```text
query → GraphRetriever → 按位置排序 → Top-K
```

##### 双向关联的使用

构建时写入的 `chunk.entity_ids` ↔ `entity.chunk_ids` 双向关联在检索时的使用：

| 方向 | 使用场景 | 代码位置 |
|------|----------|----------|
| `entity.chunk_ids` → chunk | GraphRetriever：实体遍历后定位原始文本块 | `graph.py:82-84` |
| `chunk.entity_ids` → entity | HybridStrategy 图谱扩展：向量命中 chunk 桥接到图谱 | `hybrid.py:158-160` |
| chunk_id → entity | EntityStore.get_by_chunk()：反向查找 chunk 关联的实体 | `entity_store.py:142` |
| entity_id → chunk | ChunkStore.get_by_entity()：正向查找实体关联的 chunk | `chunk_store.py:149` |

##### 权重配置

HybridStrategy 的三路权重通过 `RAGConfig` 和构造参数控制：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `graph_weight` | 0.5 | 图检索结果的权重 |
| `vector_weight` | 0.5 | 向量检索结果的权重 |
| `expansion_weight` | 0.3 | 图谱扩展结果的权重（衰减，避免噪声） |

##### 观测集成

检索管线与 `loom/observability/` 深度集成。`from_config()` 接受可选的 `tracer` 和 `metrics` 参数，自动传递到策略层：

```python
from loom.observability import LoomTracer, LoomMetrics

tracer = LoomTracer(agent_id="agent-1")
metrics = LoomMetrics(agent_id="agent-1")

kb = GraphRAGKnowledgeBase.from_config(
    llm_provider=llm,
    embedding_provider=embedder,
    tracer=tracer,    # 传递到策略层
    metrics=metrics,  # 传递到策略层
)
```

`GraphRAGKnowledgeBase.query()` 自动创建 `KNOWLEDGE_SEARCH` span，策略层在 span 上记录详细属性：

| Span Attribute | 说明 |
|----------------|------|
| `retrieval.strategy` | 策略类型（hybrid / graph_first） |
| `retrieval.graph_count` | 图检索命中数 |
| `retrieval.vector_count` | 向量检索命中数 |
| `retrieval.expansion_count` | 图谱扩展命中数（仅 hybrid） |
| `retrieval.result_count` | 最终返回结果数 |
| `retrieval.parallel_ms` | 并行检索耗时（仅 hybrid） |
| `retrieval.expansion_ms` | 图谱扩展耗时（仅 hybrid） |
| `retrieval.total_ms` | 总耗时 |
| `retrieval.fallback_to_vector` | 是否降级到向量检索（仅 graph_first） |

详见 [Observability.md](Observability.md) 中的知识检索指标章节。

#### GraphRAGKnowledgeBase

`GraphRAGKnowledgeBase` 是 `KnowledgeBaseProvider` 的完整实现，整合了构建和检索：

```python
from loom.providers.knowledge.rag import GraphRAGKnowledgeBase, RAGConfig, ExtractionConfig

# LLM 和 Embedding 从 Agent 共享同一个实例
llm = OpenAIProvider(model="gpt-4o-mini")
embedder = OpenAIEmbeddingProvider(model="text-embedding-3-small")

kb = GraphRAGKnowledgeBase.from_config(
    llm_provider=llm,           # 用于实体/关系提取
    embedding_provider=embedder, # 用于 chunk 向量化
    config=RAGConfig(
        extraction=ExtractionConfig(
            entity_types=["技术概念", "API端点"],
            hints="关注技术架构",
        ),
    ),
    name="product_docs",
    description="产品文档和API参考",
    search_hints=["产品功能", "API用法"],
)

# 构建索引
await kb.add_texts(["文档内容1", "文档内容2"])

# 检索
items = await kb.query("如何配置认证?", limit=5)

# 集成到 Agent
agent = Agent.create(llm, knowledge_base=kb)
```

## MCP 提供者

支持 Model Context Protocol 的外部工具集成：

```python
from loom.providers.mcp import StdioClient, HttpClient

# Stdio MCP（本地进程）
client = StdioClient(command="npx", args=["-y", "mcp-server"])

# HTTP MCP（远程服务）
client = HttpClient(url="http://localhost:3000/mcp")

# 获取工具列表
tools = await client.list_tools()

# 调用工具
result = await client.call_tool("tool_name", {"arg": "value"})
```

## 嵌入向量提供者

```python
from loom.providers.embedding.openai import OpenAIEmbeddingProvider

embedder = OpenAIEmbeddingProvider(model="text-embedding-3-small")
vectors = await embedder.embed(["文本1", "文本2"])
```
