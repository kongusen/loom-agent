# 架构总览

## 公理体系

Loom 的设计基于四条形式化公理，所有模块的实现都可追溯到这些公理。

| 公理 | 形式化表述 | 含义 |
|------|-----------|------|
| **A2 事件主权** | `∀communication ∈ System: communication = Task` | 所有通信都是 Task 对象，通过 EventBus 路由 |
| **A3 分形自相似** | `structure(node) ≅ structure(System)` | 每个节点的结构与整个系统同构 |
| **A4 记忆层次** | `Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4` | 四层记忆，从短期到长期，token 预算递增 |
| **A6 四范式自主** | 反思 + 工具使用 + 规划 + 协作 | Agent 自主选择执行策略 |

## 四范式执行模型

Agent 以 ReAct（Reasoning + Acting）为主要工作方式，自主决策使用哪种范式：

```
┌─────────────────────────────────────────┐
│           四范式决策框架                   │
│                                         │
│  1. 反思 (Reflection)                    │
│     └─ LLM streaming 自动体现            │
│                                         │
│  2. 工具使用 (Tool Use) ← 主要方式        │
│     └─ ReAct 循环：Think → Act → Observe │
│                                         │
│  3. 规划 (Planning) ← 复杂任务时使用       │
│     └─ create_plan 元工具                │
│                                         │
│  4. 协作 (Collaboration)                 │
│     └─ delegate_task 元工具              │
└─────────────────────────────────────────┘
```

## Mixin 组合架构

Agent 类通过五个 Mixin 组合而成，每个 Mixin 负责单一职责：

```python
class Agent(
    ToolHandlerMixin,     # 工具管理与执行
    SkillHandlerMixin,    # 技能激活与管理
    PlannerMixin,         # 规划逻辑
    DelegatorMixin,       # 任务委派
    ExecutorMixin,        # 执行循环与 LLM 交互
    BaseNode,             # 生命周期、事件发布、集体记忆
):
```

## 数据流

### 任务执行流

```
用户输入
  ↓
Task 创建 (Pydantic BaseModel, A2A 协议)
  ↓
InterceptorChain (SessionLaneInterceptor 等)
  ↓
BaseNode._execute_task_with_lifecycle()
  ↓  on_start → _execute_impl → on_complete/on_error
  ↓
ExecutionEngine.run()
  ↓
ContextOrchestrator.build() → 构建 LLM 上下文
  ↓
LLM Chat (streaming)
  ↓
ToolRouter.route() → 工具执行
  ↓
MemoryManager → 记忆更新
  ↓
Task.result (完成)
```

### 上下文构建流

```
ContextOrchestrator.build()
  ↓
ContextCollector.collect() ← 多源收集
  ├─ L1RecentSource      (最近交互)
  ├─ L2ImportantSource    (重要记忆)
  ├─ InheritedSource      (父节点上下文)
  └─ UnifiedRetrievalSource (L4 语义 + RAG 知识库)
  ↓
AdaptiveBudgetManager → token 预算分配
  ↓
ContextCompactor → 超预算时压缩
  ↓
LLM-ready 消息列表
```

### 记忆更新流

```
任务完成
  ↓
提取 importance 标记 (<imp:X.X/>)
  ↓
MemoryManager.add_task() → LoomMemory
  ↓
路由到对应层 (L1/L2 基于重要性)
  ↓
超容量时自动迁移 (L1→L2→L3→L4)
  ↓
MemoryCompactor 压缩 (FactExtractor 提取关键事实)
  ↓
L4 超阈值时 → L4Compressor
  ├─ 聚类压缩 (余弦相似度 + 并查集)
  ├─ FidelityChecker 保真度检查
  │   ├─ 通过 → 使用合并结果 (metadata 附加 fidelity 指标)
  │   └─ 不通过 → 保留原始 facts
  └─ 无 embedding → 按重要性保留 top-N
```

## 继承规则

分形架构中，父子节点的资源继承遵循以下规则：

| 类型 | 资源 | 说明 |
|------|------|------|
| **共享** | `skill_registry`, `tool_registry`, `event_bus`, `sandbox_manager`, `shared_pool` | 全局单例，所有节点共用 |
| **继承** | `config` (AgentConfig) | 子节点继承父节点配置，可增量覆盖 |
| **独立** | `active_skills`, `memory` (MemoryManager) | 每个节点独立实例 |

## 模块依赖关系

```
loom/
├── runtime/        ← 基础层：Task, TaskStatus (无外部依赖)
├── events/         ← 通信层：EventBus, Transport (依赖 runtime)
├── memory/         ← 存储层：LoomMemory, MemoryManager (依赖 runtime, events)
├── context/        ← 编排层：ContextOrchestrator (依赖 memory)
├── tools/          ← 工具层：Registry, Sandbox, Skills (依赖 events)
├── providers/      ← 集成层：LLM, Knowledge, MCP, Embedding
├── config/         ← 配置层：渐进式披露配置
├── security/       ← 安全层：ToolPolicy
├── fractal/        ← 组合层：NodeContainer, ParallelExecutor
├── observability/  ← 观测层：Tracing, Metrics
├── api/            ← API 层：StreamAPI, Version
└── agent/          ← 顶层：Agent (组合所有模块)
```
