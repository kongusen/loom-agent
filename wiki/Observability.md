# 可观测性

`loom/observability/` 提供结构化的 Tracing 和 Metrics 能力，零侵入集成到 Agent 运行时。

## 文件结构

```
loom/observability/
├── tracing.py     # LoomTracer - 结构化追踪
├── metrics.py     # LoomMetrics - 指标收集
└── exporters.py   # 导出器（OTLP, Console）
```

## LoomTracer

结构化追踪系统，记录 Agent 执行过程中的每个操作。支持嵌套 Span（Agent → Iteration → LLM Call → Tool），自动维护父子关系。

```python
from loom.observability import LoomTracer, SpanKind

tracer = LoomTracer(agent_id="agent-1", enabled=True)

# 创建嵌套 Span
with tracer.start_span(SpanKind.AGENT_RUN, "run") as run_span:
    run_span.set_attribute("task", "hello")
    with tracer.start_span(SpanKind.LLM_CALL, "gpt-4o") as llm_span:
        response = await llm.chat(messages)
        llm_span.set_attribute("tokens_in", 100)
```

### SpanKind

框架定义了 12 种 Span 类型：

| SpanKind | 枚举值 | 说明 |
|----------|--------|------|
| `AGENT_RUN` | `agent.run` | Agent 完整执行 |
| `AGENT_ITERATION` | `agent.iteration` | 单次 ReAct 迭代 |
| `LLM_CALL` | `llm.call` | LLM API 调用 |
| `TOOL_EXECUTION` | `tool.execution` | 工具执行 |
| `MEMORY_READ` | `memory.read` | 记忆读取 |
| `MEMORY_WRITE` | `memory.write` | 记忆写入 |
| `CONTEXT_BUILD` | `context.build` | 上下文构建 |
| `DELEGATION` | `agent.delegation` | 任务委派 |
| `PLANNING` | `agent.planning` | 计划执行 |
| `SKILL_ACTIVATION` | `skill.activation` | Skill 激活 |
| `KNOWLEDGE_SEARCH` | `knowledge.search` | 主动知识检索（Agent 调用 query 工具） |
| `KNOWLEDGE_RETRIEVAL` | `knowledge.retrieval` | 被动知识检索（上下文构建时自动执行） |

### Span 数据结构

每个 Span 记录以下信息：

```python
@dataclass
class Span:
    trace_id: str              # Trace 标识
    span_id: str               # Span 标识
    parent_span_id: str | None # 父 Span（嵌套追踪）
    kind: SpanKind             # Span 类型
    name: str                  # 操作名称
    start_time: float          # 开始时间
    end_time: float            # 结束时间
    attributes: dict           # 自定义属性
    events: list[dict]         # 事件列表
    status: str                # "ok" | "error"
    error_message: str         # 错误信息
```

关键方法：

- `span.set_attribute(key, value)` — 设置属性
- `span.add_event(name, attributes)` — 添加事件
- `span.set_error(exception)` — 标记错误
- `span.duration_ms` — 耗时（毫秒）

### 导出器

```python
from loom.observability.tracing import LogSpanExporter, InMemoryExporter

# 日志导出（开发调试）
log_exporter = LogSpanExporter()

# 内存导出（测试）
mem_exporter = InMemoryExporter()

tracer = LoomTracer(agent_id="agent-1")
tracer.add_exporter(log_exporter)
tracer.add_exporter(mem_exporter)
```

### 装饰器追踪

`trace_operation` 装饰器自动为异步方法创建 Span：

```python
from loom.observability.tracing import trace_operation, SpanKind

class MyService:
    def __init__(self, tracer):
        self._tracer = tracer

    @trace_operation(SpanKind.TOOL_EXECUTION)
    async def execute_tool(self, tool_name, args):
        ...  # 自动创建 TOOL_EXECUTION span
```

### Trace 摘要

```python
summary = tracer.get_trace_summary()
# {
#     "trace_id": "a1b2c3d4e5f6",
#     "agent_id": "agent-1",
#     "span_count": 15,
#     "total_duration_ms": 3456.78,
#     "error_count": 0,
#     "spans_by_kind": {"llm.call": 5, "tool.execution": 8, ...}
# }
```

## LoomMetrics

Agent 执行指标收集，支持 Counter、Gauge、Histogram 三种类型：

```python
from loom.observability import LoomMetrics

metrics = LoomMetrics(agent_id="agent-1", enabled=True)

# Counter（累加）
metrics.increment(LoomMetrics.ITERATIONS_TOTAL)
metrics.increment(LoomMetrics.TOOL_CALLS_TOTAL)

# Gauge（瞬时值）
metrics.set_gauge(LoomMetrics.CONTEXT_BUDGET_USED, 0.75)

# Histogram（分布）
metrics.observe(LoomMetrics.LLM_LATENCY, 1230.5)

# 便捷方法
metrics.record_tokens(input_tokens=500, output_tokens=200)
metrics.observe_latency("llm_call", 1230.5)
```

### 预定义指标

#### Agent 运行时指标

| 常量 | 指标名 | 类型 | 说明 |
|------|--------|------|------|
| `ITERATIONS_TOTAL` | `agent_iterations_total` | Counter | ReAct 迭代次数 |
| `TOKEN_INPUT` | `agent_token_input` | Counter | 输入 Token 消耗量 |
| `TOKEN_OUTPUT` | `agent_token_output` | Counter | 输出 Token 消耗量 |
| `TOOL_CALLS_TOTAL` | `agent_tool_calls_total` | Counter | 工具调用次数 |
| `TOOL_ERRORS_TOTAL` | `agent_tool_errors_total` | Counter | 工具错误次数 |
| `LLM_LATENCY` | `agent_llm_latency_ms` | Histogram | LLM 调用耗时 |
| `CONTEXT_BUDGET_USED` | `agent_context_budget_used_ratio` | Gauge | 上下文预算使用率 |
| `DELEGATION_TOTAL` | `agent_delegation_total` | Counter | 任务委派次数 |

#### 记忆指标

| 常量 | 指标名 | 类型 | 说明 |
|------|--------|------|------|
| `MEMORY_L1_USAGE` | `memory_l1_usage_ratio` | Gauge | L1 层使用率 |
| `MEMORY_L2_USAGE` | `memory_l2_usage_ratio` | Gauge | L2 层使用率 |

#### 知识检索指标

| 常量 | 指标名 | 类型 | 说明 |
|------|--------|------|------|
| `KNOWLEDGE_SEARCH_TOTAL` | `knowledge_search_total` | Counter | 知识检索总次数 |
| `KNOWLEDGE_SEARCH_LATENCY` | `knowledge_search_latency_ms` | Histogram | 知识检索耗时 |
| `KNOWLEDGE_HIT_RATE` | `knowledge_hit_rate` | Gauge | 检索命中率（结果数/总源数） |
| `KNOWLEDGE_RESULTS_COUNT` | `knowledge_results_count` | Gauge | 最近一次检索返回结果数 |

### Label 支持

指标支持 label 维度，用于区分不同来源：

```python
metrics.increment(LoomMetrics.TOOL_CALLS_TOTAL, labels={"tool": "bash"})
metrics.increment(LoomMetrics.TOOL_CALLS_TOTAL, labels={"tool": "read_file"})
```

### Snapshot

导出当前所有指标的快照，Histogram 自动计算统计量：

```python
snapshot = metrics.snapshot()
# {
#     "agent_id": "agent-1",
#     "counters": {"agent_iterations_total": 5, ...},
#     "gauges": {"agent_context_budget_used_ratio": 0.75, ...},
#     "histograms": {
#         "agent_llm_latency_ms": {
#             "count": 5, "sum": 6150.0,
#             "min": 800.0, "max": 1500.0, "avg": 1230.0,
#             "p50": 1200.0, "p95": 1480.0, "p99": 1500.0,
#         }
#     }
# }
```

## 知识检索观测

RAG 检索管线与观测体系深度集成。`GraphRAGKnowledgeBase.from_config()` 接受可选的 `tracer` 和 `metrics` 参数，自动传递到策略层。

### 集成方式

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

### 观测数据流

```
GraphRAGKnowledgeBase.query()
  │
  ├─ 创建 KNOWLEDGE_SEARCH span（tracer）
  │   └─ attributes: query, limit, source
  │
  ├─ 调用 strategy.retrieve()
  │   └─ 策略层在 span 上记录详细属性（见下表）
  │
  └─ 记录 metrics
      ├─ increment(KNOWLEDGE_SEARCH_TOTAL)
      ├─ observe(KNOWLEDGE_SEARCH_LATENCY, elapsed_ms)
      └─ set_gauge(KNOWLEDGE_RESULTS_COUNT, len(items))
```

### HybridStrategy Span 属性

HybridStrategy 在 `KNOWLEDGE_SEARCH` span 上记录三路检索的详细指标：

| Span Attribute | 类型 | 说明 |
|----------------|------|------|
| `retrieval.strategy` | string | `"hybrid"` |
| `retrieval.graph_count` | int | 图检索命中 chunk 数 |
| `retrieval.vector_count` | int | 向量检索命中 chunk 数 |
| `retrieval.expansion_count` | int | 图谱扩展发现的 chunk 数 |
| `retrieval.result_count` | int | 最终返回结果数（去重 + Top-K） |
| `retrieval.parallel_ms` | float | 图+向量并行检索耗时 |
| `retrieval.expansion_ms` | float | 图谱扩展耗时 |
| `retrieval.total_ms` | float | 总耗时 |

HybridStrategy 同时记录 metrics：

- `KNOWLEDGE_SEARCH_TOTAL` +1
- `KNOWLEDGE_SEARCH_LATENCY` 记录 total_ms
- `KNOWLEDGE_RESULTS_COUNT` 设为结果数
- `KNOWLEDGE_HIT_RATE` 计算为 `result_count / (graph + vector + expansion)`

### GraphFirstStrategy Span 属性

| Span Attribute | 类型 | 说明 |
|----------------|------|------|
| `retrieval.strategy` | string | `"graph_first"` |
| `retrieval.graph_count` | int | 图检索命中 chunk 数 |
| `retrieval.result_count` | int | 最终返回结果数 |
| `retrieval.fallback_to_vector` | bool | 是否降级到纯向量检索 |
| `retrieval.total_ms` | float | 总耗时 |

当 `fallback_to_vector=True` 时，表示图检索无结果，自动降级为纯向量检索。

### 典型 Trace 示例

一次 HybridStrategy 检索的完整 Trace 结构：

```
[KNOWLEDGE_SEARCH] knowledge.query:product_docs  (45.2ms)
  ├─ attributes:
  │   query: "如何配置认证?"
  │   limit: 5
  │   source: "product_docs"
  │   retrieval.strategy: "hybrid"
  │   retrieval.graph_count: 3
  │   retrieval.vector_count: 5
  │   retrieval.expansion_count: 2
  │   retrieval.result_count: 5
  │   retrieval.parallel_ms: 28.5
  │   retrieval.expansion_ms: 12.3
  │   retrieval.total_ms: 45.2
```

## 与 BaseNode 的集成

BaseNode 自动发布生命周期事件（`AgentAction`），这些事件可被 Tracer 捕获：

| 事件 | AgentAction | 说明 |
|------|-------------|------|
| `node.start` | `START` | 任务开始 |
| `node.thinking` | `THINKING` | 思考过程 |
| `node.tool_call` | `TOOL_CALL` | 工具调用 |
| `node.tool_result` | `TOOL_RESULT` | 工具结果 |
| `node.planning` | `PLANNING` | 规划 |
| `node.complete` | `COMPLETE` | 任务完成 |
| `node.error` | `ERROR` | 错误 |
| `node.message` | `MESSAGE` | 消息输出 |
