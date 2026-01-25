# 分形架构重新设计方案

**版本**: v0.4.3-alpha
**创建日期**: 2026-01-25
**状态**: 设计阶段

## 📋 概述

本文档提出了 Loom Agent 分形架构的全面重新设计方案，旨在解决当前实现中的核心问题，并实现真正的分形能力。

### 设计目标

1. **真正的分形组合** - 支持多子节点的递归组合
2. **智能上下文管理** - 自动分配和共享上下文
3. **双向记忆流动** - 父子节点间的记忆可以双向传播
4. **O(1) 复杂度保证** - 每个节点的认知负载保持恒定
5. **资源高效管理** - 智能的节点生命周期管理

### 核心原则

```
1. 最小必要原则 - 子节点只接收完成任务所需的最小上下文
2. 分层可见性 - 不同层级的记忆有不同的可见范围
3. 按需加载 - 上下文和记忆按需传递，而非全量复制
4. 双向流动 - 信息可以从父到子，也可以从子到父
5. 冲突可解 - 提供多种策略解决记忆冲突
```

---

## 🎯 核心问题分析

### 问题 1: 空间熵（复杂度爆炸）

**问题描述**：
当任务复杂度增加时，单个 Agent 的上下文会线性增长，最终超出 LLM 的处理能力。

**具体表现**：

```
场景：构建一个复杂的 Web 应用
任务复杂度 = 前端 + 后端 + 数据库 + 部署 + 测试

单个 Agent 的上下文：
- 前端框架选择和配置 (500 tokens)
- 组件设计和实现 (2000 tokens)
- 后端 API 设计 (1000 tokens)
- 数据库 schema (800 tokens)
- 部署配置 (600 tokens)
- 测试策略 (400 tokens)
─────────────────────────────
总计：5300 tokens

❌ 问题：
1. 超出单次推理的最佳范围
2. LLM 难以同时关注所有细节
3. 容易遗漏重要信息
4. 推理质量下降
```

**分形架构的解决方案**：

通过递归分解，将复杂任务分散到多个节点，每个节点只关注自己的职责：

```
Root Agent (O(1) context)
├─ Frontend Agent (O(1) context)
│   ├─ UI Design Agent
│   └─ State Management Agent
├─ Backend Agent (O(1) context)
│   ├─ API Design Agent
│   └─ Database Agent
└─ DevOps Agent (O(1) context)

✅ 每个节点只关注自己的职责
✅ 复杂度被分散到多个节点
✅ 可以无限递归分解
```

### 问题 2: 上下文管理困境

**问题描述**：
在递归分解中，如何决定哪些上下文应该传递给子节点，哪些应该保留在父节点？

**当前实现的问题**：

```python
# 当前 NodeContainer 的实现
async def execute_task(self, task: Task) -> Task:
    if self.child:
        # 直接传递整个 task 对象
        result = await self.child.execute_task(task)
        return result
```

**困境**：

```
Parent Agent Context:
┌─────────────────────────────┐
│ - 项目整体目标              │
│ - 技术栈选择                │
│ - 架构设计原则              │
│ - 已完成的子任务列表        │
│ - 当前进度                  │
└─────────────────────────────┘
         │传递什么？
         ↓
Child Agent Context:
┌─────────────────────────────┐
│ ❓ 需要父节点的哪些信息？   │
│ ❓ 是否需要全局上下文？     │
│ ❓ 如何避免信息过载？       │
└─────────────────────────────┘
```

### 问题 3: 记忆隔离与共享的矛盾

**问题描述**：
在分形架构中，每个节点都有自己的记忆系统（L1-L4），但这带来了一个根本性的矛盾。

**核心矛盾**：

1. **完全隔离** → 子节点缺少必要的上下文，无法做出正确决策
2. **完全共享** → 违背了分形架构的初衷（O(1)复杂度），子节点被父节点的记忆淹没

**需要解决的问题**：

- 子节点应该继承父节点的哪些记忆？
- 子节点的新发现如何反馈给父节点？
- 如何避免记忆冲突？
- 如何保持记忆的一致性？

### 问题 4: 任务分解的智能性

**问题描述**：
当前实现依赖 LLM 通过工具调用来分解任务，但缺少框架层面的指导和约束。

**当前问题**：

```python
# LLM 自由分解，没有框架约束
Agent: "这个任务太复杂了，我需要创建子任务"
Tool Call: delegate(task="做所有事情")  # ❌ 分解不合理

# 缺少分解策略
- 按功能分解？
- 按阶段分解？
- 按依赖关系分解？
- 如何判断是否需要继续分解？
```

### 问题 5: 节点生命周期与资源管理

**问题描述**：
分形架构会动态创建大量子节点，但缺少清晰的生命周期管理策略。

**关键问题**：

1. 子节点何时创建？（懒加载 vs 预创建）
2. 子节点何时销毁？（任务完成后立即销毁 vs 保留复用）
3. 子节点的记忆如何处理？（销毁时丢失 vs 合并到父节点）
4. 如何避免资源泄漏？（大量节点占用内存）

---

## 💡 解决方案设计

### 方案 1: 分层记忆模型

**设计目标**：
建立清晰的记忆层次结构，每层有明确的可见性和访问权限，实现智能的记忆共享和隔离。

#### 1.1 记忆作用域定义

```python
from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional

class MemoryScope(Enum):
    """记忆作用域"""
    LOCAL = "local"          # 节点私有，不共享
    SHARED = "shared"        # 父子双向共享
    INHERITED = "inherited"  # 从父节点继承（只读）
    GLOBAL = "global"        # 全局共享（所有节点）

@dataclass
class MemoryAccessPolicy:
    """记忆访问策略"""
    scope: MemoryScope
    readable: bool           # 是否可读
    writable: bool           # 是否可写
    propagate_up: bool       # 是否向上传播（子→父）
    propagate_down: bool     # 是否向下传播（父→子）

# 预定义的访问策略
ACCESS_POLICIES = {
    MemoryScope.LOCAL: MemoryAccessPolicy(
        scope=MemoryScope.LOCAL,
        readable=True,
        writable=True,
        propagate_up=False,
        propagate_down=False
    ),
    MemoryScope.SHARED: MemoryAccessPolicy(
        scope=MemoryScope.SHARED,
        readable=True,
        writable=True,
        propagate_up=True,
        propagate_down=True
    ),
    MemoryScope.INHERITED: MemoryAccessPolicy(
        scope=MemoryScope.INHERITED,
        readable=True,
        writable=False,  # 只读
        propagate_up=False,
        propagate_down=True
    ),
    MemoryScope.GLOBAL: MemoryAccessPolicy(
        scope=MemoryScope.GLOBAL,
        readable=True,
        writable=True,
        propagate_up=True,
        propagate_down=True
    ),
}
```

#### 1.2 记忆条目结构

```python
@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str                          # 唯一标识
    content: Any                     # 记忆内容
    scope: MemoryScope               # 作用域
    version: int = 1                 # 版本号（用于冲突检测）
    created_by: str = ""             # 创建者节点ID
    updated_by: str = ""             # 最后更新者节点ID
    parent_version: Optional[int] = None  # 父版本号（用于追踪）
    metadata: dict[str, Any] = None  # 元数据

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
```

#### 1.3 分形记忆管理器

```python
from typing import Dict, List
from loom.memory.core import LoomMemory

class FractalMemory:
    """
    分形记忆管理器

    职责：
    - 管理不同作用域的记忆
    - 处理父子节点间的记忆共享
    - 提供统一的读写接口
    """

    def __init__(
        self,
        node_id: str,
        parent_memory: Optional["FractalMemory"] = None,
        base_memory: Optional[LoomMemory] = None
    ):
        self.node_id = node_id
        self.parent_memory = parent_memory

        # 使用 LoomMemory 作为底层存储
        self.base_memory = base_memory or LoomMemory(node_id=node_id)

        # 按作用域组织的记忆索引
        self._memory_by_scope: Dict[MemoryScope, Dict[str, MemoryEntry]] = {
            scope: {} for scope in MemoryScope
        }

    async def write(
        self,
        entry_id: str,
        content: Any,
        scope: MemoryScope = MemoryScope.LOCAL
    ) -> MemoryEntry:
        """
        写入记忆

        Args:
            entry_id: 记忆ID
            content: 记忆内容
            scope: 作用域

        Returns:
            创建的记忆条目
        """
        # 检查写权限
        policy = ACCESS_POLICIES[scope]
        if not policy.writable:
            raise PermissionError(f"Scope {scope} is read-only")

        # 创建记忆条目
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            scope=scope,
            created_by=self.node_id,
            updated_by=self.node_id
        )

        # 存储到对应作用域
        self._memory_by_scope[scope][entry_id] = entry

        return entry

    async def read(
        self,
        entry_id: str,
        search_scopes: Optional[List[MemoryScope]] = None
    ) -> Optional[MemoryEntry]:
        """
        读取记忆

        Args:
            entry_id: 记忆ID
            search_scopes: 搜索的作用域列表（None表示搜索所有）

        Returns:
            记忆条目，如果不存在返回None
        """
        if search_scopes is None:
            search_scopes = list(MemoryScope)

        # 按优先级搜索：LOCAL > SHARED > INHERITED > GLOBAL
        for scope in search_scopes:
            if entry_id in self._memory_by_scope[scope]:
                return self._memory_by_scope[scope][entry_id]

        # 如果是INHERITED作用域，尝试从父节点读取
        if MemoryScope.INHERITED in search_scopes and self.parent_memory:
            parent_entry = await self.parent_memory.read(
                entry_id,
                search_scopes=[MemoryScope.SHARED, MemoryScope.GLOBAL]
            )
            if parent_entry:
                # 创建只读副本
                inherited_entry = MemoryEntry(
                    id=parent_entry.id,
                    content=parent_entry.content,
                    scope=MemoryScope.INHERITED,
                    version=parent_entry.version,
                    created_by=parent_entry.created_by,
                    updated_by=parent_entry.updated_by,
                    parent_version=parent_entry.version
                )
                self._memory_by_scope[MemoryScope.INHERITED][entry_id] = inherited_entry
                return inherited_entry

        return None

    async def list_by_scope(self, scope: MemoryScope) -> List[MemoryEntry]:
        """列出指定作用域的所有记忆"""
        return list(self._memory_by_scope[scope].values())
```

---

### 方案 2: 同步机制与冲突解决

**设计目标**：
实现父子节点间的记忆同步，使用乐观锁检测冲突，提供多种冲突解决策略。

#### 2.1 版本控制与乐观锁

```python
from typing import Tuple

class MemorySyncManager:
    """记忆同步管理器"""

    def __init__(self, memory: FractalMemory):
        self.memory = memory

    async def write_with_version_check(
        self,
        entry: MemoryEntry,
        expected_version: int
    ) -> Tuple[bool, Optional[str]]:
        """
        带版本检查的写入（乐观锁）

        Args:
            entry: 要写入的记忆条目
            expected_version: 期望的当前版本号

        Returns:
            (成功标志, 错误信息)
        """
        # 读取当前版本
        current = await self.memory.read(entry.id)

        # 版本冲突检测
        if current and current.version != expected_version:
            return False, f"Version conflict: expected {expected_version}, got {current.version}"

        # 更新版本号
        entry.version = expected_version + 1
        entry.updated_by = self.memory.node_id

        # 写入
        await self.memory.write(entry.id, entry.content, entry.scope)

        return True, None

    async def sync_from_parent(self) -> int:
        """
        从父节点同步SHARED记忆

        Returns:
            同步的记忆条目数量
        """
        if not self.memory.parent_memory:
            return 0

        synced_count = 0

        # 获取父节点的SHARED记忆
        parent_shared = await self.memory.parent_memory.list_by_scope(
            MemoryScope.SHARED
        )

        for parent_entry in parent_shared:
            # 检查本地是否已有
            local_entry = await self.memory.read(
                parent_entry.id,
                search_scopes=[MemoryScope.SHARED]
            )

            if not local_entry:
                # 本地没有，直接复制
                await self.memory.write(
                    parent_entry.id,
                    parent_entry.content,
                    MemoryScope.SHARED
                )
                synced_count += 1
            elif local_entry.version < parent_entry.version:
                # 本地版本较旧，需要合并
                await self._handle_conflict(local_entry, parent_entry)
                synced_count += 1

        return synced_count
```

#### 2.2 冲突解决策略

```python
from abc import ABC, abstractmethod

class ConflictResolver(ABC):
    """冲突解决器抽象接口"""

    @abstractmethod
    async def resolve(
        self,
        parent_entry: MemoryEntry,
        child_entry: MemoryEntry
    ) -> MemoryEntry:
        """
        解决冲突

        Args:
            parent_entry: 父节点的记忆条目
            child_entry: 子节点的记忆条目

        Returns:
            解决后的记忆条目
        """
        pass

class ParentWinsResolver(ConflictResolver):
    """父节点优先策略"""

    async def resolve(
        self,
        parent_entry: MemoryEntry,
        child_entry: MemoryEntry
    ) -> MemoryEntry:
        """父节点的版本覆盖子节点"""
        return parent_entry

class ChildWinsResolver(ConflictResolver):
    """子节点优先策略"""

    async def resolve(
        self,
        parent_entry: MemoryEntry,
        child_entry: MemoryEntry
    ) -> MemoryEntry:
        """子节点的版本覆盖父节点"""
        return child_entry

class MergeResolver(ConflictResolver):
    """合并策略"""

    async def resolve(
        self,
        parent_entry: MemoryEntry,
        child_entry: MemoryEntry
    ) -> MemoryEntry:
        """智能合并两个版本"""
        # 如果内容是字典，进行深度合并
        if isinstance(parent_entry.content, dict) and isinstance(child_entry.content, dict):
            merged_content = self._merge_dicts(
                parent_entry.content,
                child_entry.content
            )
        else:
            # 其他类型，使用子节点版本
            merged_content = child_entry.content

        # 创建新的合并版本
        merged_entry = MemoryEntry(
            id=parent_entry.id,
            content=merged_content,
            scope=parent_entry.scope,
            version=max(parent_entry.version, child_entry.version) + 1,
            created_by=parent_entry.created_by,
            updated_by=f"{parent_entry.updated_by}+{child_entry.updated_by}"
        )

        return merged_entry

    def _merge_dicts(self, parent_dict: dict, child_dict: dict) -> dict:
        """深度合并字典"""
        result = parent_dict.copy()
        for key, value in child_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value
        return result
```

---

### 方案 3: 变更传播机制

**设计目标**：
实现父子节点间的记忆变更自动传播，避免循环传播，确保最终一致性。

#### 3.1 变更事件定义

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class MemoryChangeEvent:
    """记忆变更事件"""
    entry_id: str                    # 变更的记忆ID
    old_version: int                 # 旧版本号
    new_version: int                 # 新版本号
    changed_by: str                  # 变更者节点ID
    scope: MemoryScope               # 作用域
    propagation_path: List[str] = field(default_factory=list)  # 传播路径

class MemoryChangeListener(ABC):
    """记忆变更监听器"""

    @abstractmethod
    async def on_memory_changed(self, event: MemoryChangeEvent) -> None:
        """处理记忆变更事件"""
        pass
```

#### 3.2 传播管理器

```python
class MemoryPropagationManager:
    """记忆传播管理器"""

    def __init__(self):
        # 节点ID -> 监听器列表
        self._listeners: Dict[str, List[MemoryChangeListener]] = defaultdict(list)

    def register_listener(
        self,
        node_id: str,
        listener: MemoryChangeListener
    ) -> None:
        """注册监听器"""
        self._listeners[node_id].append(listener)

    async def propagate_change(
        self,
        event: MemoryChangeEvent,
        target_nodes: List[str]
    ) -> None:
        """
        传播变更到目标节点

        Args:
            event: 变更事件
            target_nodes: 目标节点ID列表
        """
        # 防止循环传播
        if event.changed_by in event.propagation_path:
            return

        # 添加到传播路径
        event.propagation_path.append(event.changed_by)

        # 通知所有目标节点
        for node_id in target_nodes:
            if node_id in self._listeners:
                for listener in self._listeners[node_id]:
                    await listener.on_memory_changed(event)
```

---

### 方案 4: 智能记忆分配策略

**设计目标**：
根据任务特征自动分析和分配最相关的记忆给子节点，避免信息过载，保持O(1)复杂度。

#### 4.1 任务特征分析

```python
from typing import Set
import re

@dataclass
class TaskFeatures:
    """任务特征"""
    keywords: Set[str]              # 关键词集合
    action_type: str                # 动作类型
    complexity: float               # 复杂度评分 (0-1)
    required_context: Set[str]      # 需要的上下文类型

class TaskAnalyzer:
    """任务分析器"""

    def analyze(self, task: Task) -> TaskFeatures:
        """
        分析任务特征

        Args:
            task: 任务对象

        Returns:
            任务特征
        """
        # 提取关键词
        keywords = self._extract_keywords(task.action)

        # 判断动作类型
        action_type = self._classify_action(task.action)

        # 评估复杂度
        complexity = self._estimate_complexity(task)

        # 推断需要的上下文
        required_context = self._infer_required_context(task, keywords)

        return TaskFeatures(
            keywords=keywords,
            action_type=action_type,
            complexity=complexity,
            required_context=required_context
        )

    def _extract_keywords(self, text: str) -> Set[str]:
        """提取关键词"""
        # 简单实现：分词 + 停用词过滤
        words = re.findall(r'\w+', text.lower())
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at'}
        return {w for w in words if w not in stopwords and len(w) > 2}

    def _classify_action(self, action: str) -> str:
        """分类动作类型"""
        action_lower = action.lower()
        if any(kw in action_lower for kw in ['create', 'build', 'implement']):
            return 'creation'
        elif any(kw in action_lower for kw in ['fix', 'debug', 'resolve']):
            return 'debugging'
        elif any(kw in action_lower for kw in ['analyze', 'review', 'check']):
            return 'analysis'
        else:
            return 'general'

    def _estimate_complexity(self, task: Task) -> float:
        """评估任务复杂度"""
        # 基于多个因素评估
        factors = []

        # 描述长度
        desc_length = len(task.action)
        factors.append(min(desc_length / 200, 1.0))

        # 子任务数量
        if hasattr(task, 'subtasks'):
            factors.append(min(len(task.subtasks) / 10, 1.0))

        # 依赖数量
        if hasattr(task, 'dependencies'):
            factors.append(min(len(task.dependencies) / 5, 1.0))

        return sum(factors) / len(factors) if factors else 0.5
```

#### 4.2 智能分配策略

```python
class SmartAllocationStrategy:
    """智能记忆分配策略"""

    def __init__(
        self,
        max_inherited_memories: int = 10,
        analyzer: Optional[TaskAnalyzer] = None
    ):
        self.max_inherited_memories = max_inherited_memories
        self.analyzer = analyzer or TaskAnalyzer()

    async def allocate(
        self,
        parent_memory: FractalMemory,
        child_task: Task
    ) -> Dict[MemoryScope, List[MemoryEntry]]:
        """
        为子节点分配记忆

        Args:
            parent_memory: 父节点的记忆
            child_task: 子任务

        Returns:
            按作用域组织的记忆条目
        """
        # 分析任务特征
        features = self.analyzer.analyze(child_task)

        # 从父节点检索相关记忆
        relevant_entries = await self._retrieve_relevant_memories(
            parent_memory,
            features
        )

        # 按相关性排序
        ranked_entries = self._rank_by_relevance(relevant_entries, features)

        # 选择前N个最相关的
        selected = ranked_entries[:self.max_inherited_memories]

        return {
            MemoryScope.INHERITED: selected
        }

    async def _retrieve_relevant_memories(
        self,
        parent_memory: FractalMemory,
        features: TaskFeatures
    ) -> List[MemoryEntry]:
        """检索相关记忆"""
        # 获取父节点的SHARED和GLOBAL记忆
        shared_memories = await parent_memory.list_by_scope(MemoryScope.SHARED)
        global_memories = await parent_memory.list_by_scope(MemoryScope.GLOBAL)

        all_memories = shared_memories + global_memories

        # 过滤相关记忆
        relevant = []
        for entry in all_memories:
            if self._is_relevant(entry, features):
                relevant.append(entry)

        return relevant

    def _is_relevant(self, entry: MemoryEntry, features: TaskFeatures) -> bool:
        """判断记忆是否相关"""
        # 简单实现：检查关键词重叠
        if not isinstance(entry.content, str):
            return False

        entry_keywords = set(re.findall(r'\w+', entry.content.lower()))
        overlap = features.keywords & entry_keywords

        # 至少有2个关键词重叠
        return len(overlap) >= 2

    def _rank_by_relevance(
        self,
        entries: List[MemoryEntry],
        features: TaskFeatures
    ) -> List[MemoryEntry]:
        """按相关性排序"""
        scored_entries = []

        for entry in entries:
            score = self._calculate_relevance_score(entry, features)
            scored_entries.append((score, entry))

        # 按分数降序排序
        scored_entries.sort(key=lambda x: x[0], reverse=True)

        return [entry for _, entry in scored_entries]

    def _calculate_relevance_score(
        self,
        entry: MemoryEntry,
        features: TaskFeatures
    ) -> float:
        """计算相关性分数"""
        score = 0.0

        if not isinstance(entry.content, str):
            return score

        entry_keywords = set(re.findall(r'\w+', entry.content.lower()))
        overlap = features.keywords & entry_keywords

        # 关键词重叠度
        if features.keywords:
            score += len(overlap) / len(features.keywords) * 0.6

        # 版本新鲜度（版本越新，分数越高）
        score += min(entry.version / 10, 0.2)

        # 作用域权重（GLOBAL > SHARED）
        if entry.scope == MemoryScope.GLOBAL:
            score += 0.2

        return score
```

---

## 🏗️ 完整架构设计

### 5.1 组件交互图

```
┌─────────────────────────────────────────────────────────────┐
│                      Fractal Node                            │
│                                                               │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │   Agent      │────────▶│ FractalMemory│                  │
│  │   (LLM)      │         │              │                  │
│  └──────────────┘         └──────┬───────┘                  │
│         │                        │                           │
│         │                        │                           │
│         ▼                        ▼                           │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │ Task         │         │ Memory       │                  │
│  │ Decomposer   │         │ Sync Manager │                  │
│  └──────┬───────┘         └──────┬───────┘                  │
│         │                        │                           │
│         │                        │                           │
└─────────┼────────────────────────┼───────────────────────────┘
          │                        │
          │ Create Child           │ Sync Memory
          ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Child Fractal Node                        │
│                                                               │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │   Agent      │────────▶│ FractalMemory│                  │
│  │   (LLM)      │         │ (Inherited)  │                  │
│  └──────────────┘         └──────────────┘                  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 5.2 核心组件职责

**FractalNode（分形节点）**
- 管理节点的生命周期
- 协调Agent和Memory的交互
- 处理任务分解和子节点创建
- 实现O(1)复杂度保证

**FractalMemory（分形记忆）**
- 管理四种作用域的记忆
- 提供统一的读写接口
- 处理父子节点间的记忆继承

**MemorySyncManager（同步管理器）**
- 实现乐观锁版本控制
- 处理父子节点间的记忆同步
- 检测和解决冲突

**SmartAllocationStrategy（智能分配策略）**
- 分析任务特征
- 选择最相关的记忆分配给子节点
- 保持O(1)复杂度

---

## 📝 使用示例

### 示例 1: 创建分形节点并分配记忆

```python
from loom.fractal import FractalNode
from loom.protocol import Task

# 创建父节点
parent_node = FractalNode(
    node_id="parent",
    agent_card=AgentCard(name="Parent Agent")
)

# 父节点添加一些记忆
await parent_node.memory.write(
    "project_goal",
    "Build a web application with authentication",
    scope=MemoryScope.SHARED
)

await parent_node.memory.write(
    "tech_stack",
    "React + FastAPI + PostgreSQL",
    scope=MemoryScope.GLOBAL
)

# 创建子任务
child_task = Task(
    task_id="child-1",
    action="Implement user authentication with JWT"
)

# 创建子节点（自动分配相关记忆）
child_node = await parent_node.create_child(
    task=child_task,
    allocation_strategy=SmartAllocationStrategy(max_inherited_memories=5)
)

# 子节点可以读取继承的记忆
project_goal = await child_node.memory.read("project_goal")
print(f"Child inherited: {project_goal.content}")
```

### 示例 2: 子节点更新共享记忆

```python
# 子节点完成任务后，更新共享记忆
await child_node.memory.write(
    "auth_implementation",
    "JWT authentication implemented with refresh tokens",
    scope=MemoryScope.SHARED
)

# 同步到父节点
sync_manager = MemorySyncManager(parent_node.memory)
synced_count = await sync_manager.sync_from_child(child_node.memory)

print(f"Synced {synced_count} memories from child to parent")

# 父节点现在可以读取子节点的发现
auth_info = await parent_node.memory.read("auth_implementation")
print(f"Parent learned: {auth_info.content}")
```

---

## 🗓️ 实施路线图

### Phase 1: 基础设施（2周）

**目标**: 实现核心的记忆作用域和分配机制

**任务**:
1. 实现 `MemoryScope` 枚举和 `MemoryAccessPolicy`
2. 实现 `MemoryEntry` 数据结构
3. 实现 `FractalMemory` 基础类
4. 编写单元测试（覆盖率 > 90%）

**交付物**:
- `loom/fractal/memory.py` - 核心记忆管理
- `tests/fractal/test_memory.py` - 测试套件

### Phase 2: 同步机制（2周）

**目标**: 实现版本控制和冲突解决

**任务**:
1. 实现 `MemorySyncManager` 类
2. 实现三种冲突解决策略
3. 实现变更传播机制
4. 集成测试

**交付物**:
- `loom/fractal/sync.py` - 同步管理器
- `loom/fractal/resolvers.py` - 冲突解决器
- `tests/fractal/test_sync.py` - 同步测试

### Phase 3: 智能分配（2周）

**目标**: 实现任务分析和智能记忆分配

**任务**:
1. 实现 `TaskAnalyzer` 类
2. 实现 `SmartAllocationStrategy` 类
3. 性能优化和测试
4. 文档和示例

**交付物**:
- `loom/fractal/allocation.py` - 分配策略
- `docs/examples/fractal-memory.md` - 使用示例

### Phase 4: 集成和优化（1周）

**目标**: 集成到现有系统，性能优化

**任务**:
1. 重构 `NodeContainer` 使用新的记忆系统
2. 性能基准测试
3. 文档更新
4. 发布 v0.4.3-alpha

---

## 🧪 测试策略

### 单元测试

**记忆作用域测试**
- 测试四种作用域的读写权限
- 测试作用域隔离性
- 测试继承机制

**同步机制测试**
- 测试版本冲突检测
- 测试三种冲突解决策略
- 测试循环传播防护

**智能分配测试**
- 测试任务特征提取
- 测试相关性评分算法
- 测试分配数量限制

### 集成测试

**父子节点协作测试**
- 测试记忆继承流程
- 测试双向同步机制
- 测试多层级嵌套场景

**性能测试**
- 测试O(1)复杂度保证
- 测试大规模记忆分配性能
- 测试并发访问场景

### 测试覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| memory.py | 95% |
| sync.py | 90% |
| allocation.py | 90% |
| resolvers.py | 95% |

---

## 📌 总结

本文档提出了 Loom Agent 分形架构的全面重新设计方案，核心创新包括：

### 关键设计决策

1. **四层记忆作用域** - LOCAL、SHARED、INHERITED、GLOBAL，实现精确的记忆隔离和共享
2. **双向记忆流动** - 子节点可以修改父节点的SHARED记忆，实现真正的协作
3. **乐观锁同步** - 基于版本号的冲突检测，支持多种冲突解决策略
4. **智能记忆分配** - 基于任务特征自动选择最相关的记忆，保持O(1)复杂度
5. **事件驱动传播** - 防止循环传播，确保最终一致性

### 预期收益

**架构层面**:
- ✅ 真正的分形能力 - 支持无限递归分解
- ✅ O(1)复杂度保证 - 每个节点的认知负载恒定
- ✅ 清晰的职责分离 - 每个组件职责明确

**性能层面**:
- ✅ 避免信息过载 - 智能分配最相关的记忆
- ✅ 高效的同步机制 - 乐观锁减少锁竞争
- ✅ 可扩展性 - 支持大规模分形节点网络

**开发体验**:
- ✅ 简单易用的API - 统一的读写接口
- ✅ 灵活的策略系统 - 可插拔的冲突解决和分配策略
- ✅ 完善的测试覆盖 - 高质量的代码保证

### 下一步行动

1. **审查和讨论** - 团队评审设计方案
2. **原型验证** - 实现核心组件的原型
3. **性能测试** - 验证O(1)复杂度保证
4. **开始实施** - 按照路线图执行 Phase 1

---

**文档作者**: Claude + @kongusen
**创建日期**: 2026-01-25
**最后更新**: 2026-01-25
**状态**: 设计完成，待审批

---

## 🔗 与现有架构的整合

### 整合概述

本分形架构设计需要与以下现有设计深度整合：

1. **自主Agent设计**（autonomous-agent-design.md）- 四范式自动能力
2. **上下文管理器设计**（context-manager-design.md）- TaskContextManager
3. **Agent改进方案**（agent-improvements-summary.md）- "Agent is just a for loop"
4. **系统优化计划**（system-optimization-plan.md）- LoomMemory (L1-L4)

**核心原则**：分形架构不是独立系统，而是现有架构的自然扩展。

---

## 🎯 整合方案 1: 自主委派机制

### 问题：如何创建子节点？

**错误方案**（违背自主性）：
```python
# ❌ 显式调用委派方法
child_node = await parent_node.create_child(task)
result = await child_node.execute_task(subtask)
```

**正确方案**（自主决策）：
```python
# ✅ LLM通过meta-tool自主决策委派
# Agent循环中，LLM自动调用delegate_task工具

# 系统提示词中包含：
"""
你可以使用以下能力：
- delegate_task: 当任务复杂或需要专业能力时，委派给子Agent
"""

# LLM自主决策：
response = await llm.chat(messages, tools=[
    # 普通工具
    {"name": "search", ...},
    {"name": "calculate", ...},

    # 元工具（四范式能力）
    {"name": "create_plan", "description": "为复杂任务创建执行计划"},
    {"name": "delegate_task", "description": "委派子任务给专门的Agent"},
])

# 当LLM调用delegate_task时：
if tool_call.name == "delegate_task":
    # 框架自动创建子节点并执行
    child_result = await self._auto_delegate(tool_call.args)
```

### 实现：delegate_task元工具

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
        context_hints: 上下文提示（哪些信息需要传递）

    Returns:
        子任务执行结果
    """
    # 由Agent._auto_delegate()实现
    # 1. 创建子节点
    # 2. 使用SmartAllocationStrategy分配记忆
    # 3. 执行子任务
    # 4. 同步结果回父节点
    pass
```

### Agent中的自动委派实现

```python
class Agent(BaseNode):
    async def _execute_impl(self, task: Task) -> Task:
        """最简Agent循环 + 自主委派"""

        accumulated_messages = []

        for iteration in range(max_iterations):
            # 1. 构建上下文（使用TaskContextManager）
            messages = await self.context_manager.build_context(
                current_task=task,
                additional_messages=accumulated_messages,
            )

            # 2. 调用LLM（包含meta-tools）
            response = await self.llm_provider.chat(
                messages,
                tools=self._get_all_tools()  # 包含delegate_task
            )

            # 3. 处理工具调用
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    if tool_call.name == "delegate_task":
                        # 自动触发委派能力
                        result = await self._auto_delegate(tool_call.args, task)
                    elif tool_call.name == "create_plan":
                        # 自动触发规划能力
                        result = await self._auto_plan(tool_call.args, task)
                    else:
                        # 普通工具调用
                        result = await self._execute_tool(tool_call)

                    accumulated_messages.append({
                        "role": "tool",
                        "content": result,
                        "tool_name": tool_call.name,
                    })

        return task

    async def _auto_delegate(
        self,
        args: dict,
        parent_task: Task
    ) -> str:
        """
        自动委派实现（框架内部）

        这里整合分形架构的智能记忆分配
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

        # 2. 创建子节点（使用FractalMemory）
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

**关键点**：
- ✅ LLM自主决策何时委派
- ✅ 框架自动处理子节点创建
- ✅ 保持"Agent is just a for loop"哲学
- ✅ 分形能力通过meta-tool自然触发

---

## 🎯 整合方案 2: TaskContextManager集成

### 问题：如何智能传递上下文？

**核心挑战**：
- 子节点需要哪些父节点的上下文？
- 如何避免传递过多信息导致认知过载？
- 如何利用LLM的context_hints参数？

### 解决方案：使用TaskContextManager

**TaskContextManager的职责**（来自context-manager-design.md）：
1. 从多个源收集上下文（LoomMemory L1-L4, EventBus）
2. 智能去重和排序
3. Token感知的压缩和优化
4. 转换为LLM消息格式

### 实现：_create_child_node方法

```python
class Agent(BaseNode):
    async def _create_child_node(
        self,
        subtask: Task,
        context_hints: list[str]
    ) -> "Agent":
        """
        创建子节点并智能分配上下文

        整合点：
        - 使用TaskContextManager选择相关上下文
        - 使用SmartAllocationStrategy分配记忆
        - 使用FractalMemory实现父子记忆共享
        """
        # 1. 创建子节点的FractalMemory（继承父节点记忆）
        child_memory = FractalMemory(
            node_id=subtask.task_id,
            parent_memory=self.memory,  # 建立父子关系
            base_memory=LoomMemory(node_id=subtask.task_id)
        )

        # 2. 使用SmartAllocationStrategy分配相关记忆
        allocation_strategy = SmartAllocationStrategy(
            max_inherited_memories=10
        )

        allocated_memories = await allocation_strategy.allocate(
            parent_memory=self.memory,
            child_task=subtask,
            context_hints=context_hints  # LLM提供的提示
        )

        # 3. 将分配的记忆写入子节点（INHERITED作用域）
        for scope, entries in allocated_memories.items():
            for entry in entries:
                await child_memory.write(
                    entry.id,
                    entry.content,
                    scope=scope
                )

        # 4. 创建子节点的TaskContextManager
        child_context_manager = TaskContextManager(
            memory=child_memory.base_memory,  # 使用底层LoomMemory
            event_bus=self.event_bus,
            max_context_tokens=4000  # 子节点的上下文限制
        )

        # 5. 创建子Agent
        child_agent = Agent(
            node_id=subtask.task_id,
            agent_card=self.agent_card,  # 继承能力
            llm_provider=self.llm_provider,
            context_manager=child_context_manager,
            memory=child_memory,
            tools=self.tools  # 继承工具
        )

        return child_agent
```

### context_hints的使用

**LLM在调用delegate_task时可以提供提示**：

```python
# LLM的工具调用示例
{
    "name": "delegate_task",
    "arguments": {
        "subtask_description": "实现用户认证的JWT token生成",
        "required_capabilities": ["crypto", "jwt"],
        "context_hints": [
            "project_goal",      # 需要知道项目整体目标
            "tech_stack",        # 需要知道技术栈选择
            "auth_requirements"  # 需要知道认证需求
        ]
    }
}
```

**SmartAllocationStrategy使用这些提示**：

```python
class SmartAllocationStrategy:
    async def allocate(
        self,
        parent_memory: FractalMemory,
        child_task: Task,
        context_hints: list[str] | None = None
    ) -> Dict[MemoryScope, List[MemoryEntry]]:
        """
        智能分配记忆，优先考虑context_hints
        """
        # 1. 如果有context_hints，优先检索这些记忆
        if context_hints:
            selected = []
            for hint in context_hints:
                entry = await parent_memory.read(
                    hint,
                    search_scopes=[MemoryScope.SHARED, MemoryScope.GLOBAL]
                )
                if entry:
                    selected.append(entry)

            # 2. 如果hints不足，使用任务特征分析补充
            if len(selected) < self.max_inherited_memories:
                features = self.analyzer.analyze(child_task)
                additional = await self._retrieve_relevant_memories(
                    parent_memory,
                    features
                )
                selected.extend(additional)

            return {
                MemoryScope.INHERITED: selected[:self.max_inherited_memories]
            }

        # 3. 无hints时，完全依赖任务特征分析
        features = self.analyzer.analyze(child_task)
        relevant = await self._retrieve_relevant_memories(
            parent_memory,
            features
        )

        return {
            MemoryScope.INHERITED: relevant[:self.max_inherited_memories]
        }
```

**关键点**：
- ✅ TaskContextManager负责构建LLM上下文
- ✅ SmartAllocationStrategy负责选择相关记忆
- ✅ context_hints让LLM参与上下文选择决策
- ✅ 保持O(1)复杂度（最多N个记忆）

---

## 🎯 整合方案 3: LoomMemory (L1-L4) 集成

### 问题：FractalMemory如何与现有记忆系统协作？

**核心挑战**：
- FractalMemory的四种作用域如何映射到L1-L4层级？
- 如何避免重复实现记忆存储？
- 如何利用现有的优化（堆、向量检索等）？

### 解决方案：FractalMemory作为LoomMemory的上层抽象

**架构关系**：

```
┌─────────────────────────────────────────────┐
│         FractalMemory (作用域管理)           │
│  - LOCAL, SHARED, INHERITED, GLOBAL         │
│  - 版本控制和冲突解决                        │
│  - 父子节点记忆同步                          │
└─────────────────┬───────────────────────────┘
                  │ 使用
                  ▼
┌─────────────────────────────────────────────┐
│         LoomMemory (层级存储)                │
│  - L1: CircularBufferLayer (最近任务)       │
│  - L2: PriorityQueueLayer (重要任务)        │
│  - L3: SummaryStorageLayer (摘要)           │
│  - L4: VectorStorageLayer (长期知识)        │
└─────────────────────────────────────────────┘
```

### 实现：FractalMemory使用LoomMemory作为底层存储

```python
class FractalMemory:
    """
    分形记忆管理器

    职责：
    - 管理四种作用域（LOCAL, SHARED, INHERITED, GLOBAL）
    - 处理父子节点间的记忆同步
    - 使用LoomMemory作为底层存储
    """

    def __init__(
        self,
        node_id: str,
        parent_memory: Optional["FractalMemory"] = None,
        base_memory: Optional[LoomMemory] = None
    ):
        self.node_id = node_id
        self.parent_memory = parent_memory

        # 使用LoomMemory作为底层存储
        self.base_memory = base_memory or LoomMemory(node_id=node_id)

        # 按作用域组织的记忆索引（轻量级，只存储元数据）
        self._memory_by_scope: Dict[MemoryScope, Dict[str, MemoryEntry]] = {
            scope: {} for scope in MemoryScope
        }

    async def write(
        self,
        entry_id: str,
        content: Any,
        scope: MemoryScope = MemoryScope.LOCAL
    ) -> MemoryEntry:
        """
        写入记忆

        策略：
        - 元数据存储在_memory_by_scope（作用域管理）
        - 实际内容存储在base_memory（利用L1-L4优化）
        """
        # 1. 创建记忆条目（元数据）
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            scope=scope,
            created_by=self.node_id,
            updated_by=self.node_id
        )

        # 2. 存储元数据到作用域索引
        self._memory_by_scope[scope][entry_id] = entry

        # 3. 根据作用域决定存储到哪个层级
        if isinstance(content, Task):
            # Task对象存储到L1或L2
            importance = content.metadata.get("importance", 0.5)
            tier = MemoryTier.L2_WORKING if importance > 0.6 else MemoryTier.L1_RAW_IO
            await self.base_memory.add_task(content, tier=tier)

        elif isinstance(content, str):
            # 字符串内容存储到L4（向量检索）
            fact = Fact(
                fact_id=entry_id,
                content=content,
                source=self.node_id,
                metadata={"scope": scope.value}
            )
            await self.base_memory.add_fact(fact)

        return entry

    async def read(
        self,
        entry_id: str,
        search_scopes: Optional[List[MemoryScope]] = None
    ) -> Optional[MemoryEntry]:
        """
        读取记忆

        策略：
        - 先查询作用域索引（快速定位）
        - 如果需要，从base_memory检索完整内容
        - 支持从父节点继承（INHERITED作用域）
        """
        if search_scopes is None:
            search_scopes = list(MemoryScope)

        # 1. 按优先级搜索本地作用域
        for scope in search_scopes:
            if entry_id in self._memory_by_scope[scope]:
                return self._memory_by_scope[scope][entry_id]

        # 2. 如果是INHERITED作用域，尝试从父节点读取
        if MemoryScope.INHERITED in search_scopes and self.parent_memory:
            parent_entry = await self.parent_memory.read(
                entry_id,
                search_scopes=[MemoryScope.SHARED, MemoryScope.GLOBAL]
            )
            if parent_entry:
                # 创建只读副本
                inherited_entry = MemoryEntry(
                    id=parent_entry.id,
                    content=parent_entry.content,
                    scope=MemoryScope.INHERITED,
                    version=parent_entry.version,
                    created_by=parent_entry.created_by,
                    updated_by=parent_entry.updated_by,
                    parent_version=parent_entry.version
                )
                # 缓存到本地
                self._memory_by_scope[MemoryScope.INHERITED][entry_id] = inherited_entry
                return inherited_entry

        return None

    async def query(
        self,
        query_text: str,
        scopes: Optional[List[MemoryScope]] = None,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        跨作用域查询记忆

        利用LoomMemory的L4向量检索能力
        """
        # 1. 使用base_memory的向量检索
        facts = await self.base_memory.query(
            query_text,
            tiers=[MemoryTier.L4_GLOBAL],
            limit=limit * 2  # 多检索一些，后续过滤
        )

        # 2. 过滤符合作用域的结果
        if scopes is None:
            scopes = list(MemoryScope)

        results = []
        for fact in facts:
            scope_str = fact.metadata.get("scope")
            if scope_str:
                scope = MemoryScope(scope_str)
                if scope in scopes:
                    # 从作用域索引获取完整的MemoryEntry
                    entry = self._memory_by_scope[scope].get(fact.fact_id)
                    if entry:
                        results.append(entry)

        return results[:limit]
```

### 作用域到层级的映射策略

**映射规则**：

| 作用域 | 存储层级 | 原因 |
|--------|---------|------|
| LOCAL | L1 (CircularBuffer) | 节点私有，短期使用，自动驱逐 |
| SHARED | L2 (PriorityQueue) | 父子共享，按重要性保留 |
| INHERITED | L2 (PriorityQueue) | 从父节点继承，重要性高 |
| GLOBAL | L4 (VectorStore) | 全局知识，长期保存，向量检索 |

**关键点**：
- ✅ FractalMemory复用LoomMemory的存储优化
- ✅ 作用域管理在上层，存储优化在下层
- ✅ 避免重复实现堆、向量检索等复杂逻辑
- ✅ 保持架构清晰，职责分离

---

## 🎯 整合方案 4: 完整执行流程

### 端到端示例：构建Web应用的认证功能

让我们通过一个完整的例子，展示所有组件如何协同工作。

**场景**：父Agent接收任务"构建Web应用"，决定委派"实现用户认证"给子Agent。

### 步骤 1: 父Agent接收任务

```python
# 用户提交任务
root_task = Task(
    task_id="root-1",
    action="execute",
    parameters={
        "content": "构建一个Web应用，包含用户认证、数据管理和API接口"
    }
)

# 父Agent开始执行
parent_agent = Agent(
    node_id="parent",
    agent_card=AgentCard(name="Web App Builder"),
    llm_provider=llm_provider,
    context_manager=TaskContextManager(...),
    memory=FractalMemory(node_id="parent"),
    tools=[...]
)

result = await parent_agent.execute_task(root_task)
```

### 步骤 2: 父Agent的执行循环（"Agent is just a for loop"）

```python
class Agent(BaseNode):
    async def _execute_impl(self, task: Task) -> Task:
        """最简Agent循环"""

        accumulated_messages = []

        for iteration in range(max_iterations):
            # 1. 过滤ephemeral消息（来自agent-improvements-summary.md）
            filtered = self._filter_ephemeral_messages(accumulated_messages)

            # 2. 使用TaskContextManager构建上下文
            messages = await self.context_manager.build_context(
                current_task=task,
                additional_messages=filtered,
            )

            # 3. 调用LLM（包含meta-tools）
            response = await self.llm_provider.chat(
                messages,
                tools=self._get_all_tools()  # 包含delegate_task
            )

            # 4. 处理响应
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    if tool_call.name == "delegate_task":
                        # LLM自主决策委派！
                        result = await self._auto_delegate(tool_call.args, task)
                    else:
                        result = await self._execute_tool(tool_call)

                    accumulated_messages.append({
                        "role": "tool",
                        "content": result,
                        "tool_name": tool_call.name,
                    })

            # 5. 检查是否完成
            if response.tool_calls and any(
                tc.name == "done" for tc in response.tool_calls
            ):
                break

        return task
```

### 步骤 3: LLM自主决策委派

**LLM的思考过程**（系统提示词中包含meta-tool描述）：

```
任务：构建Web应用（认证、数据管理、API）

分析：
- 这是一个复杂任务，包含多个独立模块
- 我可以使用delegate_task将子任务委派给专门的Agent
- 先从认证模块开始

决策：调用delegate_task
```

**LLM的工具调用**：

```python
{
    "name": "delegate_task",
    "arguments": {
        "subtask_description": "实现用户认证系统，包括注册、登录、JWT token生成和验证",
        "required_capabilities": ["security", "crypto", "jwt"],
        "context_hints": [
            "project_goal",      # 需要知道整体目标
            "tech_stack",        # 需要知道技术栈
            "security_requirements"  # 需要知道安全要求
        ]
    }
}
```

### 步骤 4: 框架自动执行委派（_auto_delegate）

```python
async def _auto_delegate(self, args: dict, parent_task: Task) -> str:
    """自动委派实现"""

    # 1. 创建子任务
    subtask = Task(
        task_id=f"{parent_task.task_id}-auth",
        action="execute",
        parameters={
            "content": args["subtask_description"],
            "parent_task_id": parent_task.task_id,
        }
    )

    # 2. 创建子节点（整合所有组件）
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

### 步骤 5: 创建子节点（整合TaskContextManager + FractalMemory）

```python
async def _create_child_node(
    self,
    subtask: Task,
    context_hints: list[str]
) -> "Agent":
    """创建子节点，整合所有组件"""

    # 1. 创建FractalMemory（继承父节点）
    child_memory = FractalMemory(
        node_id=subtask.task_id,
        parent_memory=self.memory,  # 建立父子关系
        base_memory=LoomMemory(node_id=subtask.task_id)  # 使用L1-L4
    )

    # 2. 智能分配记忆（使用context_hints）
    allocation_strategy = SmartAllocationStrategy(max_inherited_memories=10)
    allocated_memories = await allocation_strategy.allocate(
        parent_memory=self.memory,
        child_task=subtask,
        context_hints=context_hints  # LLM提供的提示
    )

    # 3. 写入子节点记忆（INHERITED作用域）
    for scope, entries in allocated_memories.items():
        for entry in entries:
            await child_memory.write(entry.id, entry.content, scope=scope)

    # 4. 创建TaskContextManager
    child_context_manager = TaskContextManager(
        memory=child_memory.base_memory,  # 使用底层LoomMemory
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

### 步骤 6: 子Agent执行任务

子Agent使用相同的执行循环：

```python
# 子Agent的执行循环（完全相同的代码）
for iteration in range(max_iterations):
    # 1. 构建上下文（使用继承的记忆）
    messages = await self.context_manager.build_context(
        current_task=subtask,
        additional_messages=accumulated_messages,
    )

    # 2. 调用LLM
    response = await self.llm_provider.chat(messages, tools=self.tools)

    # 3. 执行工具调用
    # ...

    # 4. 子Agent也可以继续委派（递归！）
    if tool_call.name == "delegate_task":
        # 创建孙子节点
        grandchild_result = await self._auto_delegate(...)
```

### 步骤 7: 记忆同步（双向流动）

```python
async def _sync_memory_from_child(self, child_node: Agent) -> None:
    """从子节点同步记忆到父节点"""

    # 1. 获取子节点的SHARED记忆
    child_shared = await child_node.memory.list_by_scope(MemoryScope.SHARED)

    # 2. 合并到父节点
    for entry in child_shared:
        # 检查是否已存在
        existing = await self.memory.read(
            entry.id,
            search_scopes=[MemoryScope.SHARED]
        )

        if not existing:
            # 新记忆，直接添加
            await self.memory.write(entry.id, entry.content, MemoryScope.SHARED)
        else:
            # 已存在，使用冲突解决策略
            resolver = MergeResolver()
            merged = await resolver.resolve(existing, entry)
            await self.memory.write(merged.id, merged.content, MemoryScope.SHARED)
```

### 完整流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    Parent Agent                              │
│                                                               │
│  1. 接收任务: "构建Web应用"                                  │
│  2. Agent循环 (for loop)                                     │
│     ├─ TaskContextManager.build_context()                   │
│     │  └─ 从LoomMemory (L1-L4) 收集上下文                   │
│     ├─ LLM.chat(messages, tools=[delegate_task, ...])       │
│     │  └─ LLM决策: 调用delegate_task                        │
│     └─ _auto_delegate()                                      │
│        ├─ 创建子任务                                         │
│        ├─ _create_child_node()                               │
│        │  ├─ FractalMemory(parent=self.memory)              │
│        │  ├─ SmartAllocationStrategy.allocate()             │
│        │  │  └─ 使用context_hints选择相关记忆               │
│        │  └─ TaskContextManager(child_memory)               │
│        ├─ child.execute_task()  ──────────┐                 │
│        └─ _sync_memory_from_child()       │                 │
└───────────────────────────────────────────┼─────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Child Agent                               │
│                                                               │
│  1. 接收任务: "实现用户认证"                                 │
│  2. 继承父节点记忆 (INHERITED作用域)                        │
│     - project_goal                                           │
│     - tech_stack                                             │
│     - security_requirements                                  │
│  3. Agent循环 (相同的for loop)                               │
│     ├─ TaskContextManager.build_context()                   │
│     │  └─ 从child_memory (L1-L4) 收集上下文                 │
│     ├─ LLM.chat(messages, tools=[...])                      │
│     └─ 执行工具调用                                          │
│  4. 完成后，SHARED记忆同步回父节点                          │
└─────────────────────────────────────────────────────────────┘
```

**关键点**：
- ✅ 所有组件无缝集成
- ✅ LLM自主决策何时委派
- ✅ 智能上下文选择和传递
- ✅ 记忆双向流动
- ✅ 保持"Agent is just a for loop"哲学
- ✅ 支持无限递归（子Agent可以继续委派）

---

## 📌 整合总结

### 架构整合的核心价值

通过将分形架构与现有设计深度整合，我们实现了：

**1. 自主性 (Autonomy)**
- LLM通过meta-tools自主决策何时委派
- 无需显式调用框架方法
- 保持"Agent is just a for loop"的简洁性

**2. 智能性 (Intelligence)**
- TaskContextManager智能选择上下文
- SmartAllocationStrategy基于任务特征分配记忆
- context_hints让LLM参与上下文选择

**3. 高效性 (Efficiency)**
- FractalMemory复用LoomMemory的优化（堆、向量检索）
- 作用域管理避免信息过载
- O(1)复杂度保证

**4. 可扩展性 (Scalability)**
- 支持无限递归委派
- 记忆双向流动
- 清晰的职责分离

### 与现有设计的对应关系

| 现有设计 | 分形架构中的应用 | 整合方式 |
|---------|----------------|---------|
| autonomous-agent-design.md | delegate_task meta-tool | LLM自主触发委派 |
| context-manager-design.md | TaskContextManager | 构建子节点上下文 |
| agent-improvements-summary.md | Agent执行循环 | 保持for loop简洁性 |
| system-optimization-plan.md | LoomMemory (L1-L4) | FractalMemory底层存储 |

### 实施优先级调整

基于整合后的设计，实施路线图需要调整：

**Phase 1: 基础设施（2周）**
- ✅ 保持原计划：实现MemoryScope和FractalMemory基础类
- ✅ 新增：确保与LoomMemory的集成接口

**Phase 2: 同步机制（2周）**
- ✅ 保持原计划：版本控制和冲突解决
- ✅ 新增：与TaskContextManager的集成测试

**Phase 3: 智能分配（2周）**
- ✅ 保持原计划：TaskAnalyzer和SmartAllocationStrategy
- ✅ 新增：支持context_hints参数

**Phase 4: Agent集成（2周）**
- ✅ 新增重点：实现_auto_delegate和_create_child_node
- ✅ 新增重点：集成meta-tools到Agent执行循环
- ✅ 新增重点：完整的端到端测试

### 关键设计决策

**决策1：使用meta-tools而非显式方法**
- ✅ 优点：保持Agent简洁，LLM自主决策
- ✅ 优点：符合"Agent is just a for loop"哲学
- ⚠️ 注意：需要在系统提示词中清晰描述meta-tools

**决策2：FractalMemory作为LoomMemory的上层抽象**
- ✅ 优点：复用现有优化，避免重复实现
- ✅ 优点：清晰的职责分离
- ⚠️ 注意：需要维护作用域索引的一致性

**决策3：context_hints让LLM参与上下文选择**
- ✅ 优点：LLM知道需要哪些上下文
- ✅ 优点：避免框架过度猜测
- ⚠️ 注意：需要在delegate_task工具描述中说明

**决策4：记忆双向流动**
- ✅ 优点：子节点的发现可以反馈给父节点
- ✅ 优点：支持真正的协作
- ⚠️ 注意：需要冲突解决策略

### 下一步行动

1. **更新PLAN.md** - 反映整合后的实施计划
2. **更新Agent实现** - 添加_auto_delegate和_create_child_node方法
3. **更新系统提示词** - 添加delegate_task meta-tool描述
4. **编写集成测试** - 验证所有组件协同工作

---

**文档作者**: Claude + @kongusen
**创建日期**: 2026-01-25
**最后更新**: 2026-01-25
**状态**: 整合完成，待实施

