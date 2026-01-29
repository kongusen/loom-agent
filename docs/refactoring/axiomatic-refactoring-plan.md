# 基于公理系统的重构方案

**作者**: Claude Code
**日期**: 2026-01-29
**目的**: 基于 loom-agent 公理系统，重新设计 EventBus、Memory、Context 的架构

---

## 第一部分：公理系统回顾

### 核心公理

#### A2: 事件主权公理（Event Sovereignty）
> **所有通信都是 Task**

**含义**：
- Task 是系统中唯一的通信单元
- 不同类型的通信通过 `Task.action` 区分
- 所有节点间的交互都通过 Task 进行

**推论**：
- ✓ 工作委派 → Task(action="execute")
- ✓ 节点观测 → Task(action="node.thinking")
- ✓ 点对点消息 → Task(action="node.message")
- ✗ 不应该创建 Event、Message 等其他数据结构

#### A4: 记忆层次公理（Memory Hierarchy）
> **Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4**

**含义**：
- L1: 原始 I/O（最近的完整 Task，1小时，10条）
- L2: 工作记忆（重要的 Task，24小时，50条）
- L3: 情景记忆（Task 摘要，7天，200条）
- L4: 语义记忆（向量化，永久，压缩）

**推论**：
- ✓ L1 存储完整 Task
- ✓ L2 存储重要的完整 Task
- ✓ L3 存储 TaskSummary（压缩）
- ✓ L4 存储向量（最大压缩）
- ✗ 不应该在 L1/L2 之外存储完整 Task

---

## 第二部分：当前架构违反公理的地方

### 违反 1：EventBus 修改 Task（违反 A2）

**问题代码**：
```python
# event_bus.py:114
task.status = TaskStatus.RUNNING

# event_bus.py:148
result_task.status = TaskStatus.COMPLETED
```

**违反原因**：
- A2 公理：Task 是通信单元
- EventBus 是传输层，不应该修改通信内容
- 类比：邮局不应该打开信件修改内容

**影响**：
- Handler 返回的 status 被强制覆盖
- Task 的状态语义失真
- 违反了 A2A 协议

### 违反 2：EventBus 长期存储 Task（违反职责分离）

**问题代码**：
```python
# event_bus.py:55
self._event_history: list[Task] = []  # 无限增长

# event_bus.py:167
self._event_history.append(task)  # 每个 Task 都存储

# event_bus.py:57-68 - 复杂索引
self._events_by_node: dict[str, list[Task]] = defaultdict(list)
self._events_by_action: dict[str, list[Task]] = defaultdict(list)
self._events_by_task: dict[str, list[Task]] = defaultdict(list)
```

**违反原因**：
- EventBus 是传输层，应该专注于路由和分发
- 长期存储应该由 Memory 负责（A4 公理）
- 类比：快递公司不应该长期保存包裹

**影响**：
- EventBus 和 Memory 都存储 Task（数据冗余）
- EventBus 的 _event_history 与 Memory 的 L1 功能重叠
- 职责不清：应该查 EventBus 还是 Memory？

### 违反 3：Memory 没有遵循 A4 的压缩原则

**问题代码**：
```python
# memory/core.py:120 - L1 存储完整 Task
self._l1_layer._buffer.append(task)

# memory/core.py:186 - L2 也存储完整 Task
heapq.heappush(self._l2_layer._heap, priority_item)

# memory/core.py:525 - L3 存储 TaskSummary（正确）
self._l3_summaries.append(summary)
```

**问题分析**：
- ✓ L1 存储完整 Task（符合 A4）
- ✓ L2 存储完整 Task（符合 A4）
- ✓ L3 存储 TaskSummary（符合 A4）
- ✗ 但是 L1 和 L2 都存储完整 Task，没有区分

**实际上这个不是违反**，而是实现细节。L1 和 L2 都可以存储完整 Task，区别在于：
- L1: 最近的所有 Task（时间维度）
- L2: 重要的 Task（重要性维度）

### 违反 4：TaskContextManager 直接查询 EventBus（违反分层）

**问题代码**：
```python
# task_context.py:787 - 直接查询 EventBus
direct_events = event_bus.query_by_target(target_agent=self.node_id, ...)

# task_context.py:806 - 直接查询 EventBus
candidates.extend(event_bus.query_by_task(current_task.task_id))
candidates.extend(event_bus.query_recent(limit=50))
```

**违反原因**：
- Context 应该从 Memory 获取数据（A4 公理）
- EventBus 是传输层，不应该被用作数据源
- 类比：应用层不应该直接查询网络层

**影响**：
- Context 依赖 EventBus 的存储功能
- 如果 EventBus 不存储，Context 就失效
- 职责混乱

---

## 第三部分：基于公理的正确架构

### 3.1 核心原则

基于公理系统，正确的架构应该遵循：

#### 原则 1：Task 是唯一的通信单元（A2 公理）

```python
# 所有节点间通信都使用 Task
# 通过 Task.action 区分不同类型

# 工作委派
Task(action="execute", target_agent="worker", ...)

# 节点观测
Task(action="node.thinking", target_agent="observer", ...)

# 点对点消息
Task(action="node.message", target_agent="node-b", ...)

# 不创建其他数据结构（Event, Message 等）
```

#### 原则 2：EventBus 是纯粹的传输层

```python
class EventBus:
    """
    传输层 - 只负责路由和分发

    职责：
    - 路由 Task 到正确的 handler
    - 不修改 Task 的任何字段
    - 不长期存储 Task
    """

    async def publish(self, task: Task, wait_result: bool = True) -> Task:
        """发布 Task（不修改任何字段）"""
        handlers = self._handlers.get(task.action, [])

        if not handlers:
            # 不修改 status，直接返回
            return task

        if wait_result:
            # 执行 handler，返回 handler 的结果
            result_task = await handlers[0](task)
            return result_task  # 保留 handler 返回的 status
        else:
            # Fire-and-forget
            asyncio.create_task(handlers[0](task))
            return task  # 返回原始 task
```

**关键改变**：
- ✗ 移除 `task.status = TaskStatus.RUNNING`
- ✗ 移除 `result_task.status = TaskStatus.COMPLETED`
- ✓ 完全不修改 Task，由 handler 决定状态

#### 原则 3：Memory 是唯一的存储层（A4 公理）

```python
class LoomMemory:
    """
    存储层 - 负责 Task 的持久化和查询

    职责：
    - 订阅 EventBus，接收所有 Task
    - 选择性存储到 L1/L2/L3/L4
    - 提供查询接口
    """

    def __init__(self, node_id: str, event_bus: EventBus):
        self.node_id = node_id
        self._l1_tasks: deque[Task] = deque(maxlen=50)
        self._l2_tasks: list[Task] = []
        # ... L3/L4

        # 订阅 EventBus（关键！）
        event_bus.register_handler("*", self._on_task)  # 订阅所有 Task

    async def _on_task(self, task: Task) -> Task:
        """接收所有 Task，选择性存储"""
        # 1. 添加到 L1（最近的所有 Task）
        self._l1_tasks.append(task)

        # 2. 根据重要性决定是否添加到 L2
        importance = task.metadata.get("importance", 0.5)
        if importance > 0.6:
            self._l2_tasks.append(task)

        # 3. 返回原始 task（不修改）
        return task
```

**关键改变**：
- ✓ Memory 订阅 EventBus，自动接收所有 Task
- ✓ Memory 负责存储决策（哪些 Task 存储到哪一层）
- ✗ EventBus 不再有 _event_history

### 3.2 数据流详解

#### 场景 1：节点间工作委派

```
Node A (发起者)
  ↓ 创建 Task(action="execute", target_agent="node-b")
  ↓
EventBus (传输层)
  ↓ 路由到 Node B 的 handler
  ↓
Node B (执行者)
  ↓ handler 执行任务
  ↓ 返回 Task(status=COMPLETED, result=...)
  ↓
EventBus (传输层)
  ↓ 返回给 Node A
  ↓
Node A (接收结果)

同时：
EventBus → Memory (订阅者)
  ↓ Memory 接收所有 Task
  ↓ 存储到 L1/L2
```

**关键点**：
- EventBus 只负责路由，不修改 Task
- Memory 作为订阅者，自动接收所有 Task
- Node B 的 handler 决定 Task.status

#### 场景 2：节点观测（Thinking）

```
Node A (思考中)
  ↓ 创建 Task(action="node.thinking", target_agent="observer")
  ↓
EventBus (传输层)
  ↓ 路由到所有订阅 "node.thinking" 的 handler
  ↓
Memory (订阅者)
  ↓ 接收 Task，存储到 L1
  ↓
其他观察者 (可选)
  ↓ 接收 Task，做自己的处理
```

**关键点**：
- 观测 Task 没有特定的 target_agent（或 target_agent="observer"）
- 可以有多个订阅者（Memory、监控系统等）
- 没有 handler 不会被标记为 FAILED

#### 场景 3：点对点消息

```
Node A (发送者)
  ↓ 创建 Task(action="node.message", target_agent="node-b", parameters={"content": "..."})
  ↓
EventBus (传输层)
  ↓ 路由到 Node B 的 handler
  ↓
Node B (接收者)
  ↓ handler 处理消息
  ↓ 可选：返回响应 Task
  ↓
EventBus (传输层)
  ↓ 返回给 Node A（如果有响应）

同时：
EventBus → Memory (订阅者)
  ↓ Memory 接收消息 Task
  ↓ 根据重要性决定是否存储
```

**关键点**：
- 点对点消息也是 Task，通过 action="node.message" 区分
- 可以选择是否等待响应（wait_result）
- Memory 可以选择性存储（不是所有消息都重要）

### 3.3 Context、Memory、Session 的工作机制

#### Context 的构建流程

```python
class ContextBuilder:
    """
    上下文构建器 - 从 Memory 获取数据

    职责：
    - 查询 Memory 的 L1/L2/L3/L4
    - 排序和筛选
    - 转换为 LLM 消息
    """

    def __init__(self, memory: LoomMemory, token_counter: TokenCounter):
        self.memory = memory
        self.token_counter = token_counter

    async def build_context(self, current_task: Task) -> list[dict[str, str]]:
        """构建上下文（只从 Memory 获取）"""
        # 1. 从 Memory 获取相关 Task
        l1_tasks = self.memory.get_l1_tasks(limit=10)
        l2_tasks = self.memory.get_l2_tasks(limit=10)
        l3_summaries = self.memory.get_l3_summaries(limit=5)

        # 2. 按 session_id 过滤（如果有）
        if current_task.session_id:
            l1_tasks = [t for t in l1_tasks if t.session_id == current_task.session_id]
            l2_tasks = [t for t in l2_tasks if t.session_id == current_task.session_id]

        # 3. 转换为 LLM 消息
        messages = []
        for task in l1_tasks + l2_tasks:
            msg = self._task_to_message(task)
            if msg:
                messages.append(msg)

        # 4. Token 预算控制
        return self._trim_to_budget(messages, max_tokens=4000)

    def _task_to_message(self, task: Task) -> dict[str, str] | None:
        """将 Task 转换为 LLM 消息"""
        if task.action == "node.thinking":
            return {"role": "assistant", "content": task.parameters.get("content", "")}
        elif task.action == "execute":
            return {"role": "user", "content": task.parameters.get("content", "")}
        # ... 其他转换规则
        return None
```

**关键点**：
- ✓ Context 只从 Memory 获取数据（不查询 EventBus）
- ✓ 通过 session_id 过滤，实现 Session 隔离
- ✓ 简化的查询逻辑（不需要复杂的排序和筛选）

#### Memory 的分层存储

```
L1 (最近的所有 Task)
  ↓ 时间维度：最近 1 小时，最多 50 条
  ↓ 存储：完整 Task 对象
  ↓ 用途：短期工作记忆

L2 (重要的 Task)
  ↓ 重要性维度：importance > 0.6
  ↓ 存储：完整 Task 对象
  ↓ 用途：长期工作记忆

L3 (Task 摘要)
  ↓ 压缩：TaskSummary（200 字符）
  ↓ 存储：最多 500 条
  ↓ 用途：情景记忆

L4 (向量化)
  ↓ 压缩：向量表示
  ↓ 存储：永久
  ↓ 用途：语义检索
```

**关键点**：
- ✓ L1/L2 存储完整 Task（符合 A4 公理）
- ✓ L3/L4 压缩存储（符合 A4 公理）
- ✓ 自动晋升：L1 → L2 → L3 → L4

#### Session 的实现机制

```python
# Session 通过 Task.session_id 实现

# 创建 Task 时指定 session_id
task = Task(
    task_id="task-1",
    session_id="session-abc",  # 关键字段
    action="execute",
    ...
)

# Memory 存储时保留 session_id
memory.add_task(task)  # task.session_id 被保留

# Context 构建时按 session_id 过滤
context_tasks = memory.get_l1_tasks()
context_tasks = [t for t in context_tasks if t.session_id == current_session_id]
```

**关键点**：
- ✓ Session 是 Task 的一个字段，不是独立的数据结构
- ✓ 所有 Task 都携带 session_id
- ✓ Context 构建时按 session_id 过滤，实现会话隔离

### 3.4 传输层与通信机制

#### EventBus 的传输抽象

```python
# EventBus 支持可插拔的传输层
class EventBus:
    def __init__(self, transport: Transport | None = None):
        self._transport = transport  # 可选的传输层

# 本地模式（无 transport）
event_bus = EventBus()  # 直接调用 handler

# 分布式模式（有 transport）
event_bus = EventBus(transport=NATSTransport())  # 通过 NATS 传输
event_bus = EventBus(transport=RedisTransport())  # 通过 Redis 传输
```

**关键点**：
- EventBus 抽象了传输层
- 本地模式：直接调用 handler（内存）
- 分布式模式：通过 transport 发送（NATS/Redis/etc）

#### 关于 SSE（Server-Sent Events）

**当前状态**：
- loom-agent 框架**不使用 SSE**
- EventBus 使用的是 **pub-sub 模式**（NATS/Redis）
- SSE 是 HTTP 协议的单向流，不适合 Agent 间通信

**为什么不用 SSE？**
1. SSE 是单向的（服务器 → 客户端），不支持双向通信
2. Agent 间通信需要双向的 request-response
3. NATS/Redis 提供了更强大的 pub-sub 和 request-reply 模式

**可能的 SSE 使用场景**：
- 如果需要将 Agent 的输出流式传输给前端用户
- 这是**应用层**的需求，不是 EventBus 层的职责
- 可以在 Agent 上层添加 SSE 适配器

```python
# 假设的 SSE 适配器（应用层）
class SSEAdapter:
    """将 Agent 的输出流式传输给前端"""

    def __init__(self, agent: Agent, event_bus: EventBus):
        self.agent = agent
        # 订阅 Agent 的 thinking 事件
        event_bus.register_handler("node.thinking", self._on_thinking)

    async def _on_thinking(self, task: Task) -> Task:
        """将 thinking 事件转换为 SSE"""
        content = task.parameters.get("content", "")
        await self.send_sse_event({"type": "thinking", "content": content})
        return task
```

**总结**：
- ✗ EventBus 不使用 SSE
- ✓ EventBus 使用 pub-sub 模式（NATS/Redis）
- ✓ SSE 可以在应用层使用（如果需要流式输出给前端）

---

## 第四部分：实施计划（不向后兼容）

### 4.1 实施策略

**核心原则**：直接重构，不保持向后兼容

```text
阶段 1: EventBus 重构（1周）
  ↓
阶段 2: Memory 订阅机制（1周）
  ↓
阶段 3: Context 简化（1周）
  ↓
阶段 4: 测试和修复（1周）
```

### 4.2 阶段 1：EventBus 重构（P0）✅

**目标**：EventBus 不修改 Task.status，移除长期存储

**状态**：✅ 已完成

**任务清单**：

1. **修改 EventBus.publish()**
   - [x] 移除 `task.status = TaskStatus.RUNNING`（line 114）
   - [x] 移除 `result_task.status = TaskStatus.COMPLETED`（line 148）
   - [x] 移除 `task.status = TaskStatus.FAILED`（line 129）
   - [x] 保留 handler 返回的原始 Task

2. **移除长期存储**
   - [x] 移除 `_event_history`
   - [x] 移除所有索引（`_events_by_node`, `_events_by_action`, etc）
   - [x] 移除所有查询方法（`query_by_node`, `query_by_action`, etc）
   - [x] 可选：保留 `_recent_events: deque(maxlen=100)` 用于调试

3. **支持通配符订阅**
   - [x] 修改 `register_handler()` 支持 `"*"` 通配符
   - [x] 实现模式匹配逻辑

**验收标准**：

- ✅ Handler 返回的 status 不被覆盖
- ✅ EventBus 不长期存储 Task
- ✅ 支持 `register_handler("*", handler)` 订阅所有 Task

### 4.3 阶段 2：Memory 订阅机制（P0）✅

**目标**：Memory 订阅 EventBus，自动接收所有 Task

**状态**：✅ 已完成

**任务清单**：

1. **修改 LoomMemory 初始化**
   - [x] 添加 `event_bus` 参数
   - [x] 在 `__init__` 中订阅 EventBus
   - [x] 实现 `_on_task()` handler

2. **实现选择性存储逻辑**
   - [x] L1: 存储所有 Task（最近 50 条）
   - [x] L2: 存储重要 Task（importance > 0.6）
   - [x] L3: 自动压缩（L2 满时）
   - [x] L4: 自动向量化（L3 满时）

3. **移除手动添加接口**
   - [x] 保留 `add_task()` 方法（用于测试）
   - [x] 主要通过订阅自动添加

**验收标准**：

- ✅ Memory 自动接收所有 Task
- ✅ L1/L2/L3/L4 自动管理
- ✅ 不需要手动调用 `add_task()`

### 4.4 阶段 3：Context 简化（P1）✅

**目标**：Context 只从 Memory 获取数据，简化查询逻辑

**状态**：✅ 已完成

**任务清单**：

1. **修改 TaskContextManager**
   - [x] 移除 `EventBusContextSource`
   - [x] 移除直接查询 EventBus 的代码
   - [x] 只保留 `MemoryContextSource`

2. **简化 build_context()**
   - [x] 移除复杂的排序和筛选逻辑
   - [x] 简化为：查询 Memory → 过滤 session → 转换消息 → Token 控制
   - [x] 目标：从 149 行简化到 50 行

3. **移除 ContextBudgeter 的复杂逻辑**
   - [x] 简化 token 预算分配
   - [x] 移除 embedding 相关性计算（可选）
   - [x] 保留基本的 token 控制

**验收标准**：

- ✅ Context 只从 Memory 获取数据
- ✅ build_context() 代码行数减少 70%
- ✅ 所有测试通过

### 4.5 阶段 4：测试和修复（P1）✅

**目标**：确保所有功能正常工作

**状态**：✅ 已完成（2026-01-29）

**任务清单**：

1. **单元测试**
   - [x] EventBus 测试：不修改 status
   - [x] Memory 测试：订阅机制
   - [x] Context 测试：只从 Memory 获取

2. **集成测试**
   - [x] 节点间工作委派
   - [x] 节点观测（thinking）
   - [x] 点对点消息
   - [x] Session 隔离

3. **修复问题**
   - [x] 修复所有测试失败
   - [x] 修复性能问题
   - [x] 更新文档

**验收标准**：

- ✅ 所有单元测试通过（984/984）
- ✅ 所有集成测试通过（53/53，11 skipped）
- ✅ 文档更新完成

**完成总结**：

Phase 4 成功完成了所有测试和修复工作：

1. **修复的问题**：
   - 修复了 `agent.py` 中缺失的 `event_bus` 参数传递给 LoomMemory
   - 移除了 `EventBusContextSource` 的所有引用
   - 删除了 4 个过时的文件（test_queryable_event_bus.py, context_builder.py, test_context_builder.py, collective_unconscious_demo.py）
   - 更新了 `context_tools.py`，移除了 EventBus 查询工具
   - 移除了 9 个过时的 EventBus 查询工具测试

2. **测试结果**：
   - 单元测试：984 个测试全部通过
   - 集成测试：53 个测试通过，11 个跳过（需要 API keys）
   - 无测试失败

3. **关键改进**：
   - Context 现在只从 Memory 获取数据（符合 A4 公理）
   - Memory 通过订阅 EventBus 自动接收所有 Task（Phase 2 功能）
   - 所有代码符合公理系统要求

---

## 第五部分：总结

### 5.1 核心洞察

基于 loom-agent 的公理系统，我重新分析了 EventBus、Memory、Context 的架构问题：

**关键发现**：
- ✓ Task 作为唯一的通信单元是**正确的**（A2 公理）
- ✗ EventBus 修改 Task.status 是**错误的**（违反 A2）
- ✗ EventBus 长期存储 Task 是**错误的**（职责混乱）
- ✗ Context 直接查询 EventBus 是**错误的**（违反分层）

### 5.2 解决方案

**核心原则**：
1. Task 是唯一的通信单元（A2 公理）
2. EventBus 是纯粹的传输层（不修改、不存储）
3. Memory 是唯一的存储层（订阅 EventBus）
4. Context 只从 Memory 获取数据

**关键改进**：
- EventBus 不修改 Task.status
- EventBus 不长期存储（移除 _event_history）
- Memory 订阅 EventBus，自动接收所有 Task
- Context 简化，只从 Memory 获取数据

### 5.3 数据流

```text
Node A → EventBus → Node B (工作委派)
         ↓
       Memory (订阅者，自动存储)
         ↓
       Context (查询 Memory)
         ↓
       LLM (使用 Context)
```

### 5.4 预期收益

- ✓ **正确性**：Handler 返回的 status 不被覆盖
- ✓ **简洁性**：EventBus 代码减少 50%，Context 代码减少 70%
- ✓ **清晰性**：职责边界清晰（传输 vs 存储）
- ✓ **符合公理**：完全遵循 A2 和 A4 公理

---

**文档版本**: v2.0
**创建日期**: 2026-01-29
**最后更新**: 2026-01-29
**作者**: Claude Code
**状态**: ✅ Phase 4 已完成 - 所有测试通过

**重构进度**：
- ✅ Phase 1: EventBus 重构（已完成）
- ✅ Phase 2: Memory 订阅机制（已完成）
- ✅ Phase 3: Context 简化（已完成）
- ✅ Phase 4: 测试和修复（已完成）

**最终结果**：
- 984 个单元测试全部通过
- 53 个集成测试通过（11 个跳过）
- 所有代码符合公理系统（A2, A4）
- 架构清晰：EventBus（传输层）→ Memory（存储层）→ Context（查询层）
