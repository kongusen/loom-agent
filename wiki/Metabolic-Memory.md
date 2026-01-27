# 代谢记忆 (Metabolic Memory)

## 定义

**代谢记忆**是模仿生物认知机制的四层记忆系统，信息像营养一样经历摄入、消化、同化、排泄的循环过程。

## 核心思想

人类的记忆不是简单的"存储-检索"系统，而是动态的、分层的、有选择性的代谢过程：
- **摄入**: 从环境中获取信息（L1 工作记忆）
- **消化**: 提取重要信息（L2 优先级队列）
- **同化**: 整合到长期记忆（L3 向量存储）
- **排泄**: 丢弃不重要的信息（自动清理）

Loom 的记忆系统完全模拟这个生物学过程。

## 四层记忆谱系

| 层级 | 名称 | 容量 | 保留策略 | 用途 |
|------|------|------|----------|------|
| **L1** | 工作记忆 (Working Memory) | ~50 tasks | FIFO，自动覆盖 | 最近的短期任务 |
| **L2** | 优先级队列 (Priority Queue) | ~100 tasks | 重要性排序 | 重要但不紧急的任务 |
| **L3** | 向量存储 (Vector Store) | 无限 | 语义相似度 | 长期语义记忆 |
| **L4** | 知识图谱 (Knowledge Graph) | 无限 | 结构化关系 | 推理和关联知识 |

### L1: 工作记忆

```python
from loom.memory.layers import CircularBufferLayer

l1 = CircularBufferLayer(max_size=50)
# 最近 50 个任务，FIFO 自动淘汰
```

**特点**:
- 容量最小，速度最快
- 自动覆盖最旧的任务
- 保存完整的任务对象

### L2: 优先级队列

```python
from loom.memory.layers import PriorityQueueLayer

l2 = PriorityQueueLayer(max_size=100)
# 按 task.metadata["importance"] 排序
```

**特点**:
- 保留最重要的 100 个任务
- 使用堆结构，O(log n) 性能
- 自动淘汰低重要性任务

### L3: 向量存储

```python
from loom.memory.layers import VectorStoreLayer

l3 = VectorStoreLayer(
    dimension=1536,  # OpenAI embedding
    backend="pgvector"  # 或 "qdrant"
)
# 语义检索，返回最相似的记忆
```

**特点**:
- 基于 embedding 的语义检索
- 支持模糊查询
- 适合存储长期知识

### L4: 知识图谱

```python
from loom.memory.layers import KnowledgeGraphLayer

l4 = KnowledgeGraphLayer(backend="neo4j")
# 结构化知识，支持推理
```

**特点**:
- 实体-关系图谱
- 支持多跳推理
- 发现隐藏的关联

## 记忆代谢流程

```
新任务进入
    ↓
L1: 工作记忆 (暂时存储)
    ↓ (重要度评估)
L2: 优先级队列 (筛选)
    ↓ (语义提取)
L3: 向量存储 (长期记忆)
    ↓ (关系提取)
L4: 知识图谱 (结构化知识)
```

## 记忆作用域

除了分层，记忆还分为多个作用域：

| 作用域 | 可见性 | 生命周期 |
|--------|--------|----------|
| **PRIVATE** | 仅当前节点 | 节点销毁时清除 |
| **SHARED** | 父子节点共享 | 向上同步到父节点 |
| **INHERITED** | 从父节点继承 | 只读，无法修改 |
| **GLOBAL** | 全局可见 | 永久保存 |

参见: [Memory-Scope](Memory-Scope)

## 相关概念

- → [公理系统](Axiomatic-System) (A4: 记忆代谢公理)
- → [记忆分层](Memory-Layers) (L1-L4 详细说明)
- → [记忆作用域](Memory-Scope) (PRIVATE/SHARED/INHERITED/GLOBAL)
- → [上下文管理](Context-Management) (智能上下文构建)

## 参见

- 📖 [设计文档](design/Memory-System)
- 🔧 [API 指南]: [记忆管理](api/Memory)
- 💡 [示例代码]: [记忆系统演示](examples/memory-demo)

## 代码位置

- 核心实现: `loom/memory/core.py`
- 层实现: `loom/memory/layers/`
- 上下文管理: `loom/memory/task_context.py`

## 反向链接

被引用于: [分形架构](Fractal-Architecture) | [分形节点](Fractal-Node) | [四范式工作](Four-Paradigms)
