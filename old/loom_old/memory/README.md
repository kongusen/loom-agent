# A4: 记忆层次公理 (Memory Hierarchy Axiom)

> **公理陈述**: Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4

## 设计理念

A4层实现四层记忆系统，采用 **Token-First Design** 原则。
基于 Anthropic Context Engineering 最佳实践，所有容量以 token 为单位计量。

### Token-First 设计原则

1. **Token-First** - 所有操作以 token 为单位，而非条目数
2. **Quality over Quantity** - 按重要性和信息密度排序
3. **Just-in-Time Context** - 按需加载，避免预加载
4. **Context Compaction** - 智能压缩，最大化信息密度

**注意**: 上下文构建逻辑已迁移到 `loom.context` 模块。本模块专注于记忆存储。

## 核心组件

### 1. LoomMemory (`core.py`)
基于 Task 的分层记忆系统：
- `add_task()`: 添加任务到指定层级
- `get_l1_tasks()`: 获取 L1 最近任务
- `get_l2_tasks()`: 获取 L2 重要任务
- `promote_tasks()`: 触发层间迁移
- `search_tasks()`: 语义检索任务

### 2. MemoryManager (`manager.py`)
整合 LoomMemory 和 FractalMemory：
- 管理 L1-L4 分层存储
- 管理 LOCAL/SHARED/INHERITED/GLOBAL 作用域
- 父子节点关系管理
- 统一的读写接口

### 3. 四层记忆系统 (Token-First)

**L1: 直连 + 近期记忆 (`TokenBudgetLayer`)**
- Token 预算: 8,000 tokens（可配置）
- 特点: 短期、高频访问、FIFO 驱逐
- 存储: 完整 Task 对象
- 驱逐策略: 超出 token 预算时移除最旧的

**L2: 会话工作记忆 (`PriorityTokenLayer`)**
- Token 预算: 16,000 tokens（可配置）
- 特点: 按重要性排序、堆结构
- 存储: 重要 Task 对象（importance > 0.6）
- 驱逐策略: 超出 token 预算时移除最低重要性的

**L3: 会话摘要**
- Token 预算: 32,000 tokens（可配置）
- 特点: 压缩表示、节省空间
- 存储: TaskSummary 对象
- 驱逐策略: 超出 token 预算时移除最旧的

**L4: 跨会话记忆**
- Token 预算: 100,000 tokens（可配置）
- 特点: 向量化存储、语义检索
- 依赖: embedding provider + vector store

## L1-L4 迭代机制（压缩与迁移）

记忆层之间通过"重要性提升 + Token 预算触发压缩"进行自动迁移：

**L1 → L2（重要性提升）**
- 规则：`importance > 0.6` 的 Task 提升到 L2
- L2 使用优先队列，仅保留高重要性任务

**L2 → L3（会话摘要）**
- 触发：L2 token 使用率达到 85%
- 策略：将最不重要的任务压缩为 `TaskSummary` 写入 L3
- 目标：释放到 80% 使用率

**L3 → L4（跨会话向量记忆）**
- 触发：L3 token 使用率达到 90%
- 策略：将最旧的 20% 摘要向量化并存入 L4

## 与 context 模块的关系

- `memory/` - 负责存储（存什么）
- `context/` - 负责构建（用什么）

上下文构建请使用 `loom.context` 模块。

## 使用示例

```python
from loom.memory import MemoryManager, LoomMemory

# 创建记忆管理器（Token-First 配置）
memory = MemoryManager(
    node_id="agent-1",
    l1_token_budget=8000,   # L1: 8K tokens
    l2_token_budget=16000,  # L2: 16K tokens
    l3_token_budget=32000,  # L3: 32K tokens
    l4_token_budget=100000, # L4: 100K tokens
)

# 添加任务
memory.add_task(task)

# 获取 L1 最近任务
recent_tasks = memory.get_l1_tasks(limit=10)

# 获取 L2 重要任务
important_tasks = memory.get_l2_tasks(limit=10)

# 触发层间迁移
memory.promote_tasks()

# 获取统计信息（Token-First）
stats = memory._loom_memory.get_stats()
print(f"L1 token usage: {stats['l1_token_usage']}/{stats['l1_token_budget']}")
print(f"L2 token usage: {stats['l2_token_usage']}/{stats['l2_token_budget']}")
```

## 与上下文模块配合使用

```python
from loom.memory import LoomMemory
from loom.memory.tokenizer import EstimateCounter
from loom.context import ContextOrchestrator
from loom.context.sources import L1RecentSource, L2ImportantSource

# 创建记忆（Token-First 配置）
memory = LoomMemory(
    node_id="agent-1",
    l1_token_budget=8000,
    l2_token_budget=16000,
)

# 创建上下文源（从 memory 读取）
sources = [
    L1RecentSource(memory),
    L2ImportantSource(memory),
]

# 创建编排器
orchestrator = ContextOrchestrator(
    token_counter=EstimateCounter(),
    sources=sources,
    model_context_window=128000,
)

# 构建上下文
messages = await orchestrator.build_context(query="用户问题")
```
