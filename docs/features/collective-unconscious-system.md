# 集体潜意识系统设计

> **版本**: v0.4.0-alpha
> **基于**: Loom公理系统 + 用户洞察
> **状态**: 设计完成，待实现

## 摘要

本文档描述了基于EventBus的**集体潜意识（Collective Unconscious）**系统设计，实现了分形结构中节点间的深度信息共享和上下文自主构建。

**核心理念**：
- EventBus不仅是通信机制，更是"集体记忆"
- 节点可以主动从EventBus搜索需要的信息
- 分形结构中的所有节点共享一个"集体潜意识"

---

## 核心概念

### 1. 集体潜意识（Collective Unconscious）

**灵感来源**：荣格心理学中的"集体潜意识"概念

**在Loom中的体现**：
```
传统模型（结果到结果）：
节点A → 结果A → 节点B（只能看到结果A）

集体潜意识模型：
节点A → 思考过程 → EventBus（集体记忆）
节点B → 思考过程 → EventBus
节点C → 从EventBus搜索需要的信息（可以看到A、B的所有过程）
```

**关键特性**：
1. **共享记忆** - 所有节点的思考过程都记录在EventBus中
2. **主动搜索** - 节点可以主动查询需要的信息
3. **上下文增强** - 节点自动获取相关的集体记忆作为上下文
4. **兄弟洞察** - 节点可以看到兄弟节点的思考过程
5. **父节点上下文** - 节点可以访问父节点的上下文

### 2. 上下文自主构建

**传统模型**（被动接收）：
```
父节点 → 构建上下文 → 传递给子节点
```
问题：父节点需要预测子节点需要什么信息

**新模型**（主动构建）：
```
子节点 → 从EventBus查询 → 自主构建上下文
```
优势：子节点根据自己的需求获取信息

### 3. 分形结构的增强

**传统分形**：
```
父节点
├── 子节点1（独立）
├── 子节点2（独立）
└── 子节点3（独立）
```

**集体潜意识分形**：
```
父节点 ──┐
         │
子节点1 ──┼──→ EventBus（集体记忆）
         │
子节点2 ──┤    ↑ 所有节点都可以查询
         │    │
子节点3 ──┘    └─ 共享的集体潜意识
```

---

## 公理依据

### 公理A2（事件主权）

**形式化表述**：
```
∀communication ∈ System: communication = Task
```

**在集体潜意识中的体现**：
- 所有思考过程都是Task事件
- Task事件可以被查询和检索
- 天然支持"集体记忆"

### 公理A4（记忆层次）

**形式化表述**：
```
Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4
```

**EventBus作为L2工作记忆**：
- L1: 原始IO（节点内部）
- **L2: EventBus（集体工作记忆）** ← 新定位
- L3: 会话记忆
- L4: 全局知识库

### 公理A5（认知调度）

**形式化表述**：
```
Cognition = Orchestration(N1, N2, ..., Nk)
```

**集体潜意识是认知涌现的基础**：
- 节点间的协作需要共享信息
- 集体记忆使得协作更加智能
- 认知是网络涌现，集体潜意识是基础

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    QueryableEventBus                         │
│                   (可查询事件总线)                            │
│                                                               │
│  - 事件历史记录                                               │
│  - 多维度索引（节点ID、动作类型、任务ID）                     │
│  - 查询接口                                                   │
│  - 集体记忆API                                                │
└────────┬──────────────────────────────────┬─────────────────┘
         │                                   │
         │ publish events                    │ query events
         │                                   │
┌────────▼──────────────┐          ┌────────▼─────────────────┐
│ CollectiveAgent       │          │   ContextBuilder         │
│ (集体潜意识Agent)      │          │   (上下文构建器)          │
│                       │          │                          │
│ - 发布思考过程         │          │ - 查询相关事件            │
│ - 查询集体记忆         │          │ - 构建增强上下文          │
│ - 自主构建上下文       │          │ - 搜索相关信息            │
└───────────────────────┘          └──────────────────────────┘
```

### 核心组件

#### 1. QueryableEventBus

**文件**: `loom/events/queryable_event_bus.py`

**功能**：
- 继承自EventBus
- 记录所有事件到历史
- 提供多维度查询接口
- 实现集体记忆API

**查询接口**：
```python
# 按节点查询
events = event_bus.query_by_node("agent-1", action_filter="node.thinking")

# 按动作查询
events = event_bus.query_by_action("node.thinking", node_filter="agent-1")

# 按任务查询
events = event_bus.query_by_task("task-123")

# 查询最近事件
events = event_bus.query_recent(limit=10)

# 查询思考过程
thoughts = event_bus.query_thinking_process(node_id="agent-1")

# 获取集体记忆
collective = event_bus.get_collective_memory(limit=50)
```

#### 2. ContextBuilder

**文件**: `loom/memory/context_builder.py`

**功能**：
- 从EventBus构建上下文
- 提取兄弟节点洞察
- 提取父节点上下文
- 搜索相关事件

**核心方法**：
```python
# 为节点构建上下文
context = builder.build_context_for_node(
    node_id="agent-1",
    task_id="task-123",
    include_siblings=True,
    include_parent=True,
)

# 构建思考摘要
summary = builder.build_thinking_summary(node_id="agent-1")

# 搜索相关事件
events = builder.search_relevant_events("analysis", limit=10)

# 获取集体洞察
insights = builder.get_collective_insights(topic="data")
```

#### 3. CollectiveUnconsciousAgent

**文件**: `loom/orchestration/collective_agent.py`

**功能**：
- 继承自ObservableAgent
- 在执行前构建增强上下文
- 将集体记忆融入LLM提示
- 支持主动搜索集体记忆

**执行流程**：
```python
async def _execute_impl(self, task: Task) -> Task:
    # 1. 构建增强上下文（包含集体记忆）
    enhanced_context = await self._build_enhanced_context(task)

    # 2. 发布上下文构建事件
    await self._publish_event("node.context_built", ...)

    # 3. 构建消息（包含集体记忆）
    messages = self._build_messages_with_context(task, enhanced_context)

    # 4. 使用流式LLM
    async for chunk in self.llm_provider.stream_chat(messages):
        # 处理并发布思考过程
        ...
```

---

## 实现细节

### 1. 事件索引策略

**多维度索引**：
```python
# 按节点ID索引
_events_by_node: dict[str, list[Task]]

# 按动作类型索引
_events_by_action: dict[str, list[Task]]

# 按任务ID索引
_events_by_task: dict[str, list[Task]]
```

**优势**：
- O(1)查询复杂度
- 支持多种查询模式
- 高效的事件检索

### 2. 上下文构建策略

**上下文结构**：
```python
context = {
    "node_id": "agent-1",
    "task_id": "task-123",
    "self_history": [...],        # 自己的历史
    "sibling_insights": [...],    # 兄弟节点洞察
    "parent_context": [...],      # 父节点上下文
    "collective_memory": {...},   # 集体记忆
}
```

**构建流程**：
```
1. 查询自己的历史事件
2. 查询同一任务下的兄弟节点事件
3. 查询父任务的上下文
4. 获取集体记忆摘要
5. 组合成增强上下文
```

### 3. 集体记忆格式化

**格式化为LLM提示**：
```
=== Collective Memory (集体记忆) ===

## Sibling Insights (兄弟节点洞察):
- [child-agent-1]: Analyzed Q4 sales trends...
- [child-agent-2]: Created visualization...

## Parent Context (父节点上下文):
- [parent-agent]: Coordinating data analysis...

## Collective Insights (集体洞察):
- [agent-1]: Found interesting pattern...
- [agent-2]: Identified key metrics...

=== End of Collective Memory ===
```

---

## 使用指南

### 1. 创建可查询事件总线

```python
from loom.events.queryable_event_bus import QueryableEventBus
from loom.events.memory_transport import MemoryTransport

transport = MemoryTransport()
event_bus = QueryableEventBus(
    transport=transport,
    max_history=1000,  # 最大历史事件数
)
```

### 2. 创建集体潜意识Agent

```python
from loom.orchestration.collective_agent import CollectiveUnconsciousAgent

agent = CollectiveUnconsciousAgent(
    node_id="my-agent",
    llm_provider=provider,
    system_prompt="You are a helpful agent.",
    event_bus=event_bus,  # 注入可查询事件总线
    enable_collective_memory=True,  # 启用集体记忆
)
```

### 3. 执行任务（自动获取集体记忆）

```python
task = Task(
    task_id="task-1",
    source_agent="user",
    target_agent=agent.node_id,
    action="execute",
    parameters={"content": "Analyze the data."},
)

result = await agent.execute_task(task)
# Agent会自动从EventBus获取相关的集体记忆作为上下文
```

### 4. 查询集体记忆

```python
from loom.memory.context_builder import ContextBuilder

builder = ContextBuilder(event_bus)

# 查询思考过程
thoughts = event_bus.query_thinking_process(node_id="agent-1")

# 获取集体洞察
insights = builder.get_collective_insights(limit=20)

# 搜索相关事件
events = builder.search_relevant_events("analysis", limit=10)
```

---

## 关键优势

### 1. 增强的问题解决能力

**场景**：复杂的数据分析任务

**传统方式**：
```
父节点 → 分解任务 → 子节点1（数据分析）
                  → 子节点2（可视化，不知道子节点1的分析过程）
```

**集体潜意识方式**：
```
父节点 → 分解任务 → 子节点1（数据分析）→ EventBus
                  → 子节点2（可视化，可以看到子节点1的分析过程）
                              ↓
                         自动获取子节点1的洞察
```

### 2. 减少重复工作

**场景**：多个节点需要相同的背景信息

**传统方式**：
- 父节点需要重复传递相同信息给每个子节点
- 信息冗余，增加通信开销

**集体潜意识方式**：
- 信息一次性记录在EventBus中
- 所有节点按需查询
- 零冗余，高效共享

### 3. 支持动态协作

**场景**：节点在执行过程中需要其他节点的信息

**传统方式**：
- 需要显式的节点间通信
- 需要父节点协调

**集体潜意识方式**：
- 节点直接从EventBus查询
- 无需父节点介入
- 真正的自主协作

---

## 性能考虑

### 1. 事件历史大小限制

**策略**：循环缓冲区
```python
event_bus = QueryableEventBus(max_history=1000)
```

**效果**：
- 限制内存使用
- 保留最近的事件
- 自动淘汰旧事件

### 2. 查询优化

**索引策略**：
- 多维度索引（节点、动作、任务）
- O(1)查询复杂度
- 空间换时间

**查询限制**：
```python
# 限制返回数量
events = event_bus.query_by_node("agent-1", limit=10)
```

### 3. 上下文大小控制

**策略**：
- 只提取最近的N个事件
- 只包含相关的事件类型
- 智能过滤和摘要

```python
context = builder.build_context_for_node(
    node_id="agent-1",
    task_id="task-123",
    max_events=20,  # 限制事件数量
)
```

---

## 与现有系统的集成

### 1. 与分形结构集成

**NodeContainer兼容**：
```python
# 创建集体潜意识子节点
child = CollectiveUnconsciousAgent(
    node_id="child",
    llm_provider=provider,
    event_bus=event_bus,  # 共享事件总线
)

# 包装在分形容器中
container = NodeContainer(
    node_id="container",
    child=child,
)

# 执行任务
result = await container.execute_task(task)
# 子节点会自动发布和查询集体记忆
```

### 2. 与记忆系统集成

**EventBus作为L2工作记忆**：
```
L1 (Raw IO) → 节点内部
L2 (Working) → EventBus（集体工作记忆）← 新定位
L3 (Session) → 会话记忆
L4 (Global) → 全局知识库
```

**优势**：
- 统一的记忆层次
- EventBus自然融入记忆系统
- 支持记忆代谢和压缩

### 3. 与流式输出集成

**完全兼容**：
- CollectiveAgent继承自ObservableAgent
- 保留所有流式输出功能
- 增加了集体记忆功能

---

## 未来扩展

### 1. 语义搜索

**当前**：简单的关键词匹配
```python
events = builder.search_relevant_events("analysis")
```

**未来**：基于向量的语义搜索
```python
events = builder.semantic_search(
    query="Find insights about sales trends",
    embedding_model=embedding_model,
)
```

### 2. 智能过滤

**当前**：基于规则的过滤
**未来**：基于LLM的智能过滤
```python
context = builder.build_context_with_llm_filter(
    node_id="agent-1",
    task_description="Analyze Q4 sales",
    llm_provider=provider,
)
```

### 3. 集体记忆压缩

**当前**：简单的数量限制
**未来**：智能压缩和摘要
```python
compressed = event_bus.compress_collective_memory(
    strategy="semantic_clustering",
    target_size=100,
)
```

---

## 总结

### 核心贡献

1. **集体潜意识概念** - 将EventBus定位为"集体记忆"
2. **上下文自主构建** - 节点主动从EventBus获取信息
3. **分形结构增强** - 所有节点共享集体潜意识
4. **公理系统符合** - 完全基于A2、A4、A5公理

### 关键优势

1. **增强问题解决** - 节点可以访问其他节点的思考过程
2. **减少重复工作** - 信息共享，零冗余
3. **支持动态协作** - 节点自主协作，无需父节点介入
4. **架构优雅** - 简洁、高效、易扩展

### 下一步

1. **运行演示** - 验证设计
2. **编写测试** - 确保正确性
3. **性能优化** - 提升查询效率
4. **语义搜索** - 增强搜索能力

---

**结语**：

集体潜意识系统是对Loom框架的重要增强，它将EventBus从简单的通信机制提升为"集体记忆"，使得分形结构中的节点可以真正地协作和共享信息。这种设计完全符合公理系统，并且极大地增强了框架处理复杂问题的能力。
