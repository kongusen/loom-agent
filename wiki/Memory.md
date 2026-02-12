# 记忆系统

`loom/memory/` 实现了基于公理 A4（记忆层次）的 Token-First 多层记忆系统。

## 文件结构

```
loom/memory/
├── manager.py       # MemoryManager - 统一管理入口
├── core.py          # LoomMemory - L1-L4 底层实现
├── types.py         # MemoryUnit, MemoryTier, MemoryType 等类型
├── compaction.py    # MemoryCompactor - 记忆压缩
├── compression.py   # L4Compressor - L4 层压缩（含保真度检查）
├── fact_extractor.py# FactExtractor - 关键事实提取
├── reranker.py      # MemoryReranker - 统一重排序
├── shared_pool.py   # SharedMemoryPool - 跨 Agent 共享记忆池
├── tokenizer.py     # TokenCounter 抽象与实现
├── vector_store.py  # 向量存储接口
├── sanitizers.py    # 内容清理器
├── segment_store.py # 片段存储（Fact Indexing）
├── factory.py       # MemoryFactory
└── layers/          # 层级实现
```

## 四层记忆模型

```
┌──────────────────────────────────────────────┐
│  L1 (8K tokens)  — 最近交互，完整 Task 对象    │
│  ↓ 超容量自动迁移                              │
│  L2 (16K tokens) — 重要任务，Session 工作记忆   │
│  ↓ 压缩迁移                                   │
│  L3 (32K tokens) — Session 摘要，压缩表示       │
│  ↓ 向量化                                     │
│  L4 (100K tokens)— 向量存储，跨 Session 语义检索 │
└──────────────────────────────────────────────┘
```

| 层级 | 默认预算 | 内容 | 访问方式 |
|------|---------|------|---------|
| L1 | 8,000 tokens | 完整 Task 对象、最近交互 | 直接遍历 |
| L2 | 16,000 tokens | 重要任务、Session 工作记忆 | 重要性排序 |
| L3 | 32,000 tokens | Session 摘要、压缩表示 | 关键事实索引 |
| L4 | 100,000 tokens | 向量嵌入、跨 Session 检索 | 语义相似度 |

## MemoryManager

统一的记忆管理入口，代理 LoomMemory 并管理上下文存储。

```python
manager = MemoryManager(
    node_id="agent-1",
    parent=parent_manager,     # 父节点（分形架构）
    l1_token_budget=8000,
    l2_token_budget=16000,
    l3_token_budget=32000,
    l4_token_budget=100000,
    strategy=MemoryStrategyType.IMPORTANCE_BASED,
)

# 添加任务到记忆
await manager.add_task(task, importance=0.8)

# 上下文存储（key-value，任务间共享）
await manager.add_context("task:123:content", "任务内容...")
content = await manager.read("task:123:content")

# 查询记忆
results = await manager.query("OAuth2 认证方案")
```

### 父子关系

分形架构中，子节点的 MemoryManager 通过 `parent` 参数关联父节点，自动继承 SHARED/GLOBAL 作用域的记忆。

```python
child_manager = MemoryManager(
    node_id="child-1",
    parent=parent_manager,  # 自动继承父节点记忆
)
```

## 记忆策略

```python
class MemoryStrategyType(StrEnum):
    IMPORTANCE_BASED = "importance_based"  # 基于重要性排序（默认）
    SIMPLE = "simple"                      # 基于频率的提升
```

### IMPORTANCE_BASED 策略
- 任务按 importance 分数排序
- 高重要性任务直接进入 L2
- 低重要性任务留在 L1，超容量时被淘汰

### 自动迁移
- L1 超容量 → 按重要性迁移到 L2
- L2 超容量 → 压缩后迁移到 L3
- L3 超容量 → 向量化后迁移到 L4

## MemoryCompactor

智能记忆压缩器，在层级迁移时压缩内容：

```python
compactor = MemoryCompactor(
    config=CompactionConfig(
        trigger_threshold=0.8,    # 80% 容量时触发
        target_ratio=0.6,         # 压缩到 60%
        min_importance=0.3,       # 最低保留重要性
    ),
    memory_manager=manager,
    token_counter=counter,
    segment_store=segment_store,  # 可选：Fact Indexing
)
```

### FactExtractor

从记忆内容中提取关键事实，用于 L3 层的压缩表示：

```
原始内容: "用户讨论了 OAuth2.0 的三种模式，最终决定使用 Authorization Code 模式..."
→ 提取事实: ["决策: 使用 OAuth2.0 Authorization Code 模式", "原因: 安全性最高"]
```

## L4Compressor

L4 层知识库压缩器，当 facts 数量超过阈值时自动压缩，保持 L4 在合理规模（默认 ~150 facts）。

```python
compressor = L4Compressor(
    threshold=150,              # 触发压缩的 facts 数量
    similarity_threshold=0.75,  # 聚类相似度阈值
    min_cluster_size=3,         # 最小聚类大小
    fidelity_threshold=0.5,     # 压缩保真度阈值
)
```

### 压缩策略

```
facts 数量 > threshold?
  ├─ 有 embedding → 聚类压缩
  │   ├─ 余弦相似度矩阵 + 并查集聚类
  │   ├─ cluster ≥ min_cluster_size → 合并 + 保真度检查
  │   └─ cluster < min_cluster_size → 保留原始
  └─ 无 embedding → 重要性压缩（降级方案）
      └─ 按 importance 排序，保留前 threshold 个
```

### 保真度检查（FidelityChecker）

合并 cluster 后，通过两个信号评估压缩质量。低于阈值时放弃合并，保留原始 facts。

| 信号 | 权重 | 计算方式 |
|------|------|---------|
| Embedding 余弦相似度 | 0.6 | 合并 embedding 与各原始 embedding 的平均余弦相似度 |
| 关键词保留率 | 0.4 | 原始 facts 中提取的关键词在合并内容中的出现比例 |

```
composite_score = 0.6 × embedding_similarity + 0.4 × keyword_retention

if composite_score ≥ threshold:
    使用合并结果，metadata 附加 fidelity 指标
else:
    保留原始 facts（信息损失过大）
```

### 关键词提取

`FidelityChecker._extract_keywords` 支持中英文双语提取：

| 模式 | 示例 |
|------|------|
| 大写短语 | `Machine Learning` |
| 大写单词（过滤停用词） | `Python`, `Redis` |
| snake_case 标识符 | `memory_manager` |
| 点分路径 | `loom.memory.core` |
| ALL_CAPS 常量 | `API_KEY`, `HTTP_TIMEOUT` |
| 中文词段（按停用词切分） | `向量检索`, `召回率` |

中文提取通过在停用词位置切分连续汉字序列实现，无需外部分词库。

### FidelityResult

合并后的 fact 的 metadata 中包含保真度指标：

```python
{
    "fidelity_embedding_similarity": 0.92,
    "fidelity_keyword_retention": 0.75,
    "fidelity_composite_score": 0.85,
    "fidelity_passed": True,
    "fidelity_lost_keywords": ["Redis", "缓存"],
}
```

## MemoryReranker

统一重排序器，跨记忆层对检索结果进行重排序：

```python
class RerankSignal(StrEnum):
    RECENCY = "recency"          # 时间近度
    IMPORTANCE = "importance"     # 重要性
    RELEVANCE = "relevance"      # 语义相关度
    FREQUENCY = "frequency"      # 访问频率
```

## TokenCounter

Token 计数器抽象，支持多种实现：

| 实现 | 说明 |
|------|------|
| `TiktokenCounter` | OpenAI tiktoken（精确） |
| `AnthropicCounter` | Anthropic 计数器 |
| `EstimateCounter` | 估算（4 字符 ≈ 1 token） |

## SharedMemoryPool

跨 Agent 共享记忆池，进程内多个 Agent 持有同一引用进行读写。与 L1-L4 层级记忆互补——层级记忆是每个 Agent 私有的，SharedMemoryPool 是显式共享的。

```python
from loom.memory import SharedMemoryPool

pool = SharedMemoryPool(pool_id="team")

# 多个 Agent 共享同一 pool
agent_a = Agent.create(llm, system_prompt="研究员", shared_pool=pool)
agent_b = Agent.create(llm, system_prompt="写作者", shared_pool=pool)
```

### 读写 API

```python
# 写入（Agent A）
await pool.write("research_result", {"findings": [...]}, writer_id="agent-a")

# 读取（Agent B）
entry = await pool.read("research_result")
# entry.content, entry.version, entry.created_by, entry.updated_by

# 前缀查询
entries = await pool.list_entries(prefix="research:", limit=50)

# 删除
await pool.delete("research_result")
```

### 冲突策略

默认 last-writer-wins。可选乐观锁——传入 `expected_version` 启用版本检查：

```python
entry = await pool.read("key")
try:
    await pool.write("key", new_value, expected_version=entry.version)
except VersionConflictError as e:
    # e.key, e.expected, e.actual
    pass
```

### PoolEntry

```python
@dataclass
class PoolEntry:
    key: str
    content: Any
    version: int          # 自增版本号
    created_by: str       # 创建者 node_id
    updated_by: str       # 最后更新者 node_id
    created_at: float
    updated_at: float
    metadata: dict        # 元数据（写入时自动合并）
```

### 上下文自动注入

Agent 持有 `shared_pool` 时，框架自动注册 `SharedPoolSource` 作为上下文源。共享池条目以 `[SHARED:key]` 前缀注入 LLM 上下文，按 `updated_at` 降序排列，最新条目优先级最高。

### EventBus 集成

可选传入 `event_bus`，写入/删除操作自动发布 `shared_pool.write` / `shared_pool.delete` 事件：

```python
pool = SharedMemoryPool(pool_id="team", event_bus=event_bus)
# 写入时自动发布 Task(action="shared_pool.write", parameters={pool_id, key, version, writer})
```

### 分形继承

子节点通过 `_create_child_node` 自动继承父节点的 `shared_pool` 引用，无需手动传递。

## 类型定义

```python
class MemoryTier(StrEnum):
    L1 = "l1"  # 短期
    L2 = "l2"  # 工作
    L3 = "l3"  # 摘要
    L4 = "l4"  # 长期

class MemoryType(StrEnum):
    TASK = "task"
    CONTEXT = "context"
    FACT = "fact"
    SUMMARY = "summary"

class MemoryUnit:
    id: str
    content: Any
    tier: MemoryTier
    type: MemoryType
    importance: float
    token_count: int
    created_at: datetime
    accessed_count: int
```
