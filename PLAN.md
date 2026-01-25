# 实施计划：Loom Agent 系统全面优化

**目标版本**: v0.4.2 - v0.4.3
**创建日期**: 2026-01-25
**预计工期**: 8-10 周

## 📋 概述

本计划涵盖系统优化的三个核心阶段：
- **Phase 1**: 记忆系统重构（L1-L4 层级抽象）- v0.4.2
- **Phase 2**: 事件总线简化（类型安全 + 模式分离）- v0.4.2
- **Phase 3**: 分形架构重新设计（智能记忆分配 + 双向流动）- v0.4.3

## 🎯 目标

### 性能目标
- L2 插入性能提升 100x（从 O(n log n) 到 O(log n)）
- 内存占用减少 20%
- 代码复杂度降低 40%

### 质量目标
- 测试覆盖率达到 85%+
- 类型检查 100% 通过（mypy --strict）
- 零 lint 警告

### 架构目标
- 清晰的层级抽象
- 职责分离
- 易于扩展和测试

---

## 📦 任务分解

### Task 1: 创建 MemoryLayer 抽象接口

**优先级**: P0（最高）
**预计时间**: 1 天
**依赖**: 无

#### 目标
定义统一的记忆层级抽象接口，为所有层级提供一致的操作契约。

#### 实现文件
- `loom/memory/layers/__init__.py`
- `loom/memory/layers/base.py`

#### 详细设计

```python
# loom/memory/layers/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any

T = TypeVar('T')

class MemoryLayer(ABC, Generic[T]):
    """
    记忆层级抽象接口

    所有记忆层级（L1-L4）的统一契约。
    基于公理 A4（记忆层次公理）。
    """

    @abstractmethod
    async def add(self, item: T) -> None:
        """
        添加项目到层级

        Args:
            item: 要添加的项目
        """
        pass

    @abstractmethod
    async def retrieve(self, query: Any, limit: int = 10) -> list[T]:
        """
        从层级检索项目

        Args:
            query: 查询条件（可以是字符串、过滤器等）
            limit: 返回数量限制

        Returns:
            匹配的项目列表
        """
        pass

    @abstractmethod
    async def evict(self, count: int = 1) -> list[T]:
        """
        驱逐项目（用于容量管理）

        Args:
            count: 要驱逐的数量

        Returns:
            被驱逐的项目列表
        """
        pass

    @abstractmethod
    def size(self) -> int:
        """
        获取当前层级大小

        Returns:
            当前存储的项目数量
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空层级"""
        pass
```

#### 验收标准
- [ ] 接口定义清晰，包含完整的类型注解
- [ ] 文档字符串完整
- [ ] 通过 mypy --strict 检查
- [ ] 单元测试覆盖所有抽象方法的契约

#### 测试策略
创建一个测试基类，验证任何实现都符合接口契约：

```python
# tests/memory/test_layer_contract.py
class MemoryLayerContractTest:
    """测试任何 MemoryLayer 实现都应该通过的契约测试"""

    @abstractmethod
    def create_layer(self) -> MemoryLayer:
        """子类实现：创建待测试的层级实例"""
        pass

    async def test_add_and_retrieve(self):
        layer = self.create_layer()
        item = self.create_test_item()

        await layer.add(item)
        results = await layer.retrieve(query=None, limit=10)

        assert len(results) >= 1
        assert item in results

    async def test_size(self):
        layer = self.create_layer()
        assert layer.size() == 0

        await layer.add(self.create_test_item())
        assert layer.size() == 1

    # ... 更多契约测试
```

---

### Task 2: 实现 CircularBufferLayer (L1)

**优先级**: P0
**预计时间**: 2 天
**依赖**: Task 1

#### 目标
实现 L1 循环缓冲层，解决当前索引管理的复杂性问题。

#### 实现文件
- `loom/memory/layers/circular.py`

#### 核心改进

**问题**: 当前实现手动管理索引同步
```python
# 当前实现的问题
if len(self._l1_tasks) == self.max_l1_size:
    current_ids = {t.task_id for t in self._l1_tasks}
    evicted_ids = set(self._task_index.keys()) - current_ids
    for evicted_id in evicted_ids:
        self._task_index.pop(evicted_id, None)
```

**解决方案**: 使用回调机制自动通知驱逐事件

```python
# loom/memory/layers/circular.py
from collections import deque
from typing import Callable, Any
from loom.protocol import Task
from .base import MemoryLayer

class CircularBufferLayer(MemoryLayer[Task]):
    """
    L1: 循环缓冲层

    特性：
    - 固定容量的循环缓冲区
    - FIFO 驱逐策略
    - 驱逐事件回调机制
    """

    def __init__(self, max_size: int = 50):
        self._buffer: deque[Task] = deque(maxlen=max_size)
        self._eviction_callbacks: list[Callable[[Task], None]] = []

    async def add(self, item: Task) -> None:
        """添加任务，自动驱逐最旧的"""
        # 检查是否会驱逐
        if len(self._buffer) == self._buffer.maxlen:
            evicted = self._buffer[0]
            # 触发驱逐回调
            for callback in self._eviction_callbacks:
                callback(evicted)

        self._buffer.append(item)

    async def retrieve(self, query: Any, limit: int = 10) -> list[Task]:
        """获取最近的 N 个任务"""
        return list(self._buffer)[-limit:]

    async def evict(self, count: int = 1) -> list[Task]:
        """手动驱逐（从左侧移除）"""
        evicted = []
        for _ in range(min(count, len(self._buffer))):
            if self._buffer:
                evicted.append(self._buffer.popleft())
        return evicted

    def size(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()

    def on_eviction(self, callback: Callable[[Task], None]) -> None:
        """
        注册驱逐回调

        当任务被自动驱逐时，会调用所有注册的回调函数。
        这允许外部组件（如索引管理器）响应驱逐事件。
        """
        self._eviction_callbacks.append(callback)
```

#### 验收标准
- [ ] 实现所有 MemoryLayer 接口方法
- [ ] 通过 MemoryLayerContractTest
- [ ] 驱逐回调机制正常工作
- [ ] 性能测试：1000 次插入 < 10ms
- [ ] 测试覆盖率 > 90%

#### 测试用例

```python
# tests/memory/layers/test_circular.py
import pytest
from loom.memory.layers import CircularBufferLayer
from loom.protocol import Task

class TestCircularBufferLayer:
    async def test_fifo_eviction(self):
        """测试 FIFO 驱逐策略"""
        layer = CircularBufferLayer(max_size=3)

        task1 = Task(task_id="1", action="test")
        task2 = Task(task_id="2", action="test")
        task3 = Task(task_id="3", action="test")
        task4 = Task(task_id="4", action="test")

        await layer.add(task1)
        await layer.add(task2)
        await layer.add(task3)
        assert layer.size() == 3

        # 添加第4个，应该驱逐第1个
        await layer.add(task4)
        assert layer.size() == 3

        tasks = await layer.retrieve(query=None, limit=10)
        assert task1 not in tasks
        assert task4 in tasks

    async def test_eviction_callback(self):
        """测试驱逐回调机制"""
        layer = CircularBufferLayer(max_size=2)
        evicted_tasks = []

        # 注册回调
        layer.on_eviction(lambda task: evicted_tasks.append(task))

        task1 = Task(task_id="1", action="test")
        task2 = Task(task_id="2", action="test")
        task3 = Task(task_id="3", action="test")

        await layer.add(task1)
        await layer.add(task2)
        assert len(evicted_tasks) == 0

        # 添加第3个，应该触发回调
        await layer.add(task3)
        assert len(evicted_tasks) == 1
        assert evicted_tasks[0] == task1
```

---

### Task 3: 实现 PriorityQueueLayer (L2)

**优先级**: P0
**预计时间**: 2 天
**依赖**: Task 1

#### 目标
实现 L2 优先级队列层，解决当前重复排序的性能问题。

#### 实现文件
- `loom/memory/layers/priority.py`

#### 核心改进

**问题**: 当前实现每次插入都要全量排序
```python
# 当前实现：O(n log n)
self._l2_tasks.append(task)
self._l2_tasks.sort(key=lambda t: t.metadata.get("importance", 0.5), reverse=True)
```

**解决方案**: 使用堆（heap）数据结构

```python
# loom/memory/layers/priority.py
import heapq
from dataclasses import dataclass, field
from typing import Any
from loom.protocol import Task
from .base import MemoryLayer

@dataclass(order=True)
class PriorityItem:
    """优先级项（用于堆排序）"""
    priority: float
    item: Task = field(compare=False)

class PriorityQueueLayer(MemoryLayer[Task]):
    """
    L2: 优先级队列层

    特性：
    - 基于堆的优先级队列
    - O(log n) 插入和删除
    - 自动维护优先级顺序
    """

    def __init__(self, max_size: int = 100):
        self._heap: list[PriorityItem] = []
        self._max_size = max_size

    async def add(self, item: Task) -> None:
        """添加任务（O(log n)）"""
        importance = item.metadata.get("importance", 0.5)
        # 使用负数实现最大堆
        priority_item = PriorityItem(-importance, item)

        if len(self._heap) < self._max_size:
            heapq.heappush(self._heap, priority_item)
        else:
            # 如果新项目优先级更高，替换最低优先级项
            if priority_item < self._heap[0]:
                heapq.heapreplace(self._heap, priority_item)

    async def retrieve(self, query: Any, limit: int = 10) -> list[Task]:
        """获取前 N 个最高优先级任务"""
        sorted_items = sorted(self._heap)[:limit]
        return [item.item for item in sorted_items]

    async def evict(self, count: int = 1) -> list[Task]:
        """驱逐最低优先级的任务"""
        evicted = []
        for _ in range(min(count, len(self._heap))):
            item = heapq.heappop(self._heap)
            evicted.append(item.item)
        return evicted

    def size(self) -> int:
        return len(self._heap)

    def clear(self) -> None:
        self._heap.clear()
```

#### 性能对比

| 操作 | 当前实现 | 优化后 | 提升 |
|------|---------|--------|------|
| 插入 (n=100) | ~700 比较 | ~7 比较 | **100x** |
| 获取最大 | O(1) | O(1) | 相同 |
| 删除最小 | O(n log n) | O(log n) | **100x** |

#### 验收标准
- [ ] 实现所有 MemoryLayer 接口方法
- [ ] 通过 MemoryLayerContractTest
- [ ] 性能测试：1000 次插入 < 50ms（当前 > 5000ms）
- [ ] 测试覆盖率 > 90%

---

### Task 4: 重构 LoomMemory 为协调器

**优先级**: P0
**预计时间**: 3 天
**依赖**: Task 1, 2, 3

#### 目标
将 LoomMemory 从单体类重构为层级协调器，使用依赖注入。

#### 实现文件
- `loom/memory/core.py`（修改实现）
- `loom/memory/core.py`（标记为 deprecated）

#### 核心设计

```python
# loom/memory/core.py
from typing import TYPE_CHECKING
from .layers import MemoryLayer, CircularBufferLayer, PriorityQueueLayer
from .types import MemoryTier, TaskSummary

if TYPE_CHECKING:
    from loom.protocol import Task

class LoomMemory:
    """
    记忆系统协调器（重构版）

    职责：
    - 管理四个记忆层级
    - 协调层级间的数据流动
    - 提供统一的查询接口
    """

    def __init__(
        self,
        node_id: str,
        l1_layer: MemoryLayer["Task"] | None = None,
        l2_layer: MemoryLayer["Task"] | None = None,
        # ... 其他层级
    ):
        self.node_id = node_id

        # 依赖注入，支持自定义实现
        self.l1 = l1_layer or CircularBufferLayer(max_size=50)
        self.l2 = l2_layer or PriorityQueueLayer(max_size=100)

        # 设置层级间的数据流动
        self._setup_layer_flow()

    def _setup_layer_flow(self) -> None:
        """设置层级间的自动流动"""
        # L1 驱逐时，重要的 Task 提升到 L2
        if isinstance(self.l1, CircularBufferLayer):
            self.l1.on_eviction(self._on_l1_eviction)

    def _on_l1_eviction(self, task: "Task") -> None:
        """L1 驱逐回调：提升重要任务到 L2"""
        importance = task.metadata.get("importance", 0.5)
        if importance > 0.6:  # 阈值可配置
            asyncio.create_task(self.l2.add(task))
```

#### 验收标准
- [ ] 所有现有功能正常工作
- [ ] 通过所有现有测试
- [ ] 新增测试覆盖层级协调逻辑
- [ ] 性能不低于当前实现

---

### Task 5: 事件总线类型安全路由

**优先级**: P1
**预计时间**: 2 天
**依赖**: 无

#### 目标
引入类型安全的路由系统，替代字符串键值。

#### 实现文件
- `loom/events/actions.py`
- `loom/events/handlers.py`
- `loom/events/event_bus.py`（修改实现）

#### 核心设计

```python
# loom/events/actions.py
from enum import Enum

class TaskAction(str, Enum):
    """任务动作类型（类型安全）"""
    EXECUTE = "execute_task"
    CANCEL = "cancel_task"
    QUERY = "query_task"
    STREAM = "stream_task"

# loom/events/handlers.py
from typing import Protocol
from loom.protocol import Task

class TaskHandler(Protocol):
    """任务处理器协议"""
    async def __call__(self, task: Task) -> Task:
        ...
```

#### 验收标准
- [ ] 所有路由使用 TaskAction 枚举
- [ ] 通过 mypy --strict 检查
- [ ] 拼写错误在编译时被捕获
- [ ] 测试覆盖率 > 85%

---

## 📦 Phase 3: 分形架构任务

### Task 6: 实现分形记忆系统

**优先级**: P0（最高）
**预计时间**: 3 天
**依赖**: Task 1, 2, 3, 4

#### 目标
实现分形记忆管理系统，支持四种作用域和智能记忆分配。

#### 实现文件
- `loom/fractal/memory.py` - 核心记忆管理
- `loom/fractal/__init__.py`

#### 核心组件

```python
# 记忆作用域
class MemoryScope(Enum):
    LOCAL = "local"          # 节点私有
    SHARED = "shared"        # 父子双向共享
    INHERITED = "inherited"  # 从父节点继承（只读）
    GLOBAL = "global"        # 全局共享

# 分形记忆管理器
class FractalMemory:
    def __init__(self, node_id: str, parent_memory: Optional["FractalMemory"] = None):
        self.node_id = node_id
        self.parent_memory = parent_memory
        self._memory_by_scope: Dict[MemoryScope, Dict[str, MemoryEntry]] = {}

    async def write(self, entry_id: str, content: Any, scope: MemoryScope) -> MemoryEntry:
        """写入记忆"""
        pass

    async def read(self, entry_id: str, search_scopes: Optional[List[MemoryScope]] = None) -> Optional[MemoryEntry]:
        """读取记忆"""
        pass
```

#### 验收标准
- [ ] 实现四种记忆作用域
- [ ] 实现记忆读写接口
- [ ] 实现父子节点记忆继承
- [ ] 测试覆盖率 > 90%

---

### Task 7: 实现同步机制与冲突解决

**优先级**: P0
**预计时间**: 3 天
**依赖**: Task 6

#### 目标
实现版本控制、乐观锁和冲突解决策略。

#### 实现文件
- `loom/fractal/sync.py` - 同步管理器
- `loom/fractal/resolvers.py` - 冲突解决器

#### 核心组件

```python
# 同步管理器
class MemorySyncManager:
    async def write_with_version_check(self, entry: MemoryEntry, expected_version: int) -> Tuple[bool, Optional[str]]:
        """带版本检查的写入（乐观锁）"""
        pass

    async def sync_from_parent(self) -> int:
        """从父节点同步SHARED记忆"""
        pass

# 冲突解决策略
class ConflictResolver(ABC):
    @abstractmethod
    async def resolve(self, parent_entry: MemoryEntry, child_entry: MemoryEntry) -> MemoryEntry:
        pass

class ParentWinsResolver(ConflictResolver):
    """父节点优先策略"""
    pass

class ChildWinsResolver(ConflictResolver):
    """子节点优先策略"""
    pass

class MergeResolver(ConflictResolver):
    """智能合并策略"""
    pass
```

#### 验收标准
- [ ] 实现版本控制机制
- [ ] 实现三种冲突解决策略
- [ ] 实现变更传播机制
- [ ] 测试覆盖率 > 90%

---

### Task 8: 实现智能记忆分配策略

**优先级**: P1
**预计时间**: 2 天
**依赖**: Task 6

#### 目标
实现任务特征分析和智能记忆分配。

#### 实现文件
- `loom/fractal/allocation.py` - 分配策略
- `loom/fractal/analyzer.py` - 任务分析器

#### 核心组件

```python
# 任务分析器
class TaskAnalyzer:
    def analyze(self, task: Task) -> TaskFeatures:
        """分析任务特征"""
        pass

# 智能分配策略
class SmartAllocationStrategy:
    async def allocate(self, parent_memory: FractalMemory, child_task: Task) -> Dict[MemoryScope, List[MemoryEntry]]:
        """为子节点分配记忆"""
        pass
```

#### 验收标准
- [ ] 实现任务特征提取
- [ ] 实现相关性评分算法
- [ ] 保持O(1)复杂度
- [ ] 测试覆盖率 > 90%

---

### Task 9: 集成分形架构到现有系统（整合版）

**优先级**: P0
**预计时间**: 3 天
**依赖**: Task 6, 7, 8

#### 目标
将分形记忆系统深度整合到现有Agent架构，实现自主委派能力。

**整合要点**（基于fractal-architecture-redesign.md的整合方案）：
1. 使用meta-tools（delegate_task）而非显式方法
2. 整合TaskContextManager进行智能上下文传递
3. FractalMemory使用LoomMemory作为底层存储
4. 保持"Agent is just a for loop"哲学

#### 实现文件
- `loom/agent/base.py`（修改Agent类）
- `loom/orchestration/meta_tools.py`（新增meta-tools定义）
- `loom/fractal/integration.py`（新增整合辅助函数）

#### 核心实现

**1. 添加delegate_task meta-tool**

```python
# loom/orchestration/meta_tools.py

async def delegate_task_tool(
    subtask_description: str,
    required_capabilities: list[str] | None = None,
    context_hints: list[str] | None = None,
) -> str:
    """
    委派子任务给专门的Agent（元工具）

    Args:
        subtask_description: 子任务描述
        required_capabilities: 需要的能力列表
        context_hints: 上下文提示（哪些记忆需要传递）

    Returns:
        子任务执行结果
    """
    # 由Agent._auto_delegate()实现
    pass
```

**2. 在Agent中实现_auto_delegate方法**

```python
# loom/agent/base.py

class Agent(BaseNode):
    async def _auto_delegate(
        self,
        args: dict,
        parent_task: Task
    ) -> str:
        """
        自动委派实现（框架内部）

        整合点：
        - 使用FractalMemory建立父子关系
        - 使用SmartAllocationStrategy分配记忆
        - 使用TaskContextManager构建子节点上下文
        """
        # 1. 创建子任务
        subtask = Task(
            task_id=f"{parent_task.task_id}-child-{uuid4()}",
            action="execute",
            parameters={
                "content": args["subtask_description"],
                "parent_task_id": parent_task.task_id,
            }
        )

        # 2. 创建子节点（使用_create_child_node）
        child_node = await self._create_child_node(
            subtask=subtask,
            context_hints=args.get("context_hints", [])
        )

        # 3. 执行子任务
        result = await child_node.execute_task(subtask)

        # 4. 同步记忆（双向流动）
        await self._sync_memory_from_child(child_node)

        # 5. 返回结果
        return result.result.get("content", "")
```

**3. 实现_create_child_node方法**

```python
# loom/agent/base.py

class Agent(BaseNode):
    async def _create_child_node(
        self,
        subtask: Task,
        context_hints: list[str]
    ) -> "Agent":
        """
        创建子节点并智能分配上下文

        整合所有组件：
        - FractalMemory（继承父节点）
        - SmartAllocationStrategy（智能分配）
        - TaskContextManager（上下文构建）
        """
        # 1. 创建FractalMemory（继承父节点记忆）
        child_memory = FractalMemory(
            node_id=subtask.task_id,
            parent_memory=self.memory,
            base_memory=LoomMemory(node_id=subtask.task_id)
        )

        # 2. 使用SmartAllocationStrategy分配相关记忆
        allocation_strategy = SmartAllocationStrategy(
            max_inherited_memories=10
        )
        allocated_memories = await allocation_strategy.allocate(
            parent_memory=self.memory,
            child_task=subtask,
            context_hints=context_hints
        )

        # 3. 将分配的记忆写入子节点
        for scope, entries in allocated_memories.items():
            for entry in entries:
                await child_memory.write(entry.id, entry.content, scope=scope)

        # 4. 创建TaskContextManager
        child_context_manager = TaskContextManager(
            memory=child_memory.base_memory,
            event_bus=self.event_bus,
            max_context_tokens=4000
        )

        # 5. 创建子Agent
        child_agent = Agent(
            node_id=subtask.task_id,
            agent_card=self.agent_card,
            llm_provider=self.llm_provider,
            context_manager=child_context_manager,
            memory=child_memory,
            tools=self.tools
        )

        return child_agent
```

#### 验收标准
- [ ] 实现delegate_task meta-tool
- [ ] 实现Agent._auto_delegate方法
- [ ] 实现Agent._create_child_node方法
- [ ] 实现Agent._sync_memory_from_child方法
- [ ] 在Agent执行循环中集成meta-tool处理
- [ ] 通过所有现有测试
- [ ] 新增端到端集成测试（父子Agent协作）
- [ ] 验证记忆双向流动
- [ ] 性能基准测试通过

---

## 🔄 迁移策略

### 不向后兼容方案

```python
# loom/memory/__init__.py
import os
from loom.memory.core import LoomMemory as LoomMemory

# 默认使用新版本
LoomMemory = LoomMemory


### 完全重构策略（不向后兼容）

#### 破坏性重构原则
- **完全重写**：从零开始重新实现所有核心组件
- **不兼容旧版**：删除所有旧实现和兼容性代码
- **架构优先**：基于新设计完全重构，不妥协于历史债务
- **一次性升级**：强制用户在单个版本中完成所有迁移

#### 重构范围（v0.5.0 - 破坏性变更）
- **内存系统**：完全重写 L1-L4 层级实现
- **事件总线**：重新设计类型安全架构
- **协议接口**：统一所有 API 签名
- **配置系统**：简化配置结构
- **测试框架**：重写所有测试用例

#### 实施阶段

##### 阶段 1: 架构设计（1周）
- 完成新架构设计文档
- 定义新的 API 接口
- 确定破坏性变更清单
- 设计数据迁移工具

##### 阶段 2: 核心重构（3周）
- 重写 `loom/memory/` 模块
- 重写 `loom/events/` 模块
- 重写 `loom/protocol/` 接口
- 实现新的配置系统

##### 阶段 3: 测试重写（1周）
- 重写所有单元测试
- 重写集成测试
- 性能基准测试
- 破坏性变更验证

##### 阶段 4: 文档和工具（1周）
- 重写 API 文档
- 创建迁移指南
- 实现自动迁移工具
- 发布升级说明

#### 破坏性变更清单

##### API 变更
```python
# 旧 API (v0.4.x)
memory = LoomMemory(node_id="test")
await memory.add_task(task)
tasks = memory.get_recent_tasks()

# 新 API (v0.5.0)
memory = MemorySystem(
    config=MemoryConfig(node_id="test"),
    layers=MemoryLayers.default()
)
await memory.layers.l1.add(task)
tasks = await memory.query(QueryBuilder().recent(limit=10))
```

##### 配置变更
```python
# 旧配置
loom_config = {
    "memory": {"max_l1_size": 50},
    "events": {"batch_size": 100}
}

# 新配置
config = LoomConfig(
    memory=MemoryConfig(
        l1=CircularBufferConfig(capacity=50),
        l2=PriorityQueueConfig(capacity=100)
    ),
    events=EventSystemConfig(
        router=TypeSafeRouter(),
        batch_size=100
    )
)
```

#### 迁移工具
```bash
# 自动迁移命令
loom migrate --from=0.4.x --to=0.5.0 --project-path=.
# 生成迁移报告
loom migration-report --show-breaking-changes
# 验证迁移完整性
loom validate-migration --config=migrated_config.py
```

#### 发布策略
- **v0.5.0-rc.1**: 功能完整的候选版本
- **v0.5.0-rc.2**: 修复关键 Bug
- **v0.5.0**: 正式发布（强制升级）
- **v0.4.x**: 立即标记为 EOL（生命周期结束）

#### 用户迁移要求
- **强制升级**：v0.4.x 不再维护
- **代码重构**：必须修改所有使用 Loom 的代码
- **配置重写**：重新编写配置文件
- **测试更新**：更新所有相关测试

---

## 🧪 测试策略

### 单元测试

#### 层级抽象测试
```python
# tests/memory/test_layer_contract.py
# 确保所有层级实现符合接口契约
```

#### 性能基准测试
```python
# tests/memory/test_performance.py
import pytest
import time

def test_l2_insertion_performance():
    """L2 插入性能测试"""
    from loom.memory.layers import PriorityQueueLayer

    layer = PriorityQueueLayer(max_size=100)

    start = time.perf_counter()
    for i in range(1000):
        task = Task(task_id=f"task-{i}", action="test")
        task.metadata["importance"] = i / 1000
        await layer.add(task)

    elapsed = time.perf_counter() - start

    # 目标：< 50ms
    assert elapsed < 0.05, f"Too slow: {elapsed}s"
```

### 集成测试

#### 层级协调测试
```python
# tests/memory/test_integration.py
async def test_l1_to_l2_promotion():
    """测试 L1 驱逐时自动提升到 L2"""
    memory = LoomMemory(node_id="test")

    # 添加重要任务到 L1
    important_task = Task(task_id="important", action="test")
    important_task.metadata["importance"] = 0.8

    await memory.l1.add(important_task)

    # 填满 L1，触发驱逐
    for i in range(50):
        await memory.l1.add(Task(task_id=f"filler-{i}", action="test"))

    # 验证重要任务被提升到 L2
    l2_tasks = await memory.l2.retrieve(query=None, limit=100)
    assert important_task in l2_tasks
```

### 测试覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| layers/base.py | 100% |
| layers/circular.py | 95% |
| layers/priority.py | 95% |
| core.py | 90% |
| events/actions.py | 100% |
| events/event_bus.py | 90% |

---

## 📅 实施时间线（8-10周计划）

### Phase 1: 记忆系统重构（3周）- v0.4.2

**Week 1: 层级抽象实现**
- Day 1-2: Task 1 - 创建 MemoryLayer 抽象接口
- Day 3-5: Task 2 - 实现 CircularBufferLayer (L1)
- Day 6-7: Task 3 - 实现 PriorityQueueLayer (L2)

**Week 2: 协调器重构**
- Day 8-10: Task 4 - 重构 LoomMemory 为协调器
- Day 11-12: 集成测试和性能验证
- Day 13-14: Bug 修复和优化

**Week 3: 稳定化**
- Day 15-17: 完整测试套件
- Day 18-19: 文档更新
- Day 20-21: 发布 v0.4.2-alpha

**里程碑**: v0.4.2-alpha 发布

---

### Phase 2: 事件总线简化（2周）- v0.4.2

**Week 4: 类型安全实现**
- Day 22-23: Task 5 - 事件总线类型安全路由
- Day 24-25: 集成测试
- Day 26-28: Bug 修复和文档

**Week 5: 发布准备**
- Day 29-31: 最终测试和优化
- Day 32-33: 文档完善
- Day 34-35: 发布 v0.4.2 正式版

**里程碑**: v0.4.2 正式版发布

---

### Phase 3: 分形架构重新设计（3周）- v0.4.3

**Week 6: 分形记忆系统**
- Day 36-38: Task 6 - 实现分形记忆系统
- Day 39-41: Task 7 - 实现同步机制与冲突解决
- Day 42: 单元测试

**Week 7: 智能分配与集成**
- Day 43-44: Task 8 - 实现智能记忆分配策略
- Day 45-46: Task 9 - 集成分形架构到现有系统
- Day 47-49: 集成测试

**Week 8: 稳定化和发布**
- Day 50-52: 性能基准测试
- Day 53-54: Bug 修复和优化
- Day 55-56: 文档和示例

**里程碑**: v0.4.3-alpha 发布

---

## 📅 完全重构时间线（6周计划）

### Week 1: 架构设计和规划

**目标**: 完成架构设计，确定破坏性变更

- Day 1-2: 新架构设计文档
- Day 3-4: API 接口重新设计
- Day 5-6: 破坏性变更清单
- Day 7: 迁移工具设计

**里程碑**: 架构设计完成，开发计划确定

### Week 2-4: 核心系统重写（3周冲刺）

#### Week 2: 内存系统重构
- Day 8-10: 完全重写 MemoryLayer 抽象
- Day 11-12: 重新实现 L1-L4 层级
- Day 13-14: 新的查询系统

#### Week 3: 事件和协议重构  
- Day 15-17: 类型安全事件总线
- Day 18-19: 重新设计协议接口
- Day 20-21: 配置系统简化

#### Week 4: 集成和协调
- Day 22-24: 系统集成测试
- Day 25-26: 性能优化
- Day 27-28: 核心功能验证

**里程碑**: v0.5.0-rc.1 候选版本

### Week 5: 测试重写和验证

**目标**: 完全重写测试套件

- Day 29-30: 重写单元测试
- Day 31-32: 重写集成测试  
- Day 33-34: 性能基准测试
- Day 35: 破坏性变更验证

**里程碑**: v0.5.0-rc.2 稳定候选版本

### Week 6: 文档、工具和发布

**目标**: 完成迁移工具和文档

- Day 36-37: 重写 API 文档
- Day 38-39: 实现自动迁移工具
- Day 40-41: 迁移指南和示例
- Day 42: 正式发布准备

**里程碑**: v0.5.0 正式发布（破坏性变更）

---

## ✅ 完全重构验收标准

### 架构重构完整性
- [ ] 所有核心组件完全重写
- [ ] 零历史债务和兼容性代码
- [ ] 新架构设计完全实现
- [ ] 所有破坏性变更按计划执行

### 功能重新实现
- [ ] 内存系统（L1-L4）完全重写并正常工作
- [ ] 事件总线类型安全重构完成
- [ ] 协议接口统一重新设计
- [ ] 配置系统简化实现

### 性能目标（必须超越旧版本）
- [ ] L2 插入性能 < 10ms (1000次，相比旧版 >5000ms)
- [ ] 内存占用减少 > 30%（相比 v0.4.x）
- [ ] 启动时间减少 > 50%
- [ ] API 响应延迟减少 > 40%

### 代码质量（零妥协标准）
- [ ] 测试覆盖率 > 95%（所有新代码）
- [ ] mypy --strict 100% 通过
- [ ] ruff check --select ALL 零警告
- [ ] 代码复杂度 < 8 (McCabe)

### 测试重写完整性
- [ ] 100% 单元测试重写
- [ ] 100% 集成测试重写
- [ ] 性能基准测试套件
- [ ] 破坏性变更测试覆盖

### 文档和工具
- [ ] API 文档 100% 重写
- [ ] 迁移指南详细完整
- [ ] 自动迁移工具可用
- [ ] 示例代码全部更新
- [ ] 升级说明清晰

### 发布准备
- [ ] v0.5.0-rc.1/rc.2 测试通过
- [ ] 社区反馈收集和处理
- [ ] 破坏性变更公告发布
- [ ] EOL 计划明确传达

### 不可妥协项
- [ ] **绝对禁止**：任何向后兼容代码
- [ ] **绝对禁止**：任何性能回退
- [ ] **绝对禁止**：任何未测试的代码路径
- [ ] **绝对禁止**：任何类型检查失败

---

## 🎯 下一步行动

1. **审查计划** - 团队讨论和确认
2. **创建 Issues** - 在 GitHub 创建跟踪任务
3. **建立基准** - 运行性能测试记录当前指标
4. **开始实施** - 从 Task 1 开始

---

**计划作者**: Claude + @kongusen
**最后更新**: 2026-01-25
**状态**: 待审批

