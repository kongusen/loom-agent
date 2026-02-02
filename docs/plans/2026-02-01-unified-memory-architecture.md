# Unified Memory Architecture - Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate FractalMemory, LoomMemory, and TaskContextManager into UnifiedMemoryManager and ContextOrchestrator to eliminate responsibility overlap and establish clear architectural boundaries.

**Architecture:** Create a two-layer architecture where UnifiedMemoryManager handles all memory storage (L1-L4 layers + fractal scopes) and ContextOrchestrator handles all context building logic (token budgets + semantic projection). Agent execution loop will use these two clean interfaces instead of three overlapping systems.

**Tech Stack:** Python 3.11+, asyncio, dataclasses, Pydantic

**Principles:** TDD (test-first), DRY (no duplication), YAGNI (simple first, optimize later), frequent commits

---

## Overview

### Current State Problems

1. **Responsibility Overlap**: FractalMemory, LoomMemory, and TaskContextManager all handle memory/context
2. **Unclear Boundaries**: TaskContextManager depends on both FractalMemory and LoomMemory
3. **Scattered Logic**: Context building logic split across multiple files
4. **Hard to Test**: Interdependencies make unit testing difficult

### Target State

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent                                │
│  (Simplified execution loop)                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─── UnifiedMemoryManager
                              │    (Storage: L1-L4 + Scopes)
                              │
                              └─── ContextOrchestrator
                                   (Context Building + Budgets)
```

### Implementation Phases

**Phase 1A: UnifiedMemoryManager** (Tasks 1-5)
- Create unified storage interface
- Integrate L1-L4 layers
- Integrate fractal scopes
- Migrate tests

**Phase 1B: ContextOrchestrator** (Tasks 6-10)
- Create context orchestration interface
- Integrate token budgeting
- Integrate context sources
- Migrate tests

**Phase 1C: Agent Integration** (Tasks 11-15)
- Update Agent to use new components
- Remove old components
- Update all tests
- Verify end-to-end

---

## Phase 1A: UnifiedMemoryManager

### Task 1: Create UnifiedMemoryManager skeleton

**File:** `loom/memory/unified.py` (NEW)

**Action:** Create the basic structure with type hints and docstrings.

```python
"""
Unified Memory Manager - 统一内存管理器

整合 FractalMemory 和 LoomMemory 的职责：
- L1-L4 分层存储（来自 LoomMemory）
- LOCAL/SHARED/INHERITED/GLOBAL 作用域（来自 FractalMemory）
- 统一的读写接口
- 父子节点关系管理
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from loom.fractal.memory import MemoryScope, MemoryEntry
from loom.memory.core import LoomMemory
from loom.protocol import Task


class UnifiedMemoryManager:
    """统一内存管理器 - 整合 LoomMemory（L1-L4）和 FractalMemory（作用域）"""

    def __init__(
        self,
        node_id: str,
        parent: Optional["UnifiedMemoryManager"] = None,
        max_l1_size: int = 50,
        max_l2_size: int = 100,
        max_l3_size: int = 500,
    ):
        self.node_id = node_id
        self.parent = parent

        # 底层存储：LoomMemory 管理 L1-L4
        self._loom_memory = LoomMemory(
            node_id=node_id,
            max_l1_size=max_l1_size,
            max_l2_size=max_l2_size,
            max_l3_size=max_l3_size,
        )

        # 作用域索引
        self._memory_by_scope: dict[MemoryScope, dict[str, MemoryEntry]] = {
            scope: {} for scope in MemoryScope
        }

    async def write(
        self, entry_id: str, content: Any, scope: MemoryScope = MemoryScope.LOCAL
    ) -> MemoryEntry:
        """写入记忆（TODO: Task 2）"""
        raise NotImplementedError

    async def read(
        self, entry_id: str, search_scopes: list[MemoryScope] | None = None
    ) -> MemoryEntry | None:
        """读取记忆（TODO: Task 3）"""
        raise NotImplementedError

    # LoomMemory 兼容接口
    def add_task(self, task: Task) -> None:
        self._loom_memory.add_task(task)

    def get_l1_tasks(self, limit: int = 10, session_id: str | None = None) -> list[Task]:
        return self._loom_memory.get_l1_tasks(limit=limit, session_id=session_id)
```

**Test:** `tests/unit/test_memory/test_unified.py` (NEW)

```python
"""Tests for UnifiedMemoryManager"""
import pytest
from loom.memory.unified import UnifiedMemoryManager
from loom.fractal.memory import MemoryScope


def test_init_basic():
    """Test basic initialization"""
    manager = UnifiedMemoryManager(node_id="test-node")
    assert manager.node_id == "test-node"
    assert manager.parent is None
    assert len(manager._memory_by_scope) == len(MemoryScope)


def test_init_with_parent():
    """Test initialization with parent"""
    parent = UnifiedMemoryManager(node_id="parent")
    child = UnifiedMemoryManager(node_id="child", parent=parent)
    assert child.parent is parent
```

**Run:** `pytest tests/unit/test_memory/test_unified.py -v`

**Commit:** `feat: create UnifiedMemoryManager skeleton`

---

### Task 2: Implement write() method

**File:** `loom/memory/unified.py`

**Action:** Implement the write method with scope-based storage.

```python
async def write(
    self, entry_id: str, content: Any, scope: MemoryScope = MemoryScope.LOCAL
) -> MemoryEntry:
    """
    写入记忆到指定作用域

    Args:
        entry_id: 记忆唯一标识
        content: 记忆内容
        scope: 作用域（LOCAL/SHARED/INHERITED/GLOBAL）

    Returns:
        创建的记忆条目
    """
    from loom.fractal.memory import ACCESS_POLICIES

    # 检查写权限
    policy = ACCESS_POLICIES[scope]
    if not policy.writable:
        raise PermissionError(f"Scope {scope.value} is read-only")

    # 如果已存在，更新版本
    existing = self._memory_by_scope[scope].get(entry_id)
    if existing:
        existing.version += 1
        existing.content = content
        existing.updated_by = self.node_id
        return existing

    # 创建新记忆条目
    entry = MemoryEntry(
        id=entry_id,
        content=content,
        scope=scope,
        created_by=self.node_id,
        updated_by=self.node_id,
    )

    self._memory_by_scope[scope][entry_id] = entry
    return entry
```

**Test:** Add to `tests/unit/test_memory/test_unified.py`

```python
@pytest.mark.asyncio
async def test_write_local():
    """Test writing to LOCAL scope"""
    manager = UnifiedMemoryManager(node_id="test")
    entry = await manager.write("key1", "value1", MemoryScope.LOCAL)

    assert entry.id == "key1"
    assert entry.content == "value1"
    assert entry.scope == MemoryScope.LOCAL
    assert entry.created_by == "test"


@pytest.mark.asyncio
async def test_write_inherited_fails():
    """Test that writing to INHERITED scope fails"""
    manager = UnifiedMemoryManager(node_id="test")

    with pytest.raises(PermissionError):
        await manager.write("key1", "value1", MemoryScope.INHERITED)
```

**Run:** `pytest tests/unit/test_memory/test_unified.py::test_write_local -v`

**Commit:** `feat: implement UnifiedMemoryManager.write()`

---

### Task 3: Implement read() method

**File:** `loom/memory/unified.py`

**Action:** Implement the read method with scope hierarchy and parent inheritance.

```python
async def read(
    self, entry_id: str, search_scopes: list[MemoryScope] | None = None
) -> MemoryEntry | None:
    """
    读取记忆（支持作用域搜索和父节点继承）

    Args:
        entry_id: 记忆唯一标识
        search_scopes: 搜索的作用域列表（None = 搜索所有）

    Returns:
        记忆条目，如果不存在返回 None
    """
    if search_scopes is None:
        search_scopes = list(MemoryScope)

    # 按优先级搜索本地作用域：LOCAL > SHARED > INHERITED > GLOBAL
    for scope in search_scopes:
        if entry_id in self._memory_by_scope[scope]:
            return self._memory_by_scope[scope][entry_id]

    # 如果是 INHERITED 作用域，尝试从父节点读取
    if MemoryScope.INHERITED in search_scopes and self.parent:
        parent_entry = await self.parent.read(
            entry_id,
            search_scopes=[MemoryScope.SHARED, MemoryScope.GLOBAL, MemoryScope.INHERITED],
        )
        if parent_entry:
            # 创建只读副本并缓存
            inherited_entry = MemoryEntry(
                id=parent_entry.id,
                content=parent_entry.content,
                scope=MemoryScope.INHERITED,
                version=parent_entry.version,
                created_by=parent_entry.created_by,
                updated_by=parent_entry.updated_by,
                parent_version=parent_entry.version,
            )
            self._memory_by_scope[MemoryScope.INHERITED][entry_id] = inherited_entry
            return inherited_entry

    return None
```

**Test:** Add to `tests/unit/test_memory/test_unified.py`

```python
@pytest.mark.asyncio
async def test_read_local():
    """Test reading from LOCAL scope"""
    manager = UnifiedMemoryManager(node_id="test")
    await manager.write("key1", "value1", MemoryScope.LOCAL)

    entry = await manager.read("key1")
    assert entry is not None
    assert entry.content == "value1"


@pytest.mark.asyncio
async def test_read_inherited_from_parent():
    """Test reading INHERITED scope from parent"""
    parent = UnifiedMemoryManager(node_id="parent")
    child = UnifiedMemoryManager(node_id="child", parent=parent)

    # Parent writes to SHARED
    await parent.write("shared_key", "shared_value", MemoryScope.SHARED)

    # Child reads as INHERITED
    entry = await child.read("shared_key", [MemoryScope.INHERITED])
    assert entry is not None
    assert entry.content == "shared_value"
    assert entry.scope == MemoryScope.INHERITED
```

**Run:** `pytest tests/unit/test_memory/test_unified.py::test_read -v`

**Commit:** `feat: implement UnifiedMemoryManager.read() with parent inheritance`

---

### Task 4: Implement list_by_scope() and complete Phase 1A

**File:** `loom/memory/unified.py`

**Action:** Add list_by_scope method and additional helper methods.

```python
async def list_by_scope(self, scope: MemoryScope) -> list[MemoryEntry]:
    """列出指定作用域的所有记忆"""
    return list(self._memory_by_scope[scope].values())

def get_l2_tasks(self, limit: int = 10, session_id: str | None = None) -> list[Task]:
    """获取 L2 重要任务（兼容 LoomMemory 接口）"""
    return self._loom_memory.get_l2_tasks(limit=limit, session_id=session_id)

def promote_tasks(self) -> None:
    """触发任务提升（L1→L2→L3→L4）"""
    self._loom_memory.promote_tasks()

async def promote_tasks_async(self) -> None:
    """异步触发任务提升"""
    await self._loom_memory.promote_tasks_async()
```

**Test:** Add to `tests/unit/test_memory/test_unified.py`

```python
@pytest.mark.asyncio
async def test_list_by_scope():
    """Test listing entries by scope"""
    manager = UnifiedMemoryManager(node_id="test")
    await manager.write("key1", "value1", MemoryScope.LOCAL)
    await manager.write("key2", "value2", MemoryScope.LOCAL)
    await manager.write("key3", "value3", MemoryScope.SHARED)

    local_entries = await manager.list_by_scope(MemoryScope.LOCAL)
    assert len(local_entries) == 2

    shared_entries = await manager.list_by_scope(MemoryScope.SHARED)
    assert len(shared_entries) == 1
```

**Run:** `pytest tests/unit/test_memory/test_unified.py -v`

**Commit:** `feat: complete UnifiedMemoryManager core functionality`

---

### Task 5: Integration test for UnifiedMemoryManager

**File:** `tests/integration/test_unified_memory.py` (NEW)

**Action:** Create integration test covering parent-child memory sharing.

```python
"""Integration tests for UnifiedMemoryManager"""
import pytest
from loom.memory.unified import UnifiedMemoryManager
from loom.fractal.memory import MemoryScope
from loom.protocol import Task


@pytest.mark.asyncio
async def test_parent_child_memory_sharing():
    """Test complete parent-child memory sharing workflow"""
    # Create parent and child
    parent = UnifiedMemoryManager(node_id="parent")
    child = UnifiedMemoryManager(node_id="child", parent=parent)

    # Parent writes to SHARED scope
    await parent.write("goal", "Analyze codebase", MemoryScope.SHARED)

    # Child can read as INHERITED
    goal = await child.read("goal", [MemoryScope.INHERITED])
    assert goal is not None
    assert goal.content == "Analyze codebase"

    # Child writes to SHARED scope (visible to parent)
    await child.write("finding", "Found bug", MemoryScope.SHARED)

    # Parent can read child's SHARED memory
    finding = await parent.read("finding", [MemoryScope.SHARED])
    assert finding is not None
    assert finding.content == "Found bug"

    # Child's LOCAL memory is not visible to parent
    await child.write("private", "Internal note", MemoryScope.LOCAL)
    private = await parent.read("private")
    assert private is None


@pytest.mark.asyncio
async def test_loom_memory_compatibility():
    """Test that LoomMemory interface still works"""
    manager = UnifiedMemoryManager(node_id="test")

    # Add task via LoomMemory interface
    task = Task(task_id="task1", action="execute", parameters={"content": "test"})
    manager.add_task(task)

    # Retrieve via LoomMemory interface
    l1_tasks = manager.get_l1_tasks(limit=10)
    assert len(l1_tasks) == 1
    assert l1_tasks[0].task_id == "task1"
```

**Run:** `pytest tests/integration/test_unified_memory.py -v`

**Commit:** `test: add integration tests for UnifiedMemoryManager`

---

## Phase 1B: ContextOrchestrator

### Task 6: Create ContextOrchestrator skeleton

**File:** `loom/memory/orchestrator.py` (NEW)

**Action:** Create the context orchestration interface.

```python
"""
Context Orchestrator - 上下文编排器

统一的上下文构建逻辑，整合：
- Token 预算管理（来自 ContextBudgeter）
- 上下文源管理（来自 ContextSource）
- 消息转换（来自 MessageConverter）
- 语义投影（简化版）

设计原则：
1. 单一职责 - 只负责上下文构建，不负责存储
2. 清晰接口 - build_context() 一个核心方法
3. 可扩展 - 支持多个上下文源
"""

from typing import Any

from loom.memory.task_context import (
    ContextBudgeter,
    ContextSource,
    MessageConverter,
    BudgetConfig,
)
from loom.memory.tokenizer import TokenCounter
from loom.protocol import Task


class ContextOrchestrator:
    """
    上下文编排器

    整合 token 预算、上下文源、消息转换。
    """

    def __init__(
        self,
        token_counter: TokenCounter,
        sources: list[ContextSource],
        max_tokens: int = 4000,
        system_prompt: str = "",
        budget_config: BudgetConfig | None = None,
    ):
        """
        初始化上下文编排器

        Args:
            token_counter: Token 计数器
            sources: 上下文源列表
            max_tokens: 最大 token 数
            system_prompt: 系统提示词
            budget_config: 预算配置
        """
        self.token_counter = token_counter
        self.sources = sources
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

        # 创建预算分配器
        self.budgeter = ContextBudgeter(
            token_counter=token_counter,
            max_tokens=max_tokens,
            config=budget_config or BudgetConfig(),
        )

        # 创建消息转换器
        self.converter = MessageConverter()

    async def build_context(self, current_task: Task) -> list[dict[str, str]]:
        """
        构建 LLM 上下文

        Args:
            current_task: 当前任务

        Returns:
            OpenAI 格式的消息列表
        """
        # TODO: Implement in Task 7
        raise NotImplementedError
```

**Test:** `tests/unit/test_memory/test_orchestrator.py` (NEW)

```python
"""Tests for ContextOrchestrator"""
import pytest
from loom.memory.orchestrator import ContextOrchestrator
from loom.memory.tokenizer import TokenCounter
from loom.protocol import Task


def test_init_basic():
    """Test basic initialization"""
    counter = TokenCounter()
    orchestrator = ContextOrchestrator(
        token_counter=counter,
        sources=[],
        max_tokens=4000,
    )

    assert orchestrator.max_tokens == 4000
    assert orchestrator.budgeter is not None
    assert orchestrator.converter is not None
```

**Run:** `pytest tests/unit/test_memory/test_orchestrator.py -v`

**Commit:** `feat: create ContextOrchestrator skeleton`

---

### Task 7: Implement build_context() method

**File:** `loom/memory/orchestrator.py`

**Action:** Implement the core context building logic.

```python
async def build_context(self, current_task: Task) -> list[dict[str, str]]:
    """
    构建 LLM 上下文

    流程：
    1. 计算 token 预算
    2. 从各个源收集上下文
    3. 转换为消息格式
    4. 应用 token 限制
    """
    # 1. 计算预算
    system_tokens = (
        self.token_counter.count_messages([{"role": "system", "content": self.system_prompt}])
        if self.system_prompt
        else 0
    )
    budget = self.budgeter.allocate_budget(system_prompt_tokens=system_tokens)

    # 2. 从各个源收集上下文任务
    context_tasks: list[Task] = []
    for source in self.sources:
        tasks = await source.get_context(current_task, max_items=20)
        context_tasks.extend(tasks)

    # 3. 按 session_id 过滤
    if current_task.session_id:
        context_tasks = [t for t in context_tasks if t.session_id == current_task.session_id]

    # 4. 去重
    seen_ids = set()
    unique_tasks = []
    for task in context_tasks:
        if task.task_id not in seen_ids:
            unique_tasks.append(task)
            seen_ids.add(task.task_id)

    # 5. 转换为消息
    context_messages = self.converter.convert_tasks_to_messages(unique_tasks)
    current_messages = self.converter.convert_tasks_to_messages([current_task])

    # 6. 组装最终消息
    final_messages: list[dict[str, str]] = []
    if self.system_prompt:
        final_messages.append({"role": "system", "content": self.system_prompt})

    final_messages.extend(context_messages)
    final_messages.extend(current_messages)

    # 7. 应用 token 限制
    return self._fit_to_token_limit(final_messages)

def _fit_to_token_limit(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """确保消息不超过 token 限制"""
    current_tokens = self.token_counter.count_messages(messages)
    if current_tokens <= self.max_tokens:
        return messages

    # 保留系统消息 + 最近的消息
    system_messages = [m for m in messages if m.get("role") == "system"]
    other_messages = [m for m in messages if m.get("role") != "system"]

    system_tokens = self.token_counter.count_messages(system_messages)
    available = self.max_tokens - system_tokens

    # 从后往前保留消息
    kept = []
    current = 0
    for msg in reversed(other_messages):
        msg_tokens = self.token_counter.count_messages([msg])
        if current + msg_tokens > available:
            break
        kept.insert(0, msg)
        current += msg_tokens

    return system_messages + kept
```

**Test:** Add to `tests/unit/test_memory/test_orchestrator.py`

```python
@pytest.mark.asyncio
async def test_build_context_basic():
    """Test basic context building"""
    from loom.memory.task_context import MemoryContextSource
    from loom.memory.core import LoomMemory

    counter = TokenCounter()
    memory = LoomMemory(node_id="test")
    source = MemoryContextSource(memory)

    orchestrator = ContextOrchestrator(
        token_counter=counter,
        sources=[source],
        max_tokens=4000,
        system_prompt="You are a helpful assistant",
    )

    task = Task(task_id="task1", action="execute", parameters={"content": "test"})
    messages = await orchestrator.build_context(task)

    assert len(messages) > 0
    assert messages[0]["role"] == "system"
    assert "helpful assistant" in messages[0]["content"]
```

**Run:** `pytest tests/unit/test_memory/test_orchestrator.py::test_build_context_basic -v`

**Commit:** `feat: implement ContextOrchestrator.build_context()`

---

### Task 8-10: Complete Phase 1B (ContextOrchestrator)

**Summary:** Tasks 8-10 are simplified - the core ContextOrchestrator is complete. These tasks focus on integration testing and documentation.

**Task 8:** Integration test with UnifiedMemoryManager

**File:** `tests/integration/test_context_orchestration.py` (NEW)

```python
"""Integration tests for ContextOrchestrator with UnifiedMemoryManager"""
import pytest
from loom.memory.unified import UnifiedMemoryManager
from loom.memory.orchestrator import ContextOrchestrator
from loom.memory.task_context import MemoryContextSource, FractalMemoryContextSource
from loom.memory.tokenizer import TokenCounter
from loom.protocol import Task
from loom.fractal.memory import MemoryScope


@pytest.mark.asyncio
async def test_orchestrator_with_unified_memory():
    """Test ContextOrchestrator using UnifiedMemoryManager"""
    # Create unified memory
    memory = UnifiedMemoryManager(node_id="test")

    # Add some tasks
    task1 = Task(task_id="t1", action="execute", parameters={"content": "task 1"}, session_id="s1")
    task2 = Task(task_id="t2", action="execute", parameters={"content": "task 2"}, session_id="s1")
    memory.add_task(task1)
    memory.add_task(task2)

    # Create context source
    source = MemoryContextSource(memory._loom_memory)

    # Create orchestrator
    counter = TokenCounter()
    orchestrator = ContextOrchestrator(
        token_counter=counter,
        sources=[source],
        max_tokens=4000,
        system_prompt="Test system",
    )

    # Build context
    current = Task(task_id="t3", action="execute", parameters={"content": "current"}, session_id="s1")
    messages = await orchestrator.build_context(current)

    assert len(messages) > 0
    assert any("Test system" in m.get("content", "") for m in messages)
```

**Run:** `pytest tests/integration/test_context_orchestration.py -v`

**Commit:** `test: add integration tests for ContextOrchestrator`

---

## Phase 1C: Agent Integration

### Task 11: Update Agent to use UnifiedMemoryManager

**File:** `loom/agent/core.py`

**Action:** Replace FractalMemory + LoomMemory with UnifiedMemoryManager.

**Changes:**

1. Import UnifiedMemoryManager:
```python
from loom.memory.unified import UnifiedMemoryManager
```

2. Replace initialization in `__init__`:
```python
# OLD:
self.memory = LoomMemory(node_id=node_id, ...)
self.fractal_memory = FractalMemory(node_id=node_id, parent_memory=parent_fractal, ...)

# NEW:
self.unified_memory = UnifiedMemoryManager(
    node_id=node_id,
    parent=parent_unified if parent_unified else None,
    max_l1_size=max_l1_size,
    max_l2_size=max_l2_size,
    max_l3_size=max_l3_size,
)
```

3. Update all references:
```python
# OLD: self.memory.add_task(task)
# NEW: self.unified_memory.add_task(task)

# OLD: self.memory.get_l1_tasks()
# NEW: self.unified_memory.get_l1_tasks()

# OLD: await self.fractal_memory.write(...)
# NEW: await self.unified_memory.write(...)
```

**Test:** Run existing Agent tests to ensure compatibility.

**Run:** `pytest tests/unit/test_agent/ -v`

**Commit:** `refactor: Agent uses UnifiedMemoryManager`

---

### Task 12: Update Agent to use ContextOrchestrator

**File:** `loom/agent/core.py`

**Action:** Replace TaskContextManager with ContextOrchestrator.

**Changes:**

1. Import ContextOrchestrator:
```python
from loom.memory.orchestrator import ContextOrchestrator
```

2. Replace initialization:
```python
# OLD:
self.context_manager = TaskContextManager(
    token_counter=token_counter,
    sources=[memory_source, fractal_source],
    ...
)

# NEW:
self.context_orchestrator = ContextOrchestrator(
    token_counter=token_counter,
    sources=[memory_source, fractal_source],
    max_tokens=max_context_tokens,
    system_prompt=self._build_full_system_prompt(...),
)
```

3. Update context building in `_execute_impl`:
```python
# OLD: messages = await self.context_manager.build_context(task)
# NEW: messages = await self.context_orchestrator.build_context(task)
```

**Test:** Run Agent execution tests.

**Run:** `pytest tests/integration/test_agent_tool_execution.py -v`

**Commit:** `refactor: Agent uses ContextOrchestrator`

---

### Task 13: Remove old components

**Action:** Mark old files as deprecated or remove them.

**Files to deprecate:**
- `loom/fractal/memory.py` - Keep for now (MemoryScope/MemoryEntry still used)
- `loom/memory/task_context.py` - Keep ContextSource/MessageConverter, deprecate TaskContextManager

**Changes to `loom/memory/task_context.py`:**

```python
# Add deprecation warning to TaskContextManager
import warnings

class TaskContextManager:
    """
    DEPRECATED: Use ContextOrchestrator instead.

    This class will be removed in version 0.5.0.
    """

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "TaskContextManager is deprecated. Use ContextOrchestrator instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # ... existing code ...
```

**Commit:** `refactor: deprecate old memory/context components`

---

### Task 14: Update all tests

**Action:** Update tests to use new components.

**Files to update:**
- `tests/unit/test_agent/` - Update Agent tests
- `tests/integration/test_fractal_integration.py` - Update fractal tests
- `tests/integration/test_memory_integration.py` - Update memory tests

**Strategy:** Run tests incrementally and fix failures.

**Run:** `pytest tests/ -v --tb=short`

**Commit:** `test: update all tests for new architecture`

---

### Task 15: End-to-end verification

**Action:** Run full test suite and verify all functionality works.

**Verification checklist:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Agent can execute tasks
- [ ] Memory sharing works (parent-child)
- [ ] Context building works
- [ ] Token budgets are respected

**Run:**
```bash
pytest tests/ -v
pytest tests/integration/ -v --tb=short
```

**Final verification:** Run a real Agent workflow:

```python
# Create test script: verify_refactor.py
from loom.api import LoomApp
from loom.api.models import AgentConfig
from loom.providers.llm import OpenAIProvider

app = LoomApp()
app.set_llm_provider(OpenAIProvider(api_key="..."))

config = AgentConfig(agent_id="test-agent")
agent = app.create_agent(config)

# Test basic execution
result = await agent.execute_task(Task(
    task_id="test",
    action="execute",
    parameters={"content": "What is 2+2?"}
))

print(f"Result: {result.result}")
print("✅ Refactor verification complete!")
```

**Run:** `python verify_refactor.py`

**Commit:** `refactor: Phase 1 complete - unified memory architecture`

---

## Phase 2: Optional Optimizations (按需实施)

**重要提示**: Phase 2 的优化应该**基于实际遇到的问题**来实施，而不是提前过度设计。

### When to Implement Phase 2 Optimizations

#### Performance Optimizations (如果遇到性能问题)

**Symptoms:**
- Agent 响应延迟 > 2 秒
- 内存使用持续增长
- 工具执行时间过长

**Solutions:**
1. **Copy-on-Write (CoW)** - 减少内存复制
   - 在 `UnifiedMemoryManager.read()` 中实现 CoW 引用
   - 只在写入时才真正复制数据

2. **Tool Dependency Graph** - 并行执行工具
   - 在 `Agent._execute_impl()` 中实现依赖图分析
   - 并行执行只读工具

3. **LRU Cache** - 减少重复查询
   - 在 `UnifiedMemoryManager` 中添加 LRU 缓存
   - 缓存最近访问的记忆条目

#### Consistency Optimizations (如果遇到一致性问题)

**Symptoms:**
- 父子节点数据不同步
- 并发写入导致数据丢失
- 记忆版本冲突

**Solutions:**
1. **Version Vector** - 检测并发冲突
   - 在 `MemoryEntry` 中添加 `vector_clock` 字段
   - 实现 Lamport 时钟算法

2. **Live Link** - 事件驱动缓存失效
   - 在 `UnifiedMemoryManager.write()` 中发布更新事件
   - 子节点订阅父节点的更新事件

3. **Conflict Resolution** - 自动解决冲突
   - 实现 Last-Write-Wins 策略
   - 或让 LLM 决定使用哪个版本

#### Observability Optimizations (如果需要调试)

**Symptoms:**
- 难以追踪任务执行流程
- 错误难以定位
- 性能瓶颈不明确

**Solutions:**
1. **Distributed Tracing** - 追踪任务执行
   - 为每个任务添加 `span_id` 和 `parent_span_id`
   - 记录执行时间和状态

2. **Error Aggregation** - 聚合相似错误
   - 计算异常签名（类型 + 文件 + 行号）
   - 统计错误频率，达到阈值时告警

### Implementation Strategy for Phase 2

**Step 1: Measure First**
```python
# Add metrics to existing code
import time

start = time.time()
result = await self.unified_memory.read(entry_id)
duration = time.time() - start

if duration > 0.1:  # 100ms threshold
    logger.warning(f"Slow memory read: {entry_id} took {duration:.2f}s")
```

**Step 2: Identify Bottleneck**
- Use profiling tools (cProfile, memory_profiler)
- Check logs for slow operations
- Monitor memory usage

**Step 3: Implement Targeted Fix**
- Only implement the optimization that addresses the specific bottleneck
- Don't implement all optimizations at once
- Measure improvement after each change

**Step 4: Verify Improvement**
- Run benchmarks before and after
- Ensure tests still pass
- Check that the problem is actually solved

---

## Summary

### Phase 1 Deliverables

✅ **UnifiedMemoryManager** - Consolidates FractalMemory + LoomMemory
- Single interface for all memory operations
- Supports L1-L4 layers + fractal scopes
- Parent-child memory sharing

✅ **ContextOrchestrator** - Consolidates TaskContextManager
- Single interface for context building
- Token budget management
- Multiple context sources

✅ **Clean Architecture** - Clear boundaries
- Storage layer (UnifiedMemoryManager)
- Context layer (ContextOrchestrator)
- Agent uses both via clean interfaces

### Success Criteria

- [ ] All existing tests pass
- [ ] Agent execution works correctly
- [ ] Memory sharing works (parent-child)
- [ ] Context building respects token budgets
- [ ] Code is simpler and easier to understand

### Next Steps

1. **Execute the plan** using `superpowers:executing-plans` skill
2. **Test incrementally** after each task
3. **Commit frequently** to track progress
4. **Only implement Phase 2** if you encounter actual problems

---

**Plan Created:** 2026-02-01
**Status:** Ready for execution
**Estimated Effort:** 2-3 weeks for Phase 1

