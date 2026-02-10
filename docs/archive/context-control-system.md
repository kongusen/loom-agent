# 上下文控制系统设计

## 1. 核心问题

### 1.1 时间复杂度问题

在多agent交互系统中，随着交互次数增加：
- 每次都传递完整历史 → O(n) 复杂度
- 上下文越来越大 → LLM成本和延迟线性增长
- 最终导致系统不可用

### 1.2 解决方案

通过 **Task存储 + Memory分层 + Context控制** 实现：
- 信息压缩：不传递所有历史，只传递相关摘要
- 任务聚焦：只传递与当前任务相关的信息
- 渐进遗忘：L1→L2→L3→L4 信息逐渐压缩和抽象
- 按需检索：节点根据需要从Memory检索

**时间复杂度优化**：O(n) → O(log n) 或 O(1)

## 2. 系统架构

### 2.1 核心组件

```
┌─────────────────────────────────────────────────────────┐
│                    用户输入/Agent交互                      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  Task 创建     │  ← 内容载体
              └───────┬───────┘
                      │
                      ▼
         ┌────────────────────────┐
         │  Context Builder       │  ← 上下文控制
         │  - 从Memory检索相关历史  │
         │  - 应用过滤策略         │
         │  - 构建ExecutionContext │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  Agent/Paradigm    │  ← 执行
         │  执行任务           │
         └────────┬───────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  Memory 更新        │  ← 记忆分层
         │  - Task存入L1       │
         │  - L1→L2→L3→L4压缩  │
         └────────────────────┘
```

### 2.2 信息流动

1. **产生内容**：用户输入或工具调用产生内容
2. **Task封装**：内容封装为Task对象
3. **Context构建**：从Memory检索相关历史，构建ExecutionContext
4. **节点执行**：节点接收ExecutionContext（而非完整历史）
5. **Memory更新**：执行结果存入Memory，触发分层压缩

## 3. Task增强设计

### 3.1 新增字段

```python
@dataclass
class Task:
    # ... 现有字段 ...

    # 新增字段
    metadata: dict[str, Any] = field(default_factory=dict)
    """
    元数据，用于存储：
    - importance: 重要性评分 (0.0-1.0)
    - summary: 任务摘要
    - context_refs: 上下文引用（而非完整复制）
    - tags: 标签（用于分类和检索）
    """

    parent_task_id: str | None = None
    """父任务ID（分形架构）"""
```

### 3.2 设计原则

- **轻量传递**：Task本身保持轻量，大数据通过引用
- **可追溯**：通过parent_task_id形成任务树
- **可检索**：通过metadata支持语义检索

## 4. Memory分层存储策略

### 4.1 四层设计

| 层级 | 存储内容 | 容量 | 压缩策略 | 用途 |
|------|---------|------|---------|------|
| L1 | 完整Task对象 | 50个 | 循环缓冲区 | 最近活动 |
| L2 | 重要Task对象 | 100个 | 按重要性过滤 | 当前工作记忆 |
| L3 | Task摘要 | 500个 | 生成摘要 | 会话历史 |
| L4 | 知识向量 | 无限 | 向量化 | 全局知识库 |

### 4.2 存储结构

```python
class LoomMemory:
    # L1: 完整Task（循环缓冲区）
    _l1_tasks: deque[Task]  # maxlen=50

    # L2: 重要Task（按重要性排序）
    _l2_tasks: list[Task]  # 按importance排序

    # L3: Task摘要
    _l3_summaries: list[TaskSummary]

    # L4: 向量存储
    _l4_vector_store: VectorStore
```

### 4.3 压缩策略

#### L1 → L2: 重要性过滤

```python
def promote_l1_to_l2(self, task: Task) -> bool:
    """
    判断L1中的Task是否应该提升到L2

    重要性评分标准：
    - 用户直接交互: 0.9
    - 工具调用成功: 0.7
    - 工具调用失败: 0.8 (失败更重要，需要记住)
    - 子任务: 0.5
    """
    importance = task.metadata.get("importance", 0.5)

    # 如果L2未满，直接添加
    if len(self._l2_tasks) < self.max_l2_size:
        return importance > 0.6

    # 如果L2已满，只保留最重要的
    min_importance = min(t.metadata.get("importance", 0.5) for t in self._l2_tasks)
    return importance > min_importance
```

#### L2 → L3: 生成摘要

```python
def promote_l2_to_l3(self, task: Task) -> TaskSummary:
    """
    将L2的Task压缩为摘要

    摘要包含：
    - task_id, action
    - 参数摘要（而非完整参数）
    - 结果摘要（而非完整结果）
    - 关键标签
    """
    return TaskSummary(
        task_id=task.task_id,
        action=task.action,
        param_summary=self._summarize_params(task.parameters),
        result_summary=self._summarize_result(task.result),
        tags=task.metadata.get("tags", []),
        importance=task.metadata.get("importance", 0.5)
    )
```

#### L3 → L4: 向量化

```python
def promote_l3_to_l4(self, summary: TaskSummary) -> None:
    """
    将L3摘要向量化存入L4

    向量化内容：
    - action + param_summary + result_summary
    - 支持语义检索
    """
    text = f"{summary.action}: {summary.param_summary} -> {summary.result_summary}"
    vector = self._embedding_provider.embed(text)

    self._l4_vector_store.add(
        id=summary.task_id,
        vector=vector,
        metadata={
            "action": summary.action,
            "tags": summary.tags,
            "importance": summary.importance
        }
    )
```

## 5. Context控制机制

### 5.1 核心思想

**不传递完整历史，而是传递相关上下文**

```python
# ❌ 错误做法：传递所有历史
context = {
    "all_history": [task1, task2, ..., task_n]  # O(n)
}

# ✅ 正确做法：传递相关上下文
context = {
    "recent_tasks": memory.get_l1(limit=5),      # 最近5个
    "working_tasks": memory.get_l2(),            # 当前工作相关
    "relevant_tasks": memory.search_l4(query)    # 语义相关
}  # O(1) 或 O(log n)
```

### 5.2 Context构建策略

```python
class ContextBuilder:
    def build_context(
        self,
        current_task: Task,
        memory: LoomMemory,
        strategy: str = "balanced"
    ) -> ExecutionContext:
        """
        构建执行上下文

        策略：
        - minimal: 只包含当前任务（最快）
        - balanced: 包含最近+相关（默认）
        - comprehensive: 包含更多历史（最全）
        """
        if strategy == "minimal":
            return ExecutionContext(
                current_task=current_task,
                task_history=[],
                memory=memory
            )

        elif strategy == "balanced":
            # 1. 最近的5个Task（L1）
            recent = memory.get_l1_tasks(limit=5)

            # 2. 当前工作相关的Task（L2）
            working = memory.get_l2_tasks()

            # 3. 语义相关的Task（L4检索）
            relevant = memory.search_tasks(
                query=current_task.action,
                limit=3
            )

            # 4. 去重合并
            task_history = self._deduplicate([recent, working, relevant])

            return ExecutionContext(
                current_task=current_task,
                task_history=task_history,
                memory=memory
            )
```

### 5.3 时间复杂度分析

| 操作 | 无Context控制 | 有Context控制 | 优化效果 |
|------|--------------|--------------|---------|
| 获取历史 | O(n) | O(1) | n倍 |
| 传递数据 | O(n) | O(k), k<<n | n/k倍 |
| LLM处理 | O(n²) | O(k²) | (n/k)²倍 |

**示例**：100次交互后
- 无控制：传递100个Task，LLM处理~10000个token
- 有控制：传递10个Task，LLM处理~1000个token
- **优化：10倍速度提升，10倍成本降低**

## 6. 实现计划

### 6.1 第一阶段：Task增强

**文件**：`loom/protocol/task.py`

**改动**：
```python
@dataclass
class Task:
    # 现有字段保持不变
    task_id: str
    source_agent: str
    target_agent: str
    action: str
    parameters: dict[str, Any]
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    result: Any
    error: str | None

    # 新增字段
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_task_id: str | None = None
```

**元数据标准字段**：
- `importance`: float (0.0-1.0) - 重要性评分
- `summary`: str - 任务摘要
- `tags`: list[str] - 标签
- `context_strategy`: str - 上下文策略（minimal/balanced/comprehensive）

### 6.2 第二阶段：Memory重构

**文件**：`loom/memory/core.py`

**核心改动**：将Memory从存储MemoryUnit改为存储Task

```python
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loom.runtime import Task

class LoomMemory:
    """
    基于Task的分层记忆系统

    L1: 完整Task对象（循环缓冲区，最近50个）
    L2: 重要Task对象（按重要性排序，最多100个）
    L3: Task摘要（最多500个）
    L4: 向量存储（无限）
    """

    def __init__(
        self,
        node_id: str,
        max_l1_size: int = 50,
        max_l2_size: int = 100,
        max_l3_size: int = 500
    ):
        self.node_id = node_id

        # L1: 循环缓冲区
        self._l1_tasks: deque[Task] = deque(maxlen=max_l1_size)

        # L2: 重要Task列表
        self._l2_tasks: list[Task] = []
        self.max_l2_size = max_l2_size

        # L3: Task摘要
        self._l3_summaries: list[TaskSummary] = []
        self.max_l3_size = max_l3_size

        # L4: 向量存储（可选）
        self._l4_vector_store: VectorStore | None = None
```

**核心方法**：
```python
def add_task(self, task: Task, tier: MemoryTier = MemoryTier.L1) -> None:
    """添加Task到指定层级"""

def get_l1_tasks(self, limit: int = 10) -> list[Task]:
    """获取L1最近的Task"""

def get_l2_tasks(self) -> list[Task]:
    """获取L2工作记忆Task"""

def search_tasks(self, query: str, limit: int = 5) -> list[Task]:
    """从L4语义检索相关Task"""

def promote_tasks(self) -> None:
    """触发L1→L2→L3→L4的压缩提升"""
```

### 6.3 第三阶段：ExecutionContext更新

**文件**：`loom/paradigms/execution_context.py`

**改动**：
```python
@dataclass
class ExecutionContext:
    """
    执行上下文

    基于Task的上下文控制机制
    """
    # 当前任务
    current_task: "Task | None" = None

    # 任务历史（从Memory检索的相关Task）
    task_history: list["Task"] = field(default_factory=list)

    # 记忆系统引用
    memory: "LoomMemory | None" = None

    # 会话ID
    session_id: str = "default"

    # Agent能力声明
    agent_card: "AgentCard | None" = None

    # 父节点上下文（分形架构）
    parent_context: dict[str, Any] | None = None

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)
```

**关键变化**：
- 添加 `current_task` 字段（当前正在执行的任务）
- `task_history` 现在存储完整的Task对象（而非MemoryUnit）
- 移除 `working_memory` 字段（统一使用task_history）

### 6.4 第四阶段：ContextBuilder更新

**文件**：`loom/paradigms/context_builder.py`

**核心改动**：实现智能的上下文构建策略

```python
class ContextBuilder:
    def __init__(self):
        self._memory: "LoomMemory | None" = None
        self._session_id: str = "default"
        self._agent_card: "AgentCard | None" = None
        self._parent_context: dict[str, Any] | None = None
        self._current_task: "Task | None" = None
        self._strategy: str = "balanced"
        self._metadata: dict[str, Any] = {}

    def with_current_task(self, task: "Task") -> "ContextBuilder":
        """设置当前任务"""
        self._current_task = task
        return self

    def with_strategy(self, strategy: str) -> "ContextBuilder":
        """设置上下文策略（minimal/balanced/comprehensive）"""
        self._strategy = strategy
        return self

    def build(self) -> ExecutionContext:
        """
        构建ExecutionContext

        根据策略从Memory检索相关Task历史
        """
        task_history = []

        if self._memory and self._current_task:
            if self._strategy == "minimal":
                # 不包含历史
                task_history = []

            elif self._strategy == "balanced":
                # 最近5个 + 工作记忆 + 语义相关3个
                recent = self._memory.get_l1_tasks(limit=5)
                working = self._memory.get_l2_tasks()
                relevant = self._memory.search_tasks(
                    query=self._current_task.action,
                    limit=3
                )
                task_history = self._deduplicate([recent, working, relevant])

            elif self._strategy == "comprehensive":
                # 更多历史
                recent = self._memory.get_l1_tasks(limit=10)
                working = self._memory.get_l2_tasks()
                relevant = self._memory.search_tasks(
                    query=self._current_task.action,
                    limit=5
                )
                task_history = self._deduplicate([recent, working, relevant])

        return ExecutionContext(
            current_task=self._current_task,
            task_history=task_history,
            memory=self._memory,
            session_id=self._session_id,
            agent_card=self._agent_card,
            parent_context=self._parent_context,
            metadata=self._metadata
        )
```

### 6.5 第五阶段：Paradigm更新

**文件**：`loom/paradigms/tool_use.py`, `loom/paradigms/multi_agent.py`

**核心改动**：Paradigm执行时自动记录Task到Memory

```python
class ToolUseParadigm:
    async def execute(self, task: Task, context: dict[str, Any]) -> Task:
        """
        执行工具调用

        自动记录：
        1. 将当前task存入Memory L1
        2. 根据重要性可能提升到L2
        3. 执行完成后触发Memory压缩
        """
        exec_context = ExecutionContext.from_dict(context)

        # 1. 记录当前Task到Memory
        if exec_context.memory:
            # 设置重要性
            task.metadata["importance"] = self._calculate_importance(task)
            # 存入L1
            exec_context.memory.add_task(task, tier=MemoryTier.L1)

        # 2. 执行工具
        tool_name = task.parameters.get("tool")
        result = await self._execute_tool(tool_name, task.parameters)

        # 3. 更新Task结果
        task.result = result
        task.status = TaskStatus.COMPLETED

        # 4. 触发Memory压缩（异步）
        if exec_context.memory:
            exec_context.memory.promote_tasks()

        return task
```

**重要性计算**：
```python
def _calculate_importance(self, task: Task) -> float:
    """
    计算Task重要性

    规则：
    - 用户直接交互: 0.9
    - 工具调用成功: 0.7
    - 工具调用失败: 0.8
    - 子任务: 0.5
    """
    if task.source_agent == "user":
        return 0.9
    elif task.status == TaskStatus.FAILED:
        return 0.8
    elif task.status == TaskStatus.COMPLETED:
        return 0.7
    else:
        return 0.5
```

## 7. 总结

### 7.1 核心优势

1. **时间复杂度优化**：O(n) → O(1) 或 O(log n)
2. **成本降低**：只传递相关上下文，LLM成本降低10倍
3. **可扩展性**：支持长时间运行的agent系统
4. **符合公理**：完全基于Task（A2）和Memory分层（A4）

### 7.2 设计原则

- **Task为核心**：所有内容通过Task传递
- **Memory分层**：L1-L4渐进压缩
- **Context控制**：智能选择相关历史
- **按需检索**：节点需要时从Memory检索

### 7.3 实现顺序

1. ✅ 设计文档完成
2. ⏳ Task增强（添加metadata和parent_task_id）
3. ⏳ Memory重构（支持Task存储和分层压缩）
4. ⏳ ExecutionContext更新（添加current_task）
5. ⏳ ContextBuilder更新（实现策略）
6. ⏳ Paradigm更新（自动记录Task）
7. ⏳ 测试验证

### 7.4 关键文件

- `loom/protocol/task.py` - Task定义
- `loom/memory/core.py` - Memory系统
- `loom/paradigms/execution_context.py` - 执行上下文
- `loom/paradigms/context_builder.py` - 上下文构建器
- `loom/paradigms/tool_use.py` - 工具使用范式
- `loom/paradigms/multi_agent.py` - 多Agent范式

