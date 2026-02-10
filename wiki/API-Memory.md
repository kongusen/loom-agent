# Memory API

## LoomMemory 基础使用

### 创建记忆系统

```python
from loom.memory import LoomMemory

memory = LoomMemory(
    node_id="agent",
    l1_max_size=50,    # L1 工作记忆容量
    l2_max_size=100,   # L2 优先级队列容量
)
```

### 添加任务

```python
from loom.runtime import Task

task = Task(
    task_id="task-1",
    action="research",
    parameters={"topic": "AI"},
    metadata={"importance": 0.8}
)

await memory.add_task(task)
```

### 检索记忆

```python
# 检索相关任务
tasks = await memory.retrieve(
    query="AI research",
    limit=10
)

for task in tasks:
    print(f"{task.task_id}: {task.action}")
```

## FractalMemory (分形记忆)

### 创建分形记忆

```python
from loom.fractal.memory import FractalMemory, MemoryScope

# 子节点记忆
child_memory = FractalMemory(
    node_id="child",
    parent_memory=parent_memory,  # 继承父节点
    base_memory=LoomMemory(node_id="child")
)
```

### 写入不同作用域

```python
# PRIVATE: 仅自己可见
await child_memory.write(
    entry_id="private-thought",
    content="我的私人想法",
    scope=MemoryScope.PRIVATE
)

# SHARED: 父子共享
await child_memory.write(
    entry_id="shared-knowledge",
    content="共享的知识",
    scope=MemoryScope.SHARED
)

# GLOBAL: 全局可见
await child_memory.write(
    entry_id="global-config",
    content="全局配置",
    scope=MemoryScope.GLOBAL
)
```

### 读取记忆

```python
# 从所有作用域读取
entry = await child_memory.read(
    entry_id="shared-knowledge"
)

# 从特定作用域读取
entry = await child_memory.read(
    entry_id="config",
    search_scopes=[MemoryScope.INHERITED, MemoryScope.GLOBAL]
)
```

### 列出记忆

```python
# 列出 PRIVATE 记忆
private_entries = await child_memory.list_by_scope(
    MemoryScope.PRIVATE
)

# 列出 SHARED 记忆
shared_entries = await child_memory.list_by_scope(
    MemoryScope.SHARED
)
```

## 记忆同步

### 从子节点同步到父节点

```python
await parent_memory.sync_from_child(child_memory)
```

## 相关概念

- → [代谢记忆](Metabolic-Memory)
- → [记忆作用域](Memory-Scope)

## 代码位置

- `loom/memory/core.py`
- `loom/fractal/memory.py`

## 反向链接

被引用于: [Agent API](API-Agent)
