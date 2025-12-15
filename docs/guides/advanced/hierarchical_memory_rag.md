# HierarchicalMemory + RAG 集成指南

> **版本**: v0.1.9 
> **功能**: 分层记忆系统 + 检索增强生成（RAG）

## 概述

HierarchicalMemory 是 Loom Agent 的高级记忆系统，实现了类似人类记忆的分层架构，并支持基于向量数据库的语义检索（RAG）。

### 核心特性

- **4 层记忆架构**: Ephemeral → Working → Session → Long-term
- **语义检索（RAG）**: 基于向量相似度的智能检索
- **自动晋升机制**: Working Memory → Long-term Memory 智能流转
- **工具记忆管理**: 临时存储工具调用中间状态，用完即丢
- **无缝集成**: 与 ContextAssembler 深度集成
- **零配置启动**: 无需向量数据库也能使用（关键词检索降级）

---

## 记忆层级详解

### 1. Ephemeral Memory（临时记忆）

**用途**: 工具调用的中间状态，执行完成后自动清除

**生命周期**:
```
工具调用开始 → 记录中间状态 → 工具执行 → 保存最终结果到 Session → 清除临时记忆
```

**特点**:
- 基于 Key-Value 存储（Dict）
- 不持久化
- 不参与自动晋升
- 用于避免污染对话历史

**示例**:
```python
# 工具调用开始
await memory.add_ephemeral(
    key="tool_call_123",
    content="Calling search_api with query='Python tutorials'",
    metadata={"status": "in_progress"}
)

# 工具执行完成，清理临时记忆
await memory.clear_ephemeral(key="tool_call_123")
```

---

### 2. Working Memory（工作记忆）

**用途**: Agent 当前关注的短期重要信息

**容量**: 可配置（默认 10 条），超出后自动晋升到 Long-term

**特点**:
- 从 Session Memory 自动提取关键信息
- 支持自动晋升到 Long-term Memory
- 适合存储"最近关注的重要事实"

**示例**:
```python
memory = HierarchicalMemory(
    working_memory_size=10,  # 最多保留 10 条
    auto_promote=True,       # 启用自动晋升
)

# Working Memory 会自动从对话中提取
# 当容量超限时，最旧的记忆会晋升到 Long-term
```

---

### 3. Session Memory（会话记忆）

**用途**: 当前对话的完整历史

**容量**: 可配置（默认 100 条），超出后触发压缩

**特点**:
- 存储 `List[Message]`（兼容现有 BaseMemory 接口）
- 完整保留对话上下文
- 参与 ContextAssembler 的上下文组装

**示例**:
```python
# 添加消息到 Session Memory
async for event in memory.add_message_stream(message):
    print(event)

# 获取最近 N 条
session_msgs = await memory.get_by_tier("session", limit=20)
```

---

### 4. Long-term Memory（长期记忆）

**用途**: 跨会话的持久化知识（用户画像、领域知识等）

**容量**: 无限制（受存储空间限制）

**特点**:
- 支持向量化存储（Embedding）
- 支持语义检索（RAG）
- 可持久化到磁盘
- 自动从 Working Memory 晋升

**示例**:
```python
# 手动添加到长期记忆
await memory.add_to_longterm(
    content="用户张三是一名 Python 数据分析师，擅长 pandas 和 numpy。",
    metadata={"category": "user_profile", "importance": "high"}
)

# 语义检索
result = await memory.retrieve(
    query="用户的技术背景是什么？",
    top_k=5,
    tier="longterm"
)
```

---

## 快速开始

### 安装依赖

```bash
pip install loom-agent

# 可选：向量化能力
pip install openai  # OpenAI Embedding
pip install faiss-cpu  # FAISS 加速（可选）
```

### 基础用法（零配置）

```python
from loom.builtin.memory import HierarchicalMemory
from loom.core.message import Message

# 创建记忆系统（无需向量化，使用关键词检索）
memory = HierarchicalMemory(
    enable_persistence=False,
    auto_promote=True,
)

# 添加对话
msg = Message(role="user", content="我叫张三，是一名工程师")
async for event in memory.add_message_stream(msg):
    print(event)

# 检索（关键词匹配）
result = await memory.retrieve(query="张三是谁？", top_k=3)
print(result)
```

---

## RAG 集成（语义检索）

### 配置向量化能力

```python
from loom.builtin.memory import HierarchicalMemory
from loom.builtin.embeddings import OpenAIEmbedding
from loom.builtin.vector_store import InMemoryVectorStore

# 1. 创建 Embedding 模型
embedding = OpenAIEmbedding(
    model="text-embedding-3-small",  # 或 "text-embedding-3-large"
    api_key="your_openai_api_key",  # 或通过 OPENAI_API_KEY 环境变量
)

# 2. 创建向量存储
vector_store = InMemoryVectorStore(
    dimension=1536,  # text-embedding-3-small 的维度
    use_faiss=True,  # 使用 FAISS 加速（可选）
)
await vector_store.initialize()

# 3. 创建 HierarchicalMemory
memory = HierarchicalMemory(
    embedding=embedding,
    vector_store=vector_store,
    auto_promote=True,
)
```

### 语义检索示例

```python
# 添加对话（自动向量化）
conversations = [
    ("user", "我最近在学习 Rust 编程语言"),
    ("assistant", "Rust 是一门注重安全和性能的系统编程语言。"),
    ("user", "我对 WebAssembly 也很感兴趣"),
    ("assistant", "Rust 对 WASM 支持非常好！"),
]

for role, content in conversations:
    msg = Message(role=role, content=content)
    async for _ in memory.add_message_stream(msg):
        pass

# 手动添加用户画像到长期记忆
await memory.add_to_longterm(
    content="用户正在学习 Rust 和 WebAssembly，对系统编程感兴趣。",
    metadata={"category": "user_profile"}
)

# 语义检索（基于向量相似度）
result = await memory.retrieve(
    query="用户在学什么技术？",  # 语义匹配，不需要精确关键词
    top_k=3,
    tier="longterm",
)

print(result)
# 输出 XML 格式的检索结果：
# <retrieved_memory>
#   <memory tier="longterm" relevance="0.89">
#   用户正在学习 Rust 和 WebAssembly，对系统编程感兴趣。
#   </memory>
# </retrieved_memory>
```

---

## 工具记忆（Ephemeral Memory）

### AgentExecutor 自动集成

从 v0.1.8 开始，AgentExecutor 自动管理工具调用的临时记忆：

```python
from loom.core.agent_executor import AgentExecutor
from loom.builtin.memory import HierarchicalMemory

memory = HierarchicalMemory()

executor = AgentExecutor(
    agent=your_agent,
    context_manager=create_enhanced_context_manager(memory=memory),
)

# 工具调用流程（自动管理）：
# 1. 工具调用开始 → add_ephemeral(key="tool_{id}", ...)
# 2. 执行工具
# 3. 保存结果到 Session Memory
# 4. clear_ephemeral(key="tool_{id}")
```

### 手动管理工具记忆

```python
tool_id = "call_abc123"
tool_name = "search_database"

try:
    # 1. 记录工具调用开始
    await memory.add_ephemeral(
        key=f"tool_{tool_id}",
        content=f"Calling {tool_name}(query='user profile')",
        metadata={"tool_name": tool_name, "status": "in_progress"}
    )

    # 2. 执行工具
    result = await execute_tool(tool_name, args)

    # 3. 保存最终结果到 Session Memory
    result_msg = Message(role="tool", content=str(result), name=tool_name)
    async for _ in memory.add_message_stream(result_msg):
        pass

finally:
    # 4. 清理临时记忆（即使失败也要清理）
    await memory.clear_ephemeral(key=f"tool_{tool_id}")
```

---

## 自动晋升机制

### 工作原理

```
Session Message (对话消息)
        ↓
自动提取关键信息
        ↓
Working Memory (容量: N 条)
        ↓
容量超限 + auto_promote=True
        ↓
Long-term Memory
        ├─ 向量化 (Embedding)
        └─ 存入向量库 (VectorStore)
        ↓
持久化到磁盘（如果启用）
```

### 配置示例

```python
memory = HierarchicalMemory(
    working_memory_size=5,   # Working Memory 容量
    auto_promote=True,       # 启用自动晋升
    embedding=embedding,     # 晋升时自动向量化
    vector_store=vector_store,
)

# 添加多条消息
for i in range(10):
    msg = Message(role="user", content=f"Message {i}")
    async for _ in memory.add_message_stream(msg):
        pass

# 结果：
# - Working Memory: 5 条（最近的）
# - Long-term Memory: 5 条（最旧的已晋升）
```

---

## 与 ContextAssembler 集成

### EnhancedContextManager 自动集成

```python
from loom.core.context_assembler import create_enhanced_context_manager

# 创建带 Memory 的 ContextManager
context_manager = create_enhanced_context_manager(
    memory=memory,
    max_context_tokens=8000,
    enable_smart_assembly=True,
)

# 准备上下文（自动检索相关记忆）
message = Message(role="user", content="用户的技术背景是什么？")
prepared = await context_manager.prepare(message)

# 上下文组装流程：
# 1. 调用 memory.retrieve(query=message.content, top_k=5, tier="longterm")
# 2. 将检索结果作为 HIGH 优先级组件添加
# 3. 智能组装：系统提示 + 检索记忆 + 历史对话 + 当前消息
# 4. 自动截断以适应 token 预算
```

### 检索结果格式

`memory.retrieve()` 返回 XML 格式，方便 LLM 理解：

```xml
<retrieved_memory>
  <memory tier="longterm" relevance="0.92">
  用户是一名 Python 数据分析师，擅长 pandas、numpy 等工具。
  </memory>
  <memory tier="longterm" relevance="0.85">
  用户对机器学习和深度学习非常感兴趣，正在学习 PyTorch。
  </memory>
</retrieved_memory>
```

---

## 向量存储选项

### InMemoryVectorStore（默认）

**特点**:
- 零配置，开箱即用
- 基于 NumPy 实现
- 可选 FAISS 加速
- 不持久化（重启丢失）

```python
from loom.builtin.vector_store import InMemoryVectorStore

vector_store = InMemoryVectorStore(
    dimension=1536,
    use_faiss=True,  # 尝试使用 FAISS，失败则降级到 NumPy
)
await vector_store.initialize()
```

### ChromaDB（外部存储）

**特点**:
- 持久化存储
- 支持分布式部署
- 高性能

```python
# TODO: v0.1.9 将支持 ChromaDB 适配器
# from loom.builtin.vector_store import ChromaDBAdapter
```

---

## API 参考

### HierarchicalMemory

#### 构造函数

```python
HierarchicalMemory(
    embedding: Optional[BaseEmbedding] = None,
    vector_store: Optional[BaseVectorStore] = None,
    enable_persistence: bool = False,
    auto_promote: bool = True,
    working_memory_size: int = 10,
    session_memory_size: int = 100,
)
```

**参数**:
- `embedding`: Embedding 模型（可选）
- `vector_store`: 向量存储（可选）
- `enable_persistence`: 是否持久化到磁盘
- `auto_promote`: 是否启用自动晋升
- `working_memory_size`: Working Memory 容量
- `session_memory_size`: Session Memory 容量

#### 核心方法

##### `add_message_stream(message: Message) -> AsyncGenerator[AgentEvent]`

添加消息到 Session Memory，自动提取到 Working Memory。

```python
async for event in memory.add_message_stream(message):
    if event.type == AgentEventType.MEMORY_ADD_END:
        print("消息已添加")
```

##### `retrieve(query: str, top_k: int = 5, tier: Optional[str] = None) -> str`

语义检索相关记忆，返回 XML 格式结果。

```python
result = await memory.retrieve(
    query="用户的技术背景",
    top_k=5,
    tier="longterm",  # 可选："ephemeral", "working", "session", "longterm"
)
```

##### `add_to_longterm(content: str, metadata: Optional[Dict] = None) -> None`

手动添加到长期记忆并向量化。

```python
await memory.add_to_longterm(
    content="用户是 Python 开发者",
    metadata={"category": "profile", "importance": "high"}
)
```

##### `get_by_tier(tier: str, limit: Optional[int] = None) -> List[Message]`

按层级获取记忆。

```python
# 获取最近 10 条会话记忆
session_msgs = await memory.get_by_tier("session", limit=10)

# 获取所有长期记忆
longterm_msgs = await memory.get_by_tier("longterm")
```

#### Ephemeral Memory 方法

##### `add_ephemeral(key: str, content: str, metadata: Optional[Dict] = None)`

添加临时记忆（工具调用中间状态）。

```python
await memory.add_ephemeral(
    key="tool_call_123",
    content="Calling API...",
    metadata={"status": "in_progress"}
)
```

##### `get_ephemeral(key: str) -> Optional[str]`

获取临时记忆。

```python
content = await memory.get_ephemeral(key="tool_call_123")
```

##### `clear_ephemeral(key: Optional[str] = None)`

清除临时记忆（单个或全部）。

```python
# 清除单个
await memory.clear_ephemeral(key="tool_call_123")

# 清除全部
await memory.clear_ephemeral()
```

---

## 事件系统

v0.1.8 新增 RAG 相关事件：

```python
class AgentEventType(str, Enum):
    # RAG 事件
    MEMORY_RETRIEVE_START = "memory_retrieve_start"
    MEMORY_RETRIEVE_COMPLETE = "memory_retrieve_complete"
    MEMORY_VECTORIZE_START = "memory_vectorize_start"
    MEMORY_VECTORIZE_COMPLETE = "memory_vectorize_complete"

    # Ephemeral Memory 事件
    EPHEMERAL_ADD = "ephemeral_add"
    EPHEMERAL_CLEAR = "ephemeral_clear"
```

**监听事件示例**:

```python
async for event in memory.add_message_stream(message):
    if event.type == AgentEventType.MEMORY_VECTORIZE_START:
        print("开始向量化...")
    elif event.type == AgentEventType.MEMORY_VECTORIZE_COMPLETE:
        print("向量化完成")
```

---

## 最佳实践

### 1. 向量化开销优化

```python
# ✅ 好：批量向量化
contents = [msg.content for msg in messages]
embeddings = await embedding.embed_documents(contents)

# ❌ 差：逐条向量化
for msg in messages:
    emb = await embedding.embed_query(msg.content)
```

### 2. 长期记忆管理

```python
# 定期清理低价值记忆
longterm = await memory.get_by_tier("longterm")

# 删除低相关性或过期的记忆
# TODO: v0.1.9 将支持删除和更新操作
```

### 3. Token 预算控制

```python
# 使用 ContextAssembler 自动管理 token 预算
context_manager = create_enhanced_context_manager(
    memory=memory,
    max_context_tokens=8000,  # 根据模型限制调整
    enable_smart_assembly=True,
)

# 检索时限制数量
result = await memory.retrieve(query=query, top_k=3)  # 不要太多
```

### 4. 分层记忆策略

| 记忆层级 | 适用场景 | 容量建议 | 持久化 |
|---------|---------|----------|--------|
| Ephemeral | 工具调用中间状态 | 无限制（临时） | ❌ |
| Working | 当前任务关键信息 | 5-10 条 | ❌ |
| Session | 完整对话历史 | 50-100 条 | ❌ |
| Long-term | 用户画像、领域知识 | 无限制 | ✅ |

---

## 常见问题

### Q1: 不使用 OpenAI Embedding 可以吗？

**A**: 可以！HierarchicalMemory 支持零配置启动，会自动降级到关键词检索。

```python
# 无需 embedding 和 vector_store
memory = HierarchicalMemory()

# 仍然可以检索（关键词匹配）
result = await memory.retrieve(query="张三")
```

### Q2: 如何使用其他 Embedding 模型？

**A**: 实现 `BaseEmbedding` 接口即可：

```python
from loom.interfaces.embedding import BaseEmbedding

class CustomEmbedding(BaseEmbedding):
    async def embed_query(self, text: str) -> List[float]:
        # 你的实现
        pass

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # 你的实现
        pass
```

### Q3: 向量存储支持哪些数据库？

**A**: 当前支持：
- ✅ InMemoryVectorStore（默认）
- 🚧 ChromaDB（v0.1.9 计划）
- 🚧 Pinecone（v0.2.0 计划）

可通过实现 `BaseVectorStore` 接口自定义。

### Q4: 如何持久化 Long-term Memory？

**A**:

```python
memory = HierarchicalMemory(
    enable_persistence=True,
    # 默认保存到 ~/.loom/memory.json
)

# 手动保存
await memory.save()

# 手动加载
await memory.load()
```

### Q5: 自动晋升的规则是什么？

**A**:
1. Working Memory 容量超限时触发
2. 按 FIFO（先进先出）原则晋升最旧的记忆
3. 只晋升 `len(content) > 100` 的记忆（避免晋升无意义短句）
4. 晋升时自动向量化（如果配置了 embedding）

---

## 示例代码

完整示例请参考：
- `examples/hierarchical_memory_rag_example.py`

---

## 版本历史

### v0.1.8 (2024-12-15)

- ✅ 实现 4 层记忆架构
- ✅ 支持语义检索（RAG）
- ✅ 集成 OpenAI Embedding
- ✅ 实现 InMemoryVectorStore
- ✅ 自动晋升机制
- ✅ 工具记忆（Ephemeral Memory）
- ✅ 与 ContextAssembler 集成
- ✅ 新增 6 个 RAG 事件类型

### Roadmap

- 🚧 v0.1.9: ChromaDB 适配器
- 🚧 v0.2.0: 记忆删除和更新 API
- 🚧 v0.2.0: Pinecone 支持
- 🚧 v0.2.1: 混合检索（向量 + 关键词）

---

## 参考资料

- [BaseMemory Protocol](../../interfaces/memory.py)
- [ContextAssembler 集成](./context_assembler.md)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [FAISS GitHub](https://github.com/facebookresearch/faiss)
