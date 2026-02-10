# Context Module - 上下文构建层

基于 Anthropic Context Engineering 思想的上下文管理系统。

## 设计原则

### 1. Token-First Design（Token 优先设计）
所有上下文操作都以 token 为单位，彻底废弃条目（items）计数。

### 2. Quality over Quantity（质量优于数量）
不是"塞满上下文窗口"，而是"精选最相关的上下文"。

### 3. Just-in-Time Context（按需加载）
根据当前任务动态检索相关内容，不预加载所有可能需要的上下文。

### 4. Context Compaction（上下文压缩）
当接近预算上限时，自动压缩低优先级内容。

## 核心组件

### ContextBlock (`block.py`)
上下文的基本单位，携带 token 计数和优先级信息。

```python
@dataclass
class ContextBlock:
    content: str
    role: Literal["system", "user", "assistant"]
    token_count: int  # 必须字段
    priority: float   # 0.0-1.0
    source: str       # 来源标识
    compressible: bool = True
```

### BudgetManager (`budget.py`)
Token 预算管理，负责：
- 计算可用预算（扣除系统提示词和输出预留）
- 按比例分配给各上下文源

### ContextSource (`source.py`)
上下文源抽象接口，所有源必须实现：
```python
async def collect(
    self,
    query: str,
    token_budget: int,
    token_counter: TokenCounter,
    min_relevance: float = 0.5,
) -> list[ContextBlock]
```

### ContextCollector (`collector.py`)
协调多个上下文源，并行收集上下文。

### ContextCompactor (`compactor.py`)
智能压缩上下文，支持多级压缩：
- LIGHT: 移除冗余空格
- MEDIUM: 生成摘要
- AGGRESSIVE: 截断

### ContextOrchestrator (`orchestrator.py`)
统一入口，整合预算、收集、压缩。

## 上下文源

### L1RecentSource
从 LoomMemory L1 层获取最近任务。

### L2ImportantSource
从 LoomMemory L2 层获取重要任务。

### L4SemanticSource
从向量存储进行语义检索。

### RAGKnowledgeSource
从外部知识库检索相关知识。

### InheritedSource
从 Fractal Memory 获取继承上下文。

## 使用示例

```python
from loom.context import ContextOrchestrator
from loom.context.sources import L1RecentSource, L2ImportantSource
from loom.memory import TokenCounter, LoomMemory

# 创建 token 计数器
token_counter = TiktokenCounter()

# 创建记忆
memory = LoomMemory(node_id="agent-1")

# 创建上下文源
sources = [
    L1RecentSource(memory),
    L2ImportantSource(memory),
]

# 创建编排器
orchestrator = ContextOrchestrator(
    token_counter=token_counter,
    sources=sources,
    model_context_window=128000,
    output_reserve_ratio=0.25,
)

# 构建上下文
messages = await orchestrator.build_context(
    query="用户的问题",
    system_prompt="你是一个助手",
)
```

## 预算分配

默认分配比例：
- L1_recent: 25%
- L2_important: 20%
- L3_summary: 15%
- L4_semantic: 15%
- RAG_knowledge: 15%
- INHERITED: 10%

可通过 `allocation_ratios` 参数自定义。

## 与 memory 模块的关系

- `memory/` - 负责存储（存什么）
- `context/` - 负责构建（用什么）

`context/sources/` 从 `memory/` 读取数据，但不负责存储。
