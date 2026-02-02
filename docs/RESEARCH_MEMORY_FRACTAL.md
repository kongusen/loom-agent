# loom/memory、loom/fractal 研究总结

基于对两个模块的代码阅读与调用关系梳理的总结。

---

## 一、loom/memory（A4 记忆层次）

### 1.1 定位与公理

- **公理 A4**：Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4  
- 四层记忆、有损压缩、层间自动迁移；Session 由上层定义，L1/L2/L3 可按 session 过滤，L4 跨会话。

### 1.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **core.py** | `LoomMemory` | 基于 Task 的分层存储：L1 循环缓冲区（完整 Task）、L2 优先队列（重要 Task）、L3 TaskSummary 列表、L4 向量存储；订阅 EventBus `"*"` 自动收 Task 入 L1/L2；promote_tasks（同步）/promote_tasks_async（含 L3→L4 向量化）；Fact 索引、get_call_chain、get_stats |
| **manager.py** | `MemoryManager` | 整合 LoomMemory（L1-L4）+ Fractal 作用域：内部持 `_loom_memory` 与 `_memory_by_scope[MemoryScope]`；write/read/list_by_scope 按 LOCAL/SHARED/INHERITED/GLOBAL；INHERITED 从 parent 读并缓存；兼容 add_task、get_l1/l2_tasks、get_task、promote_tasks |
| **types.py** | `MemoryTier`, `MemoryUnit`, `TaskSummary`, `Fact`, `MemoryQuery` 等 | 层级枚举、记忆单元（含 to_message）、Task 摘要、Fact（fact_type, confidence, access_count）、查询请求 |
| **layers/** | `MemoryLayer`, `CircularBufferLayer`, `PriorityQueueLayer` | 抽象 add/retrieve/evict/size/clear；L1 用循环缓冲区，L2 用优先队列（按 importance） |
| **orchestrator.py** | `ContextOrchestrator` | 整合 TokenCounter、ContextSource、BudgetConfig；build_context(current_task) → 预算分配、多源拉取、去重、转消息、fit_to_token_limit |
| **task_context.py** | `ContextSource`, `ContextBudgeter`, `BudgetConfig`, `MessageConverter` 等 | 上下文源抽象 get_context(task, max_items)；预算比例 l1_ratio/l2_ratio/l3_l4_ratio；Task→LLM 消息转换；EventCandidate 评分 |
| **context.py** | `ContextStrategy`, `PriorityContextStrategy`, `SlidingWindowStrategy`, `ContextManager` | 从 MemoryUnit 列表按 max_tokens 选上下文（优先级或滑动窗口） |
| **compression.py** | `L4Compressor` | L4 规模控制（~150 facts）；相似度聚类/重要性保留 |
| **factory.py** | `MemoryFactory` | create_default / create_for_chat / create_for_task，封装 LoomMemory 参数 |
| **tokenizer.py** | `TokenCounter`, `TiktokenCounter`, `AnthropicCounter`, `EstimateCounter` | 统一 count/count_messages，多种实现 |
| **vector_store.py** | `VectorStoreProvider`, `InMemoryVectorStore`, `EmbeddingProvider` | 向量存储与嵌入接口；L4 语义检索依赖 |
| **knowledge_context.py** | `KnowledgeContextSource` | ContextSource 实现：先查 MemoryManager 缓存，再查 KnowledgeBaseProvider，结果写回 MemoryManager |
| **fact_extractor.py** | `FactExtractor` | 从 Task 提取 Fact（LoomMemory 内部使用） |
| **sanitizers.py** | `ContentSanitizer` | 内容清理（导出用） |

### 1.3 数据流与职责划分

- **LoomMemory**：纯「Task 分层存储」+ EventBus 订阅；L1 收所有 Task，L2 收 importance>0.6；promote 同步只做 L1→L2、L2→L3，L3→L4 在 promote_tasks_async 中做向量化。
- **MemoryManager**：在 LoomMemory 之上加「作用域」；读写按 scope，INHERITED 从 parent 拉取并缓存；对外同时暴露 LoomMemory 风格接口（add_task, get_l1/l2_tasks, promote_tasks）供 Agent 与上下文构建使用。
- **ContextOrchestrator / task_context**：不持有存储，只做「当前任务 + 多源 + 预算 → 消息列表」；源包括 LoomMemory 相关源与 KnowledgeContextSource 等。

### 1.4 使用方

- **Agent**：创建 MemoryManager(node_id, parent=parent_memory, event_bus)；作为 parent_memory 传给子 Agent；计划写入 memory 的 SHARED 作用域；上下文构建用 MemoryManager 相关 ContextSource。
- **context_tools / index_context_tools / memory_management_tools**：接收 LoomMemory（实际多为 Agent 的 memory._loom_memory 或等价接口），提供 query_l1/l2/l3/l4、list_l2/l3、promote、stats 等工具。
- **KnowledgeContextSource**：可选接收 MemoryManager 做 RAG 缓存。

### 1.5 重要性推断与 session 流

- **importance 默认规则**（`LoomMemory._infer_importance`）：未显式设置时按 `task.action` 赋值：`node.error`→0.9、`node.planning`→0.8、`node.tool_result`→0.75、`node.tool_call`→0.7、`execute`→0.65、`node.complete`→0.6、`node.thinking`→0.55，其余 0.5。用于 L2 提升（>0.6 入 L2）与 L2→L3 驱逐时的排序。
- **session_id**：由上层写入 `Task.session_id`；在 LoomMemory 的 `get_l1_tasks` / `get_l2_tasks` / `get_l3_summaries` 中可选按 session 过滤；在 ContextOrchestrator.build_context 中若 `current_task.session_id` 存在则对 context_tasks 按 session 过滤；KnowledgeContextSource、task_context 写缓存时也会带 session_id。L4 向量检索结果可再按 session 过滤（降级搜索路径），但 L4 存储本身不按 session 隔离。

### 1.6 类型与层级对应

| 类型 | 所在层/模块 | 说明 |
|------|-------------|------|
| **Task** | L1、L2、_task_index | 完整任务对象；L1 循环缓冲、L2 按 importance 堆 |
| **TaskSummary** | L3、_l3_summaries | 压缩表示（action, param_summary, result_summary, tags）；L2 满时低重要性 Task 压缩入 L3 |
| **Fact** | _fact_index、L4 语义检索 | 原子事实（fact_type, confidence, access_count）；FactExtractor 从 Task 提、add_fact 入索引；L4 向量搜索可返回 fact_ 前缀 ID 对应 Fact |
| **MemoryUnit** | context 策略 | 通用记忆单元（content, tier, type, importance）；ContextStrategy 从 MemoryUnit 列表按 token 选上下文；与 L1-L4 的 Task/Summary 不同，多用于「非 Task 型」上下文选择 |
| **MemoryEntry** | MemoryManager / FractalMemory | 作用域条目（id, content, scope, version）；LOCAL/SHARED/INHERITED/GLOBAL |

### 1.7 promote 调用点与 L4 条件

- **promote_tasks()**（同步）：在 `LoomMemory._on_task`（每收到一个 Task）、`add_task(..., L1)` 后调用；只做 L1→L2、L2→L3，**不做 L3→L4**。
- **promote_tasks_async()**：含 L3→L4 向量化；需由调用方在异步上下文中显式调用（如周期任务或任务批次结束后），否则 L4 可能长期不更新。
- **L4 向量化条件**：`enable_l4_vectorization` 为 True 且已设置 `embedding_provider` 和 `_l4_vector_store`；否则 `_add_to_l4` / `search_tasks` 会跳过向量化或降级为 `_simple_search_tasks` / `_simple_search_facts`。

### 1.8 小结

- memory 模块 = **L1-L4 分层（LoomMemory）** + **作用域与父子继承（MemoryManager 整合 Fractal 概念）** + **上下文编排与预算（ContextOrchestrator / task_context / context）** + **L4 压缩 / 向量 / Token / 知识库** 等支撑。
- 与 **events**：LoomMemory 通过 EventBus `"*"` 收 Task，实现「所有通信即 Task」的 A2 与 A4 联动。
- 与 **fractal**：MemoryManager 的 scope 与 INHERITED 设计来自 FractalMemory；loom/memory/manager 直接依赖 loom/fractal.memory（MemoryScope, MemoryEntry）。

---

## 二、loom/fractal（A3 分形自相似）

### 2.1 定位与公理

- **公理 A3**：∀node ∈ System: structure(node) ≅ structure(System)  
- 节点递归组合、运行时递归 = 节点递归；分形分解依赖 LLM + Task 递归调用，不手写递归逻辑。

### 2.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **container.py** | `NodeContainer` | 实现 NodeProtocol；持单个 child，execute_task 委托给 child，metadata 中维护 _container_depth，超 max_depth 报错；get_capabilities 返回 agent_card |
| **memory.py** | `MemoryScope`, `MemoryEntry`, `FractalMemory`, `ACCESS_POLICIES` | 作用域 LOCAL/SHARED/INHERITED/GLOBAL；MemoryEntry 含 version、created_by、updated_by；FractalMemory 按 scope 索引，read 时 INHERITED 从 parent_memory 读并缓存；写权限与 propagate 由 ACCESS_POLICIES 定义 |
| **budget.py** | `RecursiveBudget`, `BudgetTracker`, `BudgetViolation`, `QualityEvaluator`, `QualityMetrics` | 递归预算（max_depth, max_children, token/time/tool_budget）；check_can_create_child、record_*、get_remaining_budget；QualityEvaluator 用 LLM 评估 confidence/coverage/novelty |
| **synthesizer.py** | `ResultSynthesizer` | 子任务结果合成：concatenate / structured / llm；synthesize_with_quality 先评估再合成 |
| **utils.py** | `estimate_task_complexity`, `should_use_fractal` | 启发式复杂度（长度、连接词、步骤词）；是否分形由 FractalConfig + GrowthTrigger（NEVER/ALWAYS/MANUAL/COMPLEXITY）决定 |
| **resolvers.py** | `ConflictResolver`, `ParentWinsResolver`, `ChildWinsResolver`, `MergeResolver` | 父子 MemoryEntry 冲突解决；MergeResolver 深度合并 dict |
| **sync.py** | `MemorySyncManager` | 乐观锁 write_with_version_check；sync_from_parent 从父节点拉 SHARED 并按版本更新 |

### 2.3 与 memory 的衔接

- **MemoryManager**（loom/memory/manager.py）整合了 **LoomMemory** 与 **FractalMemory 的作用域**：内部用 LoomMemory 做 L1-L4，用 `_memory_by_scope`（MemoryScope → MemoryEntry）实现 Fractal 的 LOCAL/SHARED/INHERITED/GLOBAL；read 时 INHERITED 从 parent MemoryManager.read 拉取并缓存，与 FractalMemory 逻辑一致。
- **FractalMemory** 设计上可挂接 `base_memory: LoomMemory`，但当前 FractalMemory 只做 scope 索引，未在代码中把 L1-L4 存到 base_memory；**实际 L1-L4 与作用域的统一入口是 MemoryManager**。

### 2.4 NodeContainer 使用场景与依赖方向

- **NodeContainer**：实现 NodeProtocol，持**单个** child，execute_task 委托给 child 并维护 `_container_depth`；多子节点编排由 **orchestration**（如 CrewOrchestrator）负责。NodeContainer 适用于「单层包装/递归树」的显式组合，Agent 内部分形（create_plan / delegate_task）通过 meta_tools 发 Task、不直接使用 NodeContainer，因此 NodeContainer 多见于测试、自定义编排或上层 CompositeNode 式结构。
- **依赖方向**：**memory → fractal**（MemoryManager 依赖 fractal 的 MemoryScope、MemoryEntry、ACCESS_POLICIES）；fractal 仅在 TYPE_CHECKING 下引用 LoomMemory（FractalMemory.base_memory），运行时 fractal 可不依赖 memory。作用域与 INHERITED 的落地在 MemoryManager 中完成，FractalMemory 作为「纯作用域 + 父子关系」的抽象存在。

### 2.5 使用方与导出

- **Agent**：创建子 Agent 时传入 parent_memory=self.memory（MemoryManager），子节点因此具备 INHERITED 作用域与 L1-L4；BudgetTracker 在 Agent 中可选传入；分形决策（create_plan/delegate）在 agent 内用 meta_tools 实现，不直接依赖 NodeContainer。
- **fractal/__init__**：导出 NodeContainer、ResultSynthesizer、Budget*、Quality*、estimate_task_complexity、should_use_fractal；**不导出** FractalMemory、resolvers、sync（内部或由 memory 包整合使用）。若需自定义冲突策略或显式 sync_from_parent，需直接从 loom.fractal.resolvers / loom.fractal.sync 导入。
- **config**：FractalConfig、GrowthTrigger 被 utils.should_use_fractal 使用。

### 2.6 FractalMemory 与 MemoryManager / MemorySyncManager

- **FractalMemory** 与 **MemoryManager**：API 对齐（write/read/list_by_scope、INHERITED 从 parent 读并缓存）；MemoryManager 内部持 LoomMemory + _memory_by_scope，相当于「L1-L4 + Fractal 作用域」的统一入口；FractalMemory 的 base_memory 可选且当前未在包内用于 L1-L4 存储。
- **MemorySyncManager**（fractal/sync.py）：接收 **FractalMemory** 实例，提供乐观锁 write_with_version_check 与 sync_from_parent（从父节点拉 SHARED 并按版本更新）。若使用 MemoryManager 且需同类同步逻辑，需在 MemoryManager 上封装类似接口或通过适配器桥接到 FractalMemory 形态。

### 2.7 小结

- fractal 模块 = **节点容器（NodeContainer）** + **分形记忆与作用域（FractalMemory + MemoryScope/MemoryEntry）** + **递归预算与质量（BudgetTracker、QualityEvaluator）** + **结果合成（ResultSynthesizer）** + **分形工具（复杂度、是否分形）** + **冲突解决与同步（resolvers、sync）**。
- 对外主入口是 **NodeContainer** 与 **Budget/Quality/Synthesizer/Utils**；**作用域与 INHERITED** 通过 **MemoryManager** 在 memory 包中落地，与 L1-L4 一体使用。

---

## 三、两模块关系图（概念）

```
                    +------------------+
                    | loom.protocol    |
                    | Task, NodeProtocol
                    +--------+---------+
                             |
    +------------------------+------------------------+
    |                        |                        |
    v                        v                        v
+----------+          +-------------+          +----------------+
| loom.    |          | loom.       |          | loom.memory    |
| events   |          | fractal     |          | LoomMemory     |
| EventBus |          | NodeContainer|         | L1-L4, Fact    |
| "*"      |----------| BudgetTracker|         | EventBus 订阅  |
+----------+          | FractalMemory|         +-------+-+------+
    |                 | (scope 概念)  |                 |      |
    |                 +------+--------+                 |      |
    |                        |                          |      |
    |                        | 作用域 + INHERITED       |      |
    v                        v                          v      v
+----------------------------------------+    +----------------+
| loom.memory.MemoryManager              |    | context_tools  |
| _loom_memory (L1-L4)                   |    | index_context  |
| _memory_by_scope (LOCAL/SHARED/...)    |    | memory_mgmt    |
| parent → INHERITED 读                   |    | (LoomMemory 接口)
+----------------------------------------+    +----------------+
    |
    v
+----------------+
| Agent          |
| memory,        |
| parent_memory   |
+----------------+
```

---

## 四、可优化点（简要）

1. **LoomMemory 与 MemoryLayer 接口**：LoomMemory 内部 L1/L2 用 CircularBufferLayer/PriorityQueueLayer，但未通过抽象 MemoryLayer 的 async add/retrieve/evict 统一调用，而是直接操作 _buffer/_heap；若希望 L3/L4 也实现 MemoryLayer，可再对齐接口与调用路径。
2. **promote_tasks 同步版**：同步版不执行 L3→L4，注释中已说明；若调用方常只调 promote_tasks()，L4 可能长期不更新，可在文档或日志中明确「需定期调用 promote_tasks_async」。
3. **FractalMemory 与 LoomMemory 的绑定**：FractalMemory 的 base_memory 可选且当前未在包内使用；实际「L1-L4 + 作用域」由 MemoryManager 一家完成，可考虑在文档中明确 FractalMemory 为「纯作用域 + 父子关系」的抽象，L1-L4 统一由 MemoryManager 委托给 LoomMemory。
4. **resolvers / sync 的暴露**：ConflictResolver 与 MemorySyncManager 未从 fractal 包顶层的 __all__ 导出；若希望用户可插冲突策略或显式 sync_from_parent，可在 __init__ 中导出或文档中说明使用方式。
5. **ContextSource 与 MemoryManager**：task_context 中既有基于 LoomMemory 的源，也有基于 MemoryManager（作用域）的源；Agent 构建上下文时若混用，需明确各源对应 L1/L2 还是 scope，避免重复或遗漏。
6. **Agent 内 LoomMemory 访问**：context_tools 等接收 LoomMemory，Agent 持有的是 MemoryManager；当前通过 memory.add_task / memory.get_l1_tasks 等兼容接口，实际落到 _loom_memory；若工具需要直接拿 LoomMemory（如 search_facts、L4），需从 memory._loom_memory 取或统一通过 MemoryManager 再暴露一层接口。

---

## 五、快速查阅

| 用途 | 入口 | 说明 |
|------|------|------|
| 统一记忆（L1-L4 + 作用域） | `MemoryManager(node_id, parent=..., event_bus=...)` | Agent 默认使用；write/read/list_by_scope + add_task/get_l1_tasks 等 |
| 仅分层 Task 存储 | `LoomMemory(node_id, event_bus=...)` | 工具链、ContextSource 多接收 LoomMemory 或 memory._loom_memory |
| 上下文构建 | `ContextOrchestrator` + `ContextSource` 列表 | build_context(current_task) → 消息列表；预算见 BudgetConfig |
| 分形容器 | `NodeContainer(node_id, agent_card, child)` | 单子节点；多子编排用 orchestration |
| 递归预算 | `BudgetTracker(budget)` | check_can_create_child、record_*、get_remaining_budget |
| 结果合成 | `ResultSynthesizer().synthesize(...)` | concatenate / structured / llm |
| 冲突解决 / 同步 | `loom.fractal.resolvers` / `loom.fractal.sync` | 包内未导出，需直接导入；MemorySyncManager 接收 FractalMemory |

**记忆更新**：需 L4 向量化时，在异步上下文中定期或批次后调用 `memory.promote_tasks_async()`；仅调 `promote_tasks()` 不会更新 L4。

---

*文档版本：基于 loom-agent 代码库梳理，适用于 feature/agent-skill-refactor 及后续分支。*
