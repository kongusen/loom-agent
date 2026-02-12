# 上下文编排

`loom/context/` 实现了基于 Anthropic Context Engineering 思想的上下文编排系统，负责为 LLM 构建最优的上下文窗口。

## 文件结构

```
loom/context/
├── orchestrator.py      # ContextOrchestrator - 统一入口
├── collector.py         # ContextCollector - 多源收集
├── compactor.py         # ContextCompactor - 超预算压缩
├── budget.py            # BudgetManager / AdaptiveBudgetManager
├── block.py             # ContextBlock - 上下文块
├── source.py            # ContextSource 抽象接口
├── sources/             # 内置上下文源
│   ├── memory.py        # L1RecentSource, L2ImportantSource
│   ├── inherited.py     # InheritedSource (父节点上下文)
│   ├── shared_pool.py   # SharedPoolSource (跨 Agent 共享池)
│   ├── semantic.py      # 语义检索源
│   ├── rag.py           # RAG 知识库源
│   ├── skill.py         # Skill 上下文源
│   ├── tool.py          # 工具上下文源
│   ├── prompt.py        # 提示词源
│   ├── user.py          # 用户输入源
│   └── agent.py         # Agent 状态源
└── retrieval/           # 统一检索子系统
    ├── source.py        # UnifiedRetrievalSource
    ├── unified_reranker.py # UnifiedReranker
    ├── query_rewriter.py   # QueryRewriter
    ├── candidates.py    # 候选结果
    └── injector.py      # 检索结果注入
```

## ContextOrchestrator

统一入口，协调预算管理、收集和压缩三个阶段：

```python
orchestrator = ContextOrchestrator(
    token_counter=TiktokenCounter(model="gpt-4"),
    sources=[
        L1RecentSource(memory),
        L2ImportantSource(memory),
        InheritedSource(memory),
        UnifiedRetrievalSource(memory, knowledge_bases),
    ],
    model_context_window=128000,
    output_reserve_ratio=0.25,
    budget_manager=adaptive_budget,
)

# 构建上下文
context_blocks = await orchestrator.build(query="用户的问题")
```

### 构建流程

```
1. BudgetManager.allocate()     → 为每个源分配 token 预算
2. ContextCollector.collect()   → 从各源收集 ContextBlock
3. ContextCompactor.compact()   → 超预算时压缩（摘要/截断）
4. 输出 → LLM-ready 消息列表
```

## BudgetManager

管理 token 预算分配。

```python
budget = BudgetManager(
    token_counter=counter,
    model_context_window=128000,
    output_reserve_ratio=0.25,     # 预留 25% 给输出
    allocation_ratios={
        "L1_recent": 0.25,        # 最近交互
        "L2_important": 0.20,     # 重要记忆
        "INHERITED": 0.10,        # 继承上下文
        "retrieval": 0.15,        # 检索结果
    },
)
```

### AdaptiveBudgetManager

根据任务阶段动态调整预算分配比例：

- 任务初期：更多预算给检索（获取背景信息）
- 任务中期：更多预算给最近交互（保持连贯性）
- 任务后期：更多预算给重要记忆（综合决策）

## ContextSource

上下文源的抽象接口：

```python
class ContextSource(ABC):
    name: str                    # 源名称（用于预算分配）
    priority: int                # 优先级

    async def collect(
        self,
        query: str,
        budget: TokenBudget,
    ) -> list[ContextBlock]: ...
```

### 内置源

| 源 | 说明 |
|-----|------|
| `L1RecentSource` | 从 L1 层获取最近交互 |
| `L2ImportantSource` | 从 L2 层获取重要记忆 |
| `InheritedSource` | 从父节点 MemoryManager 获取继承上下文 |
| `SharedPoolSource` | 从 SharedMemoryPool 获取跨 Agent 共享条目 |
| `UnifiedRetrievalSource` | 统一检索：L4 语义 + RAG 知识库 |

## ContextBlock

上下文块是收集和压缩的基本单位：

```python
@dataclass
class ContextBlock:
    source: str          # 来源标识
    content: str         # 内容
    token_count: int     # token 数
    priority: float      # 优先级 (0-1)
    metadata: dict       # 元数据
```

## 统一检索子系统

`loom/context/retrieval/` 整合了 L4 语义检索和 RAG 知识库检索。这是检索的被动通道——每次 LLM 交互前自动执行，结果注入上下文。主动通道（Agent 调用 `query` 工具）详见 [Tools.md](Tools.md)。

### UnifiedRetrievalSource

同时从记忆 L4 层和外部知识库检索，合并结果后统一重排序：

```
用户查询
  ↓
QueryRewriter → 查询增强
  ↓
并行召回 (recall_limit=20/源):
  ├─ L4 语义检索 (LoomMemory.search_l4, min_score 过滤)
  └─ RAG 知识库检索 (KnowledgeBaseProvider.query, min_relevance 过滤)
  ↓
Reranker → 去重 + 多信号加权排序
  ↓
RetrievalInjector → 预算感知注入 (截断到 token_budget)
  ↓
ContextBlock 列表
```

### QueryRewriter

纯文本处理，不调用 LLM。从最近对话上下文中提取高频实词，追加到原始查询：

```
原始查询: "认证方案"
对话上下文: [...最近5条消息含 "OAuth2", "安全", "token"...]
  ↓
重写后: "认证方案 [OAuth2 安全 token]"
```

策略：
1. 从最近 N 条消息（默认 5）提取词频
2. 过滤停用词（中英文）和已在查询中出现的词
3. 取 top-K（默认 6）高频实词追加到查询

### Reranker

系统唯一的重排序器，处理所有检索源的候选项。三步流程：去重 → 多信号加权 → 过滤排序。

#### 重排序信号

| 信号 | 权重 | 计算方式 |
|------|------|---------|
| `VectorScoreSignal` | 0.40 | 直接使用召回时的向量/相关度分数 |
| `QueryOverlapSignal` | 0.35 | 查询关键词在候选内容中的命中率 |
| `OriginDiversitySignal` | 0.15 | 惩罚占比过高的来源（>70% → 0.3, >50% → 0.6） |
| `ContentLengthSignal` | 0.10 | 适中长度优先（200-800 字符 → 1.0） |

```
final_score = Σ(signal.score × signal.weight) / Σ(signal.weight)
```

#### 去重

基于内容指纹（`candidate.fingerprint`）合并重复候选，保留 `vector_score` 更高的版本。

### RetrievalInjector

将重排序后的候选项转换为 `ContextBlock`，按 token 预算截断。优先保留 `final_score` 高的候选。
