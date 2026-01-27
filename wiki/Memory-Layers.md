# 记忆分层 (Memory Layers)

## 定义

**记忆分层**是 Loom 的四层记忆系统，从工作记忆到知识图谱，模拟人类认知的完整记忆谱系。

## 四层结构

```
┌─────────────────────────────────────┐
│  L4: 知识图谱 (Knowledge Graph)     │  ← 结构化知识，推理
├─────────────────────────────────────┤
│  L3: 向量存储 (Vector Store)        │  ← 长期语义记忆
├─────────────────────────────────────┤
│  L2: 优先级队列 (Priority Queue)    │  ← 重要任务缓存
├─────────────────────────────────────┤
│  L1: 工作记忆 (Working Memory)      │  ← 短期记忆
└─────────────────────────────────────┘
```

## L1: 工作记忆 (Circular Buffer)

**特点**:
- 容量: ~50 tasks
- 策略: FIFO (先进先出)
- 速度: O(1) 快速访问

**用途**:
- 临时存储最近的任务
- 快速访问短期信息
- 自动淘汰最旧的任务

**实现**: `CircularBufferLayer`

```python
from loom.memory.layers import CircularBufferLayer

l1 = CircularBufferLayer(max_size=50)

# 添加任务（自动淘汰最旧的）
await l1.add(task)

# 检索最近的任务
recent = await l1.retrieve(None, limit=10)
```

**适用场景**:
- 需要快速访问最近的任务
- 不需要长期保留
- 自动管理容量

---

## L2: 优先级队列 (Priority Queue)

**特点**:
- 容量: ~100 tasks
- 策略: 按重要性排序
- 速度: O(log n) 插入和删除

**用途**:
- 保存重要的但不是紧急的任务
- 根据 `task.metadata["importance"]` 排序
- 自动淘汰低重要性任务

**实现**: `PriorityQueueLayer`

```python
from loom.memory.layers import PriorityQueueLayer

l2 = PriorityQueueLayer(max_size=100)

# 添加任务（自动按重要性排序）
task.metadata["importance"] = 0.8
await l2.add(task)

# 检索最重要的任务
important = await l2.retrieve(None, limit=10)
```

**适用场景**:
- 需要保留重要信息
- 有明确的优先级标准
- 自动管理容量

---

## L3: 向量存储 (Vector Store)

**特点**:
- 容量: 无限
- 策略: 语义相似度检索
- 速度: O(log n) ANN 检索

**用途**:
- 长期语义记忆
- 基于embedding的模糊查询
- 跨任务的记忆关联

**实现**: `VectorStoreLayer`

```python
from loom.memory.layers import VectorStoreLayer

l3 = VectorStoreLayer(
    dimension=1536,  # OpenAI embedding
    backend="pgvector"  # 或 "qdrant"
)

# 添加记忆（自动生成 embedding）
await l3.add(
    MemoryEntry(
        id="mem-1",
        content="Python 是一种编程语言"
    )
)

# 语义检索
results = await l3.retrieve(
    query="编程语言",
    limit=10
)
```

**支持的后端**:
- `pgvector`: PostgreSQL + pgvector 扩展
- `qdrant`: 专用向量数据库

**适用场景**:
- 需要长期保留信息
- 语义检索和模糊查询
- 跨任务的知识复用

---

## L4: 知识图谱 (Knowledge Graph)

**特点**:
- 容量: 无限
- 策略: 结构化关系推理
- 速度: 可变（取决于图查询复杂度）

**用途**:
- 结构化知识存储
- 多跳推理
- 发现隐藏的关联

**实现**: `KnowledgeGraphLayer`

```python
from loom.memory.layers import KnowledgeGraphLayer

l4 = KnowledgeGraphLayer(backend="neo4j")

# 添加实体和关系
await l4.add_entity(
    Entity(
        id="python",
        type="ProgrammingLanguage",
        properties={"name": "Python", "created": 1991}
    )
)

await l4.add_relation(
    Relation(
        source="python",
        target="guido",
        relation="created_by"
    )
)

# 图查询
results = await l4.retrieve(
    query="MATCH (p:ProgrammingLanguage)-[r:created_by]->(p) RETURN p"
)
```

**支持的后端**:
- `neo4j`: 图数据库
- `memory`: 内存图（开发测试）

**适用场景**:
- 需要存储结构化知识
- 需要多跳推理
- 发现实体间的关系

---

## 层级协作

### 自动记忆流动

```python
class LoomMemory:
    async def add_task(self, task: Task):
        # 1. 先进入 L1 工作记忆
        await self.l1.add(task)

        # 2. 如果重要，进入 L2 优先级队列
        if task.metadata.get("importance", 0) > 0.5:
            await self.l2.add(task)

        # 3. 提取语义，进入 L3 向量存储
        embedding = await self._embed(task)
        await self.l3.add(MemoryEntry(
            id=task.task_id,
            content=task.action,
            embedding=embedding
        ))

        # 4. 提取关系，进入 L4 知识图谱
        entities = await self._extract_entities(task)
        await self.l4.add_entities(entities)
```

### 检索策略

```python
class LoomMemory:
    async def retrieve(
        self,
        query: str,
        limit: int = 10
    ) -> list[MemoryEntry]:
        results = []

        # 1. 从 L1 获取最近的任务
        results.extend(await self.l1.retrieve(query, limit=3))

        # 2. 从 L2 获取重要的任务
        results.extend(await self.l2.retrieve(query, limit=3))

        # 3. 从 L3 语义检索
        results.extend(await self.l3.retrieve(query, limit=4))

        # 4. 从 L4 图推理
        results.extend(await self.l4.retrieve(query, limit=2))

        # 去重并排序
        return self._deduplicate_and_rank(results)
```

## 性能考虑

| 层级 | 插入速度 | 检索速度 | 容量 | 成本 |
|------|----------|----------|------|------|
| L1 | O(1) | O(1) | 小 | 低 |
| L2 | O(log n) | O(n log n) | 中 | 低 |
| L3 | O(log n) | O(log n) | 大 | 中 |
| L4 | O(1) | 可变 | 大 | 高 |

## 相关概念

- → [代谢记忆](Metabolic-Memory) (整体架构)
- → [记忆作用域](Memory-Scope) (PRIVATE/SHARED/INHERITED/GLOBAL)
- → [上下文管理](Context-Management) (智能上下文构建)

## 参见

- 📖 [设计文档](design/Memory-Layers)
- 🔧 [API 指南]: [记忆 API](api/Memory)

## 代码位置

- 核心: `loom/memory/core.py`
- 层实现: `loom/memory/layers/`

## 反向链接

被引用于: [代谢记忆](Metabolic-Memory) | [上下文管理](Context-Management) | [Agent API](API-Agent)
