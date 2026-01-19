# Loom系统优化分析 - 空间复杂度、递归机制与架构反思

> **分析日期**: 2026-01-18
> **分析范围**: 空间复杂度、递归机制、React机制、四大范式、架构封装

## 1. 概述

本文档对Loom框架进行系统性的优化分析，重点关注：
1. **空间复杂度处理** - 内存管理、数据累积、泄漏风险
2. **递归机制** - 递归深度控制、调用栈管理
3. **React机制** - 单节点反应式执行
4. **四大范式** - Reflection、ToolUse、Planning、MultiAgent
5. **架构反思** - 封装合理性、接口简洁性、自由度平衡

### 1.1 设计原则回顾

Loom框架基于公理化设计，核心原则包括：
- **A3（分形自相似）**: 节点结构与系统结构同构
- **A6（四范式工作）**: 每个agent具备四种基本能力
- **简洁性原则**: 分型结构内部非常简单
- **自由度原则**: 确保灵活性的同时保持接口简单

### 1.2 分析方法

本次分析采用以下方法：
1. **代码审查** - 系统性检查关键模块
2. **模式识别** - 识别潜在的反模式和风险点
3. **复杂度分析** - 评估时间和空间复杂度
4. **架构反思** - 审视封装合理性和接口设计

---

## 2. 空间复杂度问题分析

### 2.1 问题概览

| 问题类型 | 严重程度 | 影响范围 | 优先级 |
|---------|---------|---------|--------|
| Task索引无限增长 | 高 | Memory系统 | P0 |
| Fact索引无限增长 | 高 | Memory系统 | P0 |
| 并行执行深拷贝 | 高 | Orchestration | P0 |
| L2任务无限制加载 | 中 | Context构建 | P1 |
| 循环引用风险 | 中 | ExecutionContext | P1 |

### 2.2 问题详解

#### 问题1: Task索引的内存泄漏

**位置**: `loom/memory/core.py`

**问题代码**:
```python
class LoomMemory:
    def __init__(self, ...):
        self._task_index: dict[str, "Task"] = {}

    def add_task(self, task: "Task", tier: MemoryTier = MemoryTier.L1_RAW_IO) -> None:
        # 添加到索引
        self._task_index[task.task_id] = task
        # 但删除时可能不会清理索引
```

**问题描述**:
- Task被添加到`_task_index`但永不删除
- 即使Task从L1、L2、L3中移除，索引中仍保留引用
- 导致Task对象无法被垃圾回收

**泄漏场景**:
```
1. 添加Task到L1 → 添加到_task_index
2. Task从L1循环缓冲区溢出 → 从L1移除
3. Task从L2移除 → 从L2移除
4. Task从L3移除 → 从L3移除
5. _task_index中仍然保留引用 → 内存泄漏
```

**空间复杂度**: O(所有历史Task数量) - 无界增长

**影响**:
- 长期运行的系统会持续累积Task对象
- 内存占用线性增长，最终导致OOM

---

#### 问题2: Fact索引的无限增长

**位置**: `loom/paradigms/multi_agent.py`, `loom/paradigms/tool_use.py`

**问题代码**:
```python
# 直接向_fact_index添加fact，无上限检查
if exec_context.memory:
    facts = await exec_context.memory.fact_extractor.extract_facts(task)
    for fact in facts:
        exec_context.memory._fact_index[fact.fact_id] = fact
```

**问题描述**:
- 直接访问私有属性`_fact_index`，绕过封装
- 每个Task可能提取多个facts
- 无上限检查，无过期清理机制
- 长期运行会导致`_fact_index`无限增长

**空间复杂度**: O(所有历史Fact数量) - 无界增长

**影响**:
- 每个Task执行都可能添加1-5个facts
- 1000个Task = 1000-5000个facts
- 10000个Task = 10000-50000个facts
- 内存占用持续增长

---

#### 问题3: 并行执行的深拷贝问题

**位置**: `loom/orchestration/pipeline_builder.py`

**问题代码**:
```python
class ParallelStep(PipelineStep):
    async def execute(self, task: Task) -> Task:
        from copy import deepcopy

        # 为每个节点创建任务的深拷贝
        tasks = [deepcopy(task) for _ in self.nodes]

        results = await asyncio.gather(
            *[node.execute_task(t) for node, t in zip(self.nodes, tasks, strict=False)],
            return_exceptions=True,
        )
```

**问题描述**:
- 每个并行节点都创建完整的Task深拷贝
- N个节点 = N个完整的Task副本在内存中
- 如果Task包含大量数据（参数、结果），内存占用成倍增加

**空间复杂度**: O(N × sizeof(Task))

**示例场景**:
```
场景1: 10个并行节点 + 1MB任务 = 10MB内存占用
场景2: 100个并行节点 + 1MB任务 = 100MB内存占用
场景3: 10个并行节点 + 10MB任务 = 100MB内存占用
```

**影响**:
- 并行度越高，内存占用越大
- 大型任务（如包含大量上下文）会导致严重的内存浪费
- 可能导致内存不足或性能下降

---

#### 问题4: L2任务无限制加载

**位置**: `loom/paradigms/context_builder.py`

**问题代码**:
```python
def build(self) -> ExecutionContext:
    if self._strategy == "balanced":
        # 1. 最近的5个Task（L1）
        recent = self._memory.get_l1_tasks(limit=5)

        # 2. 当前工作相关的Task（L2）
        working = self._memory.get_l2_tasks()  # 无limit参数！

        # 4. 去重合并
        task_history = self._deduplicate([recent, working, relevant])
```

**问题描述**:
- `get_l2_tasks()`返回所有L2任务，无limit参数
- 如果L2包含100个任务，每次构建上下文都会加载所有100个
- 多次构建会导致内存中存在多个副本

**空间复杂度**: O(L2_size) - 每次构建都加载全部L2

**影响**:
- L2设计容量为100个任务
- 每次构建上下文可能加载100个Task对象
- 如果频繁构建上下文，内存占用会显著增加

---

#### 问题5: 循环引用风险

**位置**: `loom/paradigms/execution_context.py`

**问题代码**:
```python
@dataclass
class ExecutionContext:
    current_task: "Task | None" = None
    task_history: list["Task"] = field(default_factory=list)
    memory: "LoomMemory | None" = None
    parent_context: dict[str, Any] | None = None  # 可能形成循环引用
```

**问题描述**:
- `parent_context`可能包含对当前context的引用
- 形成循环引用：Context A → parent_context → Context B → parent_context → Context A
- Python垃圾回收器可以处理，但会增加GC压力

**影响**:
- 增加垃圾回收器的负担
- 可能导致内存释放延迟
- 在高频创建context的场景下影响性能

---

## 3. 递归机制问题分析

### 3.1 问题概览

| 问题类型 | 严重程度 | 影响范围 | 优先级 |
|---------|---------|---------|--------|
| NodeContainer无深度限制 | 高 | Fractal | P0 |
| Pipeline嵌套无检查 | 中 | Orchestration | P1 |
| 反思范式有界递归 | 低 | Paradigms | P2 |

### 3.2 问题详解

#### 问题6: NodeContainer的无限递归风险

**位置**: `loom/fractal/container.py`

**问题代码**:
```python
async def execute_task(self, task: Task) -> Task:
    if self.child:
        return await self.child.execute_task(task)  # 无深度限制
    task.error = "No child to execute task"
    return task
```

**问题描述**:
- 容器可以无限嵌套：Container1 → Container2 → Container3 → ...
- 每层调用都会增加调用栈深度
- Python默认递归限制为1000层，超过会导致RecursionError

**递归深度**: 理论上无限，实践中受限于Python递归限制

**风险场景**:
```python
# 创建深度1000+的容器链
container1 = NodeContainer(...)
container2 = NodeContainer(...)
# ... 1000个容器
container1.set_child(container2)
container2.set_child(container3)
# ...
# 执行时会导致RecursionError
```

**影响**:
- 深度超过1000层会导致RecursionError
- 即使不超过限制，深层递归也会消耗大量栈空间
- 调试困难，错误信息不清晰

---

#### 问题7: Pipeline嵌套的隐式递归

**位置**: `loom/orchestration/pipeline_builder.py`

**问题代码**:
```python
async def execute_task(self, task: Task) -> Task:
    current_task = task
    for i, step in enumerate(self.steps):
        current_task = await step.execute(current_task)
        # 如果step本身是Pipeline，会形成嵌套调用
```

**问题描述**:
- Pipeline可以包含其他Pipeline作为步骤
- 嵌套Pipeline会形成递归调用链
- 无显式深度检查

**风险场景**:
```python
# Pipeline A包含Pipeline B
# Pipeline B包含Pipeline C
# Pipeline C包含Pipeline D
# 形成4层嵌套
```

**影响**:
- 嵌套深度过大会增加调用栈深度
- 调试困难，难以追踪执行流程
- 性能开销随嵌套深度增加

---

## 4. React机制（反应式执行）分析

### 4.1 现状评估

**当前实现**:
- 反思范式（ReflectionParadigm）提供有界的迭代反应
- 条件分支（ConditionalStep）提供基于条件的反应式路由
- 路由编排器（RouterOrchestrator）提供基于能力的反应式选择

**优点**:
- 反思范式实现了基本的自我评估和改进
- 有界迭代（max_iterations=3）避免了无限循环
- 简洁的实现符合"分型结构内部非常简单"的原则

### 4.2 问题识别

#### 问题8: 缺乏全局反应机制

**问题描述**:
- 反应式执行仅限于单节点或简单的条件分支
- 缺乏跨节点的全局反应机制
- 无法实现复杂的反馈循环

**示例场景**:
```
场景：多节点协作中的动态调整
- Node A执行失败
- 需要通知Node B调整策略
- 当前无法实现这种跨节点反应
```

**影响**:
- 限制了系统的自适应能力
- 无法实现复杂的协作模式
- 需要手动编排反馈逻辑

#### 问题9: 缺乏状态观察机制

**问题描述**:
- 无Observable/Reactive模式的实现
- 无事件驱动的反应式更新
- 状态变化无法自动触发相关节点的更新

**影响**:
- 需要主动轮询状态变化
- 无法实现真正的反应式架构
- 增加了编程复杂度

### 4.3 设计反思

**问题**:
- 当前的React机制过于简单，仅支持单节点的迭代反应
- 缺乏系统级的反应式支持

**建议**:
- 保持当前简洁的实现（符合设计原则）
- 如需复杂反应式能力，应通过组合现有范式实现
- 避免引入过度复杂的反应式框架

---

## 5. 四大范式实现分析

### 5.1 现状评估

**四大范式实现**:
1. **ReflectionParadigm** (`reflection.py`) - 反思范式 ✅
2. **ToolUseParadigm** (`tool_use.py`) - 工具使用范式 ✅
3. **MultiAgentParadigm** (`multi_agent.py`) - 多代理范式 ✅
4. **PlanningParadigm** (`planning/`) - 规划范式 ✅

**优点**:
- 四大范式都已实现，符合A6公理
- 接口统一（都继承自Paradigm基类）
- 实现简洁，符合"分型结构内部非常简单"的原则

### 5.2 问题识别

#### 问题10: 范式间的耦合

**位置**: `loom/paradigms/multi_agent.py`, `loom/paradigms/tool_use.py`

**问题代码**:
```python
# 范式直接访问Memory的私有属性
if exec_context.memory:
    facts = await exec_context.memory.fact_extractor.extract_facts(task)
    for fact in facts:
        exec_context.memory._fact_index[fact.fact_id] = fact  # 直接访问私有属性
```

**问题描述**:
- 范式直接访问Memory的私有属性`_fact_index`
- 绕过了封装，违反了面向对象原则
- 增加了范式和Memory之间的耦合

**影响**:
- 如果Memory的内部实现改变，范式代码也需要修改
- 难以维护和测试
- 违反了"确保自由度的同时保持接口简单"的原则

#### 问题11: ExecutionContext的过度设计

**位置**: `loom/paradigms/execution_context.py`

**问题代码**:
```python
@dataclass
class ExecutionContext:
    current_task: "Task | None" = None
    task_history: list["Task"] = field(default_factory=list)
    memory: "LoomMemory | None" = None
    session_id: str = "default"
    agent_card: "AgentCard | None" = None
    parent_context: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

**问题描述**:
- ExecutionContext包含7个字段，可能过于复杂
- 部分字段使用率低（如parent_context）
- 增加了使用复杂度

**反思**:
- 是否所有字段都是必需的？
- 能否简化为更简洁的接口？
- 是否符合"接口简单"的原则？

### 5.3 设计反思

**优点**:
- 四大范式的实现都很简洁
- 基类设计合理（只有一个execute方法）
- 符合公理化设计原则

**改进方向**:
- 减少范式和Memory之间的耦合
- 简化ExecutionContext的设计
- 提供更清晰的封装边界

---

## 6. 架构封装反思

### 6.1 封装合理性评估

#### 6.1.1 良好的封装

**Fractal模块**:
- ✅ NodeContainer非常简洁（88行）
- ✅ 只提供核心的包装能力
- ✅ 符合"分型结构内部非常简单"的原则

**Paradigm基类**:
- ✅ 接口极简（只有一个execute方法）
- ✅ 易于扩展和实现
- ✅ 符合"接口简单"的原则

**Protocol定义**:
- ✅ NodeProtocol定义清晰
- ✅ Task、AgentCard等数据结构设计合理
- ✅ 提供了良好的抽象

#### 6.1.2 过度封装的问题

**ContextBuilder**:
```python
# 链式调用API
builder = ContextBuilder()
builder.with_memory(memory)
       .with_session_id(session_id)
       .with_agent_card(agent_card)
       .with_parent_context(parent_context)
       .with_current_task(task)
       .with_strategy(strategy)
```

**问题**:
- 链式调用增加了复杂度
- 提供了两个构建方法（build和build_async）
- 可能过度设计

**建议**:
- 考虑简化为直接构造函数
- 减少API表面积

### 6.2 自由度与简洁性的平衡

#### 6.2.1 成功的平衡

**Paradigm接口**:
```python
class Paradigm(ABC):
    @abstractmethod
    async def execute(self, task: Task, context: dict[str, Any]) -> Task:
        pass
```

**优点**:
- 接口极简（一个方法）
- context使用dict提供最大自由度
- 易于扩展和实现

**符合原则**:
- ✅ 接口简单
- ✅ 自由度高
- ✅ 易于理解和使用

#### 6.2.2 需要改进的地方

**Memory的封装**:
- ❌ 私有属性被外部直接访问（`_fact_index`）
- ❌ 缺乏清晰的公共API
- ❌ 封装边界不清晰

**建议**:
- 提供公共方法`add_fact(fact)`替代直接访问`_fact_index`
- 明确哪些是公共API，哪些是内部实现
- 使用`__`前缀标记真正的私有属性

### 6.3 架构反思总结

**设计原则回顾**:
1. **分型结构内部非常简单** - ✅ 已实现（NodeContainer、Paradigm基类）
2. **确保自由度的同时保持接口简单** - ⚠️ 部分实现（Paradigm接口好，ContextBuilder过度设计）
3. **对之前的封装进行反思** - ✅ 已识别问题（Memory封装、范式耦合）

**核心问题**:
- 部分模块过度封装（ContextBuilder）
- 部分模块封装不足（Memory的私有属性被直接访问）
- 需要找到更好的平衡点

---

## 7. 优化建议和改进方案

### 7.1 P0优先级改进（必须立即修复）

#### 改进1: 修复Task索引内存泄漏

**目标**: 防止`_task_index`无限增长

**方案**:
```python
class LoomMemory:
    def __init__(self, ...):
        self._task_index: dict[str, "Task"] = {}
        self._max_index_size = 1000  # 最大索引大小

    def add_task(self, task: "Task", tier: MemoryTier = MemoryTier.L1_RAW_IO) -> None:
        # 添加到索引
        self._task_index[task.task_id] = task

        # 定期清理
        if len(self._task_index) > self._max_index_size:
            self._cleanup_task_index()

    def _cleanup_task_index(self) -> None:
        """清理过期的Task索引"""
        # 保留L1、L2、L3中的Task
        active_task_ids = set()
        active_task_ids.update(t.task_id for t in self._l1_tasks)
        active_task_ids.update(t.task_id for t in self._l2_tasks)
        active_task_ids.update(s.task_id for s in self._l3_summaries)

        # 删除不活跃的Task
        self._task_index = {
            tid: task for tid, task in self._task_index.items()
            if tid in active_task_ids
        }
```

**预期效果**:
- 索引大小保持在合理范围内
- 防止内存泄漏
- 不影响正常功能

---

#### 改进2: 修复Fact索引内存泄漏

**目标**: 提供公共API，防止`_fact_index`无限增长

**方案**:
```python
class LoomMemory:
    def __init__(self, ...):
        self._fact_index: dict[str, Fact] = {}
        self._max_fact_index_size = 5000  # 最大Fact索引大小

    def add_fact(self, fact: Fact) -> None:
        """添加Fact到索引（公共API）"""
        self._fact_index[fact.fact_id] = fact

        # 定期清理
        if len(self._fact_index) > self._max_fact_index_size:
            self._cleanup_fact_index()

    def _cleanup_fact_index(self) -> None:
        """清理低价值的Fact"""
        # 按访问次数和置信度排序
        facts = sorted(
            self._fact_index.values(),
            key=lambda f: (f.access_count, f.confidence),
            reverse=True
        )

        # 保留前80%
        keep_count = int(len(facts) * 0.8)
        self._fact_index = {f.fact_id: f for f in facts[:keep_count]}
```

**范式代码修改**:
```python
# 修改前（直接访问私有属性）
exec_context.memory._fact_index[fact.fact_id] = fact

# 修改后（使用公共API）
exec_context.memory.add_fact(fact)
```

**预期效果**:
- 提供清晰的封装边界
- 防止Fact索引无限增长
- 保留高价值的Facts

---

#### 改进3: 优化并行执行的深拷贝

**目标**: 减少并行执行时的内存占用

**方案**:
```python
class ParallelStep(PipelineStep):
    async def execute(self, task: Task) -> Task:
        # 方案1: 浅拷贝（推荐）
        # 只拷贝Task对象本身，不拷贝内部数据
        tasks = [Task(
            task_id=f"{task.task_id}_parallel_{i}",
            action=task.action,
            parameters=task.parameters,  # 共享引用
            target_agent=task.target_agent,
        ) for i, _ in enumerate(self.nodes)]

        # 方案2: 写时复制（Copy-on-Write）
        # 使用共享的只读数据，只在修改时才复制
        # 需要更复杂的实现，暂不推荐

        results = await asyncio.gather(
            *[node.execute_task(t) for node, t in zip(self.nodes, tasks, strict=False)],
            return_exceptions=True,
        )
```

**预期效果**:
- 空间复杂度从O(N × sizeof(Task))降低到O(N × sizeof(Task_metadata))
- 大幅减少内存占用
- 性能提升

---

#### 改进4: 添加递归深度限制

**目标**: 防止NodeContainer和Pipeline的无限递归

**方案**:
```python
class NodeContainer:
    def __init__(
        self,
        node_id: str,
        agent_card: AgentCard,
        child: NodeProtocol | None = None,
        max_depth: int = 100,  # 新增参数
    ):
        self.node_id = node_id
        self.source_uri = f"node://{node_id}"
        self.agent_card = agent_card
        self.child: NodeProtocol | None = child
        self.max_depth = max_depth
        self._current_depth = 0  # 当前深度

    async def execute_task(self, task: Task) -> Task:
        # 检查深度
        self._current_depth += 1
        if self._current_depth > self.max_depth:
            task.status = TaskStatus.FAILED
            task.error = f"Recursion depth exceeded: {self._current_depth} > {self.max_depth}"
            self._current_depth -= 1
            return task

        # 委托给子节点
        if self.child:
            result = await self.child.execute_task(task)
            self._current_depth -= 1
            return result

        task.error = "No child to execute task"
        self._current_depth -= 1
        return task
```

**预期效果**:
- 防止RecursionError
- 提供清晰的错误信息
- 可配置的深度限制

---

### 7.2 P1优先级改进（重要但不紧急）

#### 改进5: 优化L2任务加载

**目标**: 为`get_l2_tasks()`添加limit参数

**方案**:
```python
class LoomMemory:
    def get_l2_tasks(self, limit: int | None = None) -> list["Task"]:
        """获取L2任务"""
        if limit is None:
            return list(self._l2_tasks)
        return list(self._l2_tasks[:limit])
```

**ContextBuilder修改**:
```python
def build(self) -> ExecutionContext:
    if self._strategy == "balanced":
        recent = self._memory.get_l1_tasks(limit=5)
        working = self._memory.get_l2_tasks(limit=10)  # 添加limit
        # ...
```

**预期效果**:
- 减少上下文构建时的内存占用
- 提供更灵活的控制

---

#### 改进6: 简化ContextBuilder

**目标**: 减少过度封装，提供更简洁的API

**方案**:
```python
# 方案1: 简化为直接构造函数
context = ExecutionContext(
    current_task=task,
    memory=memory,
    session_id="session_123",
    strategy="balanced"
)

# 方案2: 保留builder但简化
def create_context(
    task: Task,
    memory: LoomMemory,
    strategy: str = "balanced",
    **kwargs
) -> ExecutionContext:
    """简化的上下文创建函数"""
    # 直接构建，无需链式调用
    return ExecutionContext(...)
```

**预期效果**:
- 减少API复杂度
- 更易于理解和使用
- 符合"接口简单"原则

---

### 7.3 P2优先级改进（可选优化）

#### 改进7: 添加循环引用检测

**目标**: 检测并警告循环引用

**方案**:
```python
class ExecutionContext:
    def __post_init__(self):
        """检测循环引用"""
        if self.parent_context:
            self._check_circular_reference()

    def _check_circular_reference(self, visited: set | None = None) -> None:
        """检测循环引用"""
        if visited is None:
            visited = set()

        context_id = id(self)
        if context_id in visited:
            logger.warning("Circular reference detected in ExecutionContext")
            return

        visited.add(context_id)
        # 递归检查parent_context
```

---

## 8. 总结与结论

### 8.1 关键发现

**空间复杂度问题**:
- ✅ 识别了5个关键问题（Task索引、Fact索引、深拷贝、L2加载、循环引用）
- ✅ 提供了具体的修复方案
- ✅ 优先级明确（P0-P2）

**递归机制问题**:
- ✅ 识别了2个关键问题（NodeContainer、Pipeline嵌套）
- ✅ 提供了深度限制方案
- ✅ 保持了分型结构的简洁性

**React机制**:
- ✅ 当前实现简洁有效
- ⚠️ 缺乏全局反应机制（但符合设计原则）
- ✅ 建议保持现状，通过组合实现复杂功能

**四大范式**:
- ✅ 实现完整，符合A6公理
- ⚠️ 存在耦合问题（范式直接访问Memory私有属性）
- ✅ 提供了解耦方案

**架构封装**:
- ✅ 部分模块封装良好（Fractal、Paradigm基类）
- ⚠️ 部分模块过度封装（ContextBuilder）
- ⚠️ 部分模块封装不足（Memory）

### 8.2 设计原则评估

| 原则 | 评估 | 说明 |
|-----|------|------|
| 分型结构内部非常简单 | ✅ 优秀 | NodeContainer、Paradigm基类都很简洁 |
| 确保自由度的同时保持接口简单 | ⚠️ 部分达成 | Paradigm接口好，ContextBuilder过度设计 |
| 对之前的封装进行反思 | ✅ 已完成 | 识别了封装问题并提供改进方案 |

### 8.3 实施建议

**立即实施（P0）**:
1. 修复Task索引内存泄漏
2. 修复Fact索引内存泄漏（提供公共API）
3. 优化并行执行的深拷贝
4. 添加递归深度限制

**近期实施（P1）**:
1. 优化L2任务加载
2. 简化ContextBuilder

**可选实施（P2）**:
1. 添加循环引用检测

### 8.4 预期收益

**内存优化**:
- Task索引：从无界增长 → 最多1000个
- Fact索引：从无界增长 → 最多5000个
- 并行执行：内存占用减少50-90%

**稳定性提升**:
- 防止RecursionError
- 防止OOM
- 提供清晰的错误信息

**代码质量**:
- 更清晰的封装边界
- 更简洁的API
- 更易于维护

---

## 9. 附录

### 9.1 问题优先级矩阵

| 问题 | 严重程度 | 影响范围 | 修复难度 | 优先级 |
|-----|---------|---------|---------|--------|
| Task索引泄漏 | 高 | Memory | 低 | P0 |
| Fact索引泄漏 | 高 | Memory | 低 | P0 |
| 并行深拷贝 | 高 | Orchestration | 中 | P0 |
| 递归深度 | 高 | Fractal | 中 | P0 |
| L2无限制加载 | 中 | Context | 低 | P1 |
| ContextBuilder过度设计 | 中 | Paradigms | 中 | P1 |
| 循环引用 | 低 | Context | 低 | P2 |

### 9.2 相关文件清单

**需要修改的文件**:
1. `loom/memory/core.py` - 添加索引清理机制
2. `loom/paradigms/multi_agent.py` - 使用公共API
3. `loom/paradigms/tool_use.py` - 使用公共API
4. `loom/orchestration/pipeline_builder.py` - 优化深拷贝
5. `loom/fractal/container.py` - 添加深度限制
6. `loom/paradigms/context_builder.py` - 简化API

**需要添加的测试**:
1. `tests/memory/test_index_cleanup.py` - 测试索引清理
2. `tests/fractal/test_depth_limit.py` - 测试深度限制
3. `tests/orchestration/test_parallel_memory.py` - 测试并行内存优化

---

**文档版本**: v1.0
**最后更新**: 2026-01-18
**作者**: Claude Code Analysis

