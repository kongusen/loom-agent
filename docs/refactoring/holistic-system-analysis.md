# Loom Agent 整体系统分析与重构方案

**作者**: Claude Code
**日期**: 2026-01-29
**目的**: 从整体视角分析 EventBus、Context、Memory、Task 四大系统的依赖关系，识别跨系统架构问题，提出统一的重构方案

---

## 第一部分：系统依赖分析

### 1.1 核心发现：Task 作为通用数据结构的过载

通过深入分析代码，我发现了一个**根本性的架构问题**：

> **Task 被用作系统中的"万能数据结构"，承担了远超其设计初衷的多重职责。**

#### Task 的五重身份

| 身份 | 用途 | 代码位置 | 问题 |
|------|------|----------|------|
| **1. 工作单元** | 执行任务，需要响应 | `protocol/task.py` | ✓ 原始设计目的 |
| **2. 事件通知** | 观测节点行为 | `base_node.py:129-143` | ✗ 无状态事件被强制加状态 |
| **3. 消息传递** | 节点间通信 | `event_bus.py:93-155` | ✗ 点对点消息被当作任务 |
| **4. 记忆存储** | L1-L4 持久化 | `memory/core.py:89-109` | ✗ 存储粒度过粗 |
| **5. 上下文输入** | LLM 消息转换 | `memory/task_context.py:386-449` | ✗ 转换逻辑复杂 |

**核心问题**：Task 是为 A2A 协议设计的**有状态工作单元**，但被强制用于**无状态事件通知**、**消息传递**、**记忆存储**等场景，导致语义混乱和架构扭曲。

### 1.2 系统依赖关系图

```
┌─────────────────────────────────────────────────────────────┐
│                        BaseNode                              │
│  - 创建 Task 对象（工作 + 事件）                              │
│  - 发布到 EventBus                                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        EventBus                              │
│  - 存储 Task 到 _event_history                               │
│  - 修改 Task.status (RUNNING/COMPLETED/FAILED)              │
│  - 提供查询接口（by_node, by_action, by_task, by_target）   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        Memory                                │
│  - L1: 存储完整 Task（CircularBufferLayer）                  │
│  - L2: 存储重要 Task（PriorityQueueLayer）                   │
│  - L3: 存储 TaskSummary（压缩）                              │
│  - L4: 向量化 TaskSummary                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   TaskContextManager                         │
│  - 从 Memory 获取 L1 tasks                                   │
│  - 从 EventBus 获取 direct/bus events                        │
│  - 分配 token 预算（L1: 30%, L2: 25%, L3/L4: 20%）          │
│  - 转换 Task → LLM messages                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        Context                               │
│  - 提供给 LLM 的消息列表                                      │
│  - 影响节点的执行决策                                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
                        (循环回 BaseNode)
```

**关键洞察**：这是一个**紧耦合的循环依赖链**，Task 作为唯一的数据结构在各个系统间流转，每个系统都对 Task 有不同的理解和操作。

### 1.3 具体依赖问题分析

#### 问题 1：EventBus 与 Memory 的重复存储

**现状**：
- EventBus 存储 Task 到 `_event_history`（event_bus.py:167）
- Memory 存储 Task 到 L1/L2 层（memory/core.py:110-121, 163-186）
- 两者存储的是**同一个 Task 对象**，但用途不同

**问题**：
```python
# EventBus 存储（用于事件查询）
self._event_history.append(task)  # event_bus.py:167

# Memory 存储（用于上下文构建）
self._l1_layer._buffer.append(task)  # memory/core.py:120
```

**影响**：
- 数据冗余：同一个 Task 被存储两次
- 同步问题：EventBus 修改 Task.status 后，Memory 中的 Task 也被修改（共享引用）
- 职责不清：EventBus 应该存储"事件"，Memory 应该存储"记忆"，但都存储 Task

#### 问题 2：EventBus 修改业务状态

**现状**：
```python
# event_bus.py:114 - 强制设置 RUNNING
task.status = TaskStatus.RUNNING

# event_bus.py:148 - 强制设置 COMPLETED
result_task.status = TaskStatus.COMPLETED

# event_bus.py:129 - 无 handler 即 FAILED
task.status = TaskStatus.FAILED
```

**问题**：
- EventBus 是**传输层**，不应该修改**业务层**的状态
- Handler 返回的状态被强制覆盖（如 handler 返回 FAILED，但被改成 COMPLETED）
- 观测事件（无 handler）被误标为 FAILED

**根本原因**：Task 既是"工作单元"又是"事件通知"，EventBus 无法区分

#### 问题 3：TaskContextManager 的复杂性爆炸

**现状**：
- TaskContextManager 有 941 行代码（task_context.py）
- 集成了 Memory、EventBus、KnowledgeBase、Embedding 等多个系统
- `build_context()` 方法有 149 行（746-894）

**复杂度来源**：
```python
# 1. 从 Memory 获取 L1 tasks
l1_tasks = source.memory.get_l1_tasks(limit=10)

# 2. 从 EventBus 获取 direct messages
direct_events = event_bus.query_by_target(target_agent=self.node_id, ...)

# 3. 从 EventBus 获取 bus messages（需要排序）
candidates.extend(event_bus.query_by_task(current_task.task_id))
candidates.extend(event_bus.query_recent(limit=50))
# ... 复杂的排序和筛选逻辑

# 4. Token 预算分配
allocation = self.budgeter.allocate_budget(...)

# 5. Task → LLM Message 转换
messages = self.converter.convert_tasks_to_messages(tasks)

# 6. 知识库查询
knowledge_items = await self.knowledge_base.query(query, limit=3)
```

**问题**：
- 单一类承担了太多职责（查询、排序、预算、转换、合并）
- 难以测试和维护
- 性能瓶颈（每次构建上下文都要查询多个系统）

**根本原因**：缺少清晰的抽象层，直接在 TaskContextManager 中集成所有系统

#### 问题 4：Memory 与 EventBus 的职责重叠

**现状**：
- Memory 存储 Task 用于"记忆"（长期保留）
- EventBus 存储 Task 用于"事件查询"（短期历史）
- TaskContextManager 同时查询两者

**职责混乱**：
```python
# Memory 的职责（应该是）
- 存储重要的工作记忆（L2）
- 压缩和总结（L3）
- 语义检索（L4）

# EventBus 的职责（应该是）
- 路由和分发任务
- 提供实时事件流
- 不应该长期存储

# 实际情况
- Memory 存储完整 Task（L1/L2）
- EventBus 也存储完整 Task（_event_history）
- 两者都提供查询接口，功能重叠
```

**影响**：
- 数据冗余和不一致
- 查询逻辑分散（有时查 Memory，有时查 EventBus）
- 难以决定"应该存储在哪里"

---

## 第二部分：跨系统架构问题

### 2.1 根本问题总结

通过深入分析，我识别出 **3 个根本性的架构问题**：

#### 根本问题 1：数据结构过载 - Task 的多重身份危机

**问题本质**：
> Task 被设计为 A2A 协议的**有状态工作单元**，但被强制用于**无状态事件**、**消息传递**、**记忆存储**、**上下文输入**等多种场景。

**类比**：
> 这就像用"快递单"（Task）来表示"商品"、"通知信"、"账单"、"收据"。虽然都是纸质文档，但语义完全不同。

**影响**：
- EventBus 无法区分"任务"和"事件"，导致状态管理混乱
- Memory 存储粒度过粗，无法区分"工作记忆"和"事件记忆"
- Context 构建复杂，需要复杂的转换逻辑

**解决方向**：
- 引入专门的 Event 类型（无状态通知）
- 引入专门的 Message 类型（点对点通信）
- Task 回归本质：有状态的工作单元

#### 根本问题 2：职责边界模糊 - 存储与传输的混淆

**问题本质**：
> EventBus 既是"传输层"（路由和分发），又是"存储层"（事件历史），职责混乱。
> Memory 既存储"工作记忆"，又存储"事件记忆"，边界不清。

**类比**：
> 这就像快递公司（EventBus）既负责运输，又负责仓储。邮局（Memory）既存储信件，又存储包裹。

**影响**：
- EventBus 的 _event_history 与 Memory 的 L1 功能重叠
- 数据冗余和同步问题
- 难以决定"应该存储在哪里"

**解决方向**：
- EventBus 专注于传输和路由，不长期存储
- Memory 专注于记忆管理，不关心传输
- 引入专门的 EventStore（如果需要长期事件历史）

#### 根本问题 3：集成层过度复杂 - 缺少清晰的抽象

**问题本质**：
> TaskContextManager 直接集成了 Memory、EventBus、KnowledgeBase、Embedding 等多个系统，缺少中间抽象层。

**类比**：
> 这就像一个"超级管家"（TaskContextManager）直接管理厨房、卧室、客厅、车库，没有分区管理。

**影响**：
- 单一类 941 行代码，难以维护
- 查询逻辑分散，难以优化
- 测试困难，依赖太多

**解决方向**：
- 引入 ContextSource 抽象（统一的上下文来源接口）
- 引入 ContextBuilder 分层（查询层、排序层、转换层、合并层）
- 每个系统提供独立的 ContextSource 实现

### 2.2 架构问题的影响范围

| 问题 | 影响系统 | 严重度 | 影响 |
|------|---------|--------|------|
| **Task 多重身份** | EventBus, Memory, Context | P0 | 语义混乱，状态失真 |
| **EventBus 修改状态** | EventBus, Task | P0 | Handler 返回值被覆盖 |
| **重复存储** | EventBus, Memory | P1 | 数据冗余，同步问题 |
| **职责重叠** | EventBus, Memory | P1 | 查询逻辑分散 |
| **集成复杂** | TaskContextManager | P1 | 难以维护和测试 |
| **转换复杂** | MessageConverter | P2 | 性能瓶颈 |

**关键洞察**：
> 这些问题不是孤立的 bug，而是**系统性的架构缺陷**。零散修补无法根治，需要**整体重构**。

---

## 第三部分：整体重构方案

### 3.1 核心设计原则

基于第一性原理，重构必须遵循以下核心原则：

#### 原则 1：数据结构分离 - 单一职责

**原则**：
> 每种数据结构只服务于一个明确的目的，不承担多重职责。

**具体实施**：
```python
# Task - 有状态的工作单元（A2A 协议）
@dataclass
class Task:
    task_id: str
    status: TaskStatus  # 有状态
    result: Any         # 需要结果
    # 用于：任务执行、工作流编排

# Event - 无状态的通知消息（观测）
@dataclass
class Event:
    event_id: str
    event_type: str
    data: dict          # 无状态，只是通知
    # 用于：节点观测、系统监控

# Message - 点对点通信
@dataclass
class Message:
    message_id: str
    from_node: str
    to_node: str
    content: Any
    # 用于：节点间直接通信

# MemoryEntry - 记忆存储单元
@dataclass
class MemoryEntry:
    entry_id: str
    content: str        # 压缩后的内容
    importance: float
    timestamp: datetime
    # 用于：L1-L4 记忆存储
```

**关键规则**：
- ✓ Task 用于任务执行（需要响应）
- ✓ Event 用于事件通知（不需要响应）
- ✓ Message 用于点对点通信（可选响应）
- ✓ MemoryEntry 用于记忆存储（压缩表示）

#### 原则 2：职责分离 - 传输与存储解耦

**原则**：
> 传输层（EventBus）专注于路由和分发，不负责长期存储。
> 存储层（Memory）专注于记忆管理，不关心传输细节。

**具体实施**：
```
┌─────────────────────────────────────────┐
│         传输层 (Transport Layer)         │
│  - EventBus: 路由和分发                  │
│  - MessageBus: 点对点通信                │
│  - 不长期存储（最多保留最近 N 条）        │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│         存储层 (Storage Layer)           │
│  - Memory: L1-L4 记忆管理                │
│  - EventStore: 事件历史（可选）          │
│  - 不关心传输细节                        │
└─────────────────────────────────────────┘
```

**关键规则**：
- ✗ EventBus 不应该有 `_event_history`（长期存储）
- ✓ EventBus 只保留最近的事件（用于调试，如最近 100 条）
- ✓ Memory 订阅 EventBus，选择性存储重要事件
- ✓ 如果需要完整事件历史，使用专门的 EventStore

#### 原则 3：抽象分层 - 清晰的接口边界

**原则**：
> 引入清晰的抽象层，避免直接耦合。

**具体实施**：
```
┌─────────────────────────────────────────┐
│         应用层 (Application)             │
│  - BaseNode                              │
│  - Agent                                 │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│         上下文层 (Context Layer)         │
│  - ContextBuilder                        │
│  - ContextSource (抽象接口)              │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│         服务层 (Service Layer)           │
│  - Memory (实现 ContextSource)           │
│  - EventStore (实现 ContextSource)       │
│  - KnowledgeBase (实现 ContextSource)    │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│         基础设施层 (Infrastructure)      │
│  - EventBus                              │
│  - MessageBus                            │
│  - VectorStore                           │
└─────────────────────────────────────────┘
```

**关键规则**：
- ✓ 每层只依赖下一层的抽象接口
- ✓ 上层不直接访问底层实现
- ✓ 通过依赖注入实现解耦

### 3.2 新架构设计

#### 架构全景图

```
┌─────────────────────────────────────────────────────────────┐
│                      应用层 (Application)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ BaseNode │  │  Agent   │  │ Workflow │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    上下文层 (Context Layer)                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              ContextBuilder                           │  │
│  │  - 查询多个 ContextSource                             │  │
│  │  - 排序和筛选                                         │  │
│  │  - Token 预算分配                                     │  │
│  │  - 转换为 LLM 消息                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    服务层 (Service Layer)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Memory     │  │  EventStore  │  │KnowledgeBase │      │
│  │(ContextSrc)  │  │(ContextSrc)  │  │(ContextSrc)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 基础设施层 (Infrastructure)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  EventBus    │  │ MessageBus   │  │ VectorStore  │      │
│  │(传输+路由)   │  │(点对点通信)  │  │(向量检索)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

#### 核心组件设计

**1. 数据结构层**

```python
# protocol/event.py - 新增
@dataclass
class Event:
    """无状态事件通知"""
    event_id: str
    event_type: str  # "node.thinking", "node.tool_call", etc.
    source_node: str
    data: dict[str, Any]
    timestamp: datetime
    session_id: str | None = None

    # 不包含 status 字段（无状态）

# protocol/message.py - 新增
@dataclass
class Message:
    """点对点通信消息"""
    message_id: str
    from_node: str
    to_node: str
    content: Any
    priority: float = 0.5
    ttl_seconds: int | None = None
    timestamp: datetime

# memory/types.py - 修改
@dataclass
class MemoryEntry:
    """记忆存储单元（替代直接存储 Task）"""
    entry_id: str
    entry_type: str  # "task", "event", "message", "summary"
    content: str  # 压缩后的文本表示
    importance: float
    timestamp: datetime
    metadata: dict[str, Any]

    # 可以从 Task/Event/Message 转换而来
    @classmethod
    def from_task(cls, task: Task) -> "MemoryEntry":
        return cls(
            entry_id=task.task_id,
            entry_type="task",
            content=f"{task.action}: {task.parameters}",
            importance=task.metadata.get("importance", 0.5),
            timestamp=task.created_at,
            metadata={"status": task.status.value, "result": task.result}
        )
```

**2. EventBus 重构**

```python
class EventBus:
    """
    事件总线 - 专注于传输和路由

    职责：
    - 路由 Task（工作单元）
    - 路由 Event（事件通知）
    - 不长期存储（只保留最近 100 条用于调试）
    - 不修改 Task.status（由 handler 决定）
    """

    def __init__(self, transport: Transport | None = None):
        self._task_handlers: dict[str, list[TaskHandler]] = defaultdict(list)
        self._event_handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._transport = transport

        # 只保留最近的事件（用于调试）
        self._recent_events: deque[Event] = deque(maxlen=100)

    async def publish_task(self, task: Task, wait_result: bool = True) -> Task:
        """发布任务（不修改 status）"""
        handlers = self._task_handlers.get(task.action, [])

        if not handlers:
            # 不修改 status，返回原始 task
            return task

        if wait_result:
            # 执行 handler，返回 handler 的结果
            result_task = await handlers[0](task)
            return result_task  # 保留 handler 返回的 status
        else:
            # Fire-and-forget
            asyncio.create_task(handlers[0](task))
            return task

    async def publish_event(self, event: Event) -> None:
        """发布事件（无状态通知）"""
        # 记录到最近事件（用于调试）
        self._recent_events.append(event)

        # 找到所有匹配的 handler
        handlers = self._event_handlers.get(event.event_type, [])

        # 并发执行所有 handler（不只是第一个）
        tasks = [handler(event) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)
```

**3. Memory 重构**

```python
class LoomMemory:
    """
    记忆系统 - 专注于记忆管理

    职责：
    - 存储 MemoryEntry（不是 Task）
    - L1-L4 分层管理
    - 订阅 EventBus，选择性存储重要事件
    """

    def __init__(self, node_id: str, event_bus: EventBus | None = None):
        self.node_id = node_id
        self._l1_entries: deque[MemoryEntry] = deque(maxlen=50)
        self._l2_entries: list[MemoryEntry] = []
        # ... L3/L4

        # 订阅 EventBus（如果提供）
        if event_bus:
            event_bus.register_event_handler("node.thinking", self._on_thinking_event)
            event_bus.register_event_handler("node.tool_call", self._on_tool_call_event)

    async def _on_thinking_event(self, event: Event) -> None:
        """处理思考事件（选择性存储）"""
        # 转换为 MemoryEntry
        entry = MemoryEntry(
            entry_id=event.event_id,
            entry_type="event",
            content=event.data.get("content", ""),
            importance=0.7,  # 思考事件重要性较高
            timestamp=event.timestamp,
            metadata={"event_type": event.event_type}
        )

        # 添加到 L1
        self._l1_entries.append(entry)

    def add_task_result(self, task: Task) -> None:
        """存储任务结果（转换为 MemoryEntry）"""
        entry = MemoryEntry.from_task(task)

        # 根据重要性决定存储层级
        if entry.importance > 0.6:
            self._l2_entries.append(entry)
        else:
            self._l1_entries.append(entry)

    def query_entries(
        self,
        entry_type: str | None = None,
        limit: int = 10
    ) -> list[MemoryEntry]:
        """查询记忆条目"""
        entries = list(self._l1_entries) + self._l2_entries

        if entry_type:
            entries = [e for e in entries if e.entry_type == entry_type]

        return entries[-limit:]
```

**4. ContextBuilder 重构**

```python
class ContextBuilder:
    """
    上下文构建器 - 简化的集成层

    职责：
    - 查询多个 ContextSource
    - 排序和筛选
    - Token 预算分配
    - 转换为 LLM 消息
    """

    def __init__(
        self,
        sources: list[ContextSource],
        token_counter: TokenCounter,
        max_tokens: int = 4000
    ):
        self.sources = sources
        self.token_counter = token_counter
        self.max_tokens = max_tokens

    async def build_context(
        self,
        current_task: Task
    ) -> list[dict[str, str]]:
        """构建上下文（简化版）"""
        # 1. 从所有 sources 收集条目
        all_entries: list[MemoryEntry] = []
        for source in self.sources:
            entries = await source.get_entries(current_task, limit=20)
            all_entries.extend(entries)

        # 2. 排序（按重要性和时间）
        all_entries.sort(
            key=lambda e: (e.importance, e.timestamp.timestamp()),
            reverse=True
        )

        # 3. 转换为 LLM 消息
        messages = []
        total_tokens = 0

        for entry in all_entries:
            msg = {"role": "assistant", "content": entry.content}
            msg_tokens = self.token_counter.count_messages([msg])

            if total_tokens + msg_tokens > self.max_tokens:
                break

            messages.append(msg)
            total_tokens += msg_tokens

        return messages
```

### 3.3 关键改进总结

| 问题 | 旧设计 | 新设计 | 改进 |
|------|--------|--------|------|
| **Task 多重身份** | Task 用于所有场景 | Task/Event/Message/MemoryEntry 分离 | 语义清晰，职责单一 |
| **EventBus 修改状态** | 强制设置 RUNNING/COMPLETED | 不修改 status，由 handler 决定 | Handler 返回值不被覆盖 |
| **重复存储** | EventBus 和 Memory 都存储 Task | EventBus 不长期存储，Memory 存储 MemoryEntry | 消除冗余，职责清晰 |
| **职责重叠** | EventBus 有 _event_history | EventBus 只保留最近 100 条 | 传输与存储分离 |
| **集成复杂** | TaskContextManager 941 行 | ContextBuilder 简化，通过 ContextSource 抽象 | 易于维护和测试 |
| **只执行第一个 handler** | `handlers[0]` | 执行所有匹配的 handler | 支持多订阅者 |

---

## 第四部分：实施路线图

### 4.1 实施策略

**核心原则**：渐进式重构，保持向后兼容

```
阶段 1: 数据结构分离（2-3周）
  ↓
阶段 2: EventBus 重构（2-3周）
  ↓
阶段 3: Memory 重构（2-3周）
  ↓
阶段 4: Context 重构（1-2周）
  ↓
阶段 5: 清理和优化（持续）
```

### 4.2 阶段 1：数据结构分离（P0）

**目标**：引入 Event、Message、MemoryEntry，建立清晰的数据结构边界

**任务清单**：

1. **创建新的数据结构**
   - [ ] 创建 `protocol/event.py` - Event 类
   - [ ] 创建 `protocol/message.py` - Message 类
   - [ ] 修改 `memory/types.py` - 添加 MemoryEntry 类
   - [ ] 添加转换方法（Task → MemoryEntry, Event → MemoryEntry）

2. **更新 BaseNode**
   - [ ] 修改 `publish_thinking()` 使用 Event 而不是 Task
   - [ ] 修改 `publish_tool_call()` 使用 Event 而不是 Task
   - [ ] 保持向后兼容（同时支持旧的 Task 方式）

3. **测试**
   - [ ] 单元测试：Event/Message/MemoryEntry 创建和转换
   - [ ] 集成测试：BaseNode 发布 Event

**验收标准**：
- ✓ Event/Message/MemoryEntry 类创建完成
- ✓ BaseNode 可以发布 Event
- ✓ 所有现有测试通过

### 4.3 阶段 2：EventBus 重构（P0）

**目标**：EventBus 不修改 Task.status，支持 Event 路由，移除长期存储

**任务清单**：

1. **修改 EventBus 核心逻辑**
   - [ ] 修改 `publish()` 方法，不修改 Task.status
   - [ ] 添加 `publish_event()` 方法，支持 Event 路由
   - [ ] 添加 `register_event_handler()` 方法
   - [ ] 执行所有匹配的 handler（不只是第一个）

2. **移除长期存储**
   - [ ] 将 `_event_history` 改为 `deque(maxlen=100)`
   - [ ] 移除复杂的索引（`_events_by_node`, `_events_by_action` 等）
   - [ ] 保留简单的 `query_recent()` 方法（用于调试）

3. **向后兼容**
   - [ ] 保留旧的 `publish()` 接口（标记为 deprecated）
   - [ ] 添加迁移指南

4. **测试**
   - [ ] 单元测试：publish_task 不修改 status
   - [ ] 单元测试：publish_event 执行所有 handler
   - [ ] 集成测试：EventBus + BaseNode

**验收标准**：
- ✓ Handler 返回的 status 不被覆盖
- ✓ Event 可以被多个 handler 处理
- ✓ EventBus 不长期存储事件
- ✓ 所有现有测试通过

### 4.4 阶段 3：Memory 重构（P1）

**目标**：Memory 存储 MemoryEntry，订阅 EventBus

**任务清单**：

1. **修改存储结构**
   - [ ] L1/L2 存储 MemoryEntry 而不是 Task
   - [ ] 添加 `add_entry()` 方法
   - [ ] 保留 `add_task()` 方法（转换为 MemoryEntry）

2. **订阅 EventBus**
   - [ ] Memory 订阅 EventBus 的 Event
   - [ ] 选择性存储重要事件（thinking, tool_call）
   - [ ] 自动转换 Event → MemoryEntry

3. **更新查询接口**
   - [ ] 修改 `get_l1_tasks()` → `get_l1_entries()`
   - [ ] 修改 `get_l2_tasks()` → `get_l2_entries()`
   - [ ] 保持向后兼容（提供适配器）

4. **测试**
   - [ ] 单元测试：MemoryEntry 存储和查询
   - [ ] 单元测试：Event → MemoryEntry 转换
   - [ ] 集成测试：Memory + EventBus

**验收标准**：
- ✓ Memory 存储 MemoryEntry
- ✓ Memory 可以订阅 EventBus
- ✓ 事件自动转换为记忆条目
- ✓ 所有现有测试通过

### 4.5 阶段 4：Context 重构（P1）

**目标**：简化 TaskContextManager，使用 ContextSource 抽象

**任务清单**：

1. **创建 ContextSource 抽象**
   - [ ] 定义 `ContextSource` 接口
   - [ ] 实现 `MemoryContextSource`
   - [ ] 实现 `KnowledgeBaseContextSource`

2. **简化 ContextBuilder**
   - [ ] 重构 `build_context()` 方法（从 149 行简化到 50 行）
   - [ ] 使用 ContextSource 抽象
   - [ ] 移除直接依赖 EventBus

3. **测试**
   - [ ] 单元测试：ContextSource 实现
   - [ ] 单元测试：ContextBuilder
   - [ ] 集成测试：完整上下文构建流程

**验收标准**：
- ✓ ContextBuilder 代码行数减少 70%
- ✓ 通过 ContextSource 抽象查询
- ✓ 所有现有测试通过

### 4.6 阶段 5：清理和优化（持续）

**任务清单**：

1. **移除废弃代码**
   - [ ] 移除旧的 `publish()` 接口
   - [ ] 移除 EventBus 的复杂索引
   - [ ] 清理向后兼容代码

2. **文档更新**
   - [ ] 更新 `docs/framework/event-bus.md`
   - [ ] 更新 `docs/features/memory-system.md`
   - [ ] 更新 `AGENTS.md`

3. **性能优化**
   - [ ] 优化 MemoryEntry 查询
   - [ ] 优化 Context 构建性能
   - [ ] 添加性能测试

---

## 第五部分：总结与建议

### 5.1 核心洞察

从整体视角分析 EventBus、Context、Memory、Task 四大系统，我发现了**3 个根本性的架构问题**：

1. **数据结构过载**：Task 被用作"万能数据结构"，承担了工作单元、事件通知、消息传递、记忆存储、上下文输入等多重职责
2. **职责边界模糊**：EventBus 既是传输层又是存储层，Memory 既存储工作记忆又存储事件记忆
3. **集成层过度复杂**：TaskContextManager 直接集成多个系统，缺少清晰的抽象层

这些问题不是孤立的 bug，而是**系统性的架构缺陷**，导致：
- 语义混乱和状态失真
- 数据冗余和同步问题
- 代码复杂度爆炸（TaskContextManager 941 行）
- 难以维护和测试

### 5.2 解决方案

**整体重构方案**基于三个核心原则：

1. **数据结构分离**：Task/Event/Message/MemoryEntry 各司其职
2. **职责分离**：传输层（EventBus）与存储层（Memory）解耦
3. **抽象分层**：通过 ContextSource 抽象实现清晰的接口边界

**关键改进**：
- EventBus 不修改 Task.status，由 handler 决定
- EventBus 不长期存储，只保留最近 100 条用于调试
- Memory 存储 MemoryEntry，订阅 EventBus 选择性存储
- ContextBuilder 简化，通过 ContextSource 抽象查询

### 5.3 预期收益

- ✓ **正确性**：状态语义正确，Handler 返回值不被覆盖
- ✓ **可扩展性**：支持多订阅者、观察者模式
- ✓ **可维护性**：清晰的职责边界，代码行数减少 70%
- ✓ **可测试性**：通过抽象接口，易于单元测试
- ✓ **性能**：消除数据冗余，优化查询逻辑

### 5.4 实施建议

**渐进式重构**：
- 阶段 1（2-3周）：数据结构分离
- 阶段 2（2-3周）：EventBus 重构
- 阶段 3（2-3周）：Memory 重构
- 阶段 4（1-2周）：Context 重构
- 阶段 5（持续）：清理和优化

**向后兼容**：
- 保留旧接口（标记为 deprecated）
- 提供迁移指南
- 逐步迁移现有代码

### 5.5 关键文件索引

**分析文档**：
- `docs/refactoring/holistic-system-analysis.md` - 本文档（整体分析）
- `docs/refactoring/event-bus-first-principles-analysis.md` - EventBus 第一性原理分析
- `docs/refactoring/event-bus-issues-and-plan.md` - EventBus 问题清单

**核心实现文件**：
- `loom/events/event_bus.py` - EventBus 实现
- `loom/memory/core.py` - Memory 实现
- `loom/memory/task_context.py` - TaskContextManager 实现
- `loom/orchestration/base_node.py` - BaseNode 实现
- `loom/protocol/task.py` - Task 定义

---

**文档版本**: v1.0
**创建日期**: 2026-01-29
**作者**: Claude Code
**状态**: 待审核

