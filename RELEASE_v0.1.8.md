# Loom Agent v0.1.8 Release Notes

> **发布日期**: 2024-12-15
> **版本**: 0.1.8
> **重大更新**: HierarchicalMemory + RAG 集成 - 类人记忆架构

---

## 🎯 核心特性

### 🧠 分层记忆系统（Hierarchical Memory）

v0.1.8 引入了革命性的**分层记忆系统**，模仿人类认知架构，结合**检索增强生成（RAG）**实现语义知识检索。

**4 层记忆架构**：
```
Ephemeral Memory  → 工具调用临时状态（用完即丢）
Working Memory    → Agent 短期关注（自动晋升）
Session Memory    → 完整对话历史
Long-term Memory  → 跨会话持久化知识（向量检索）
```

**关键优势**：
- ✅ 零配置启动（无需向量数据库，关键词检索降级）
- ✅ 100% 向后兼容（现有 Memory 实现无需修改）
- ✅ 优雅降级（FAISS/Embedding 可选）
- ✅ Stream-First 架构（完整事件可观测）
- ✅ 生产就绪（错误处理、异步、线程安全）

---

## 🚀 主要更新

### 1. BaseMemory Protocol 扩展

**文件**: `loom/interfaces/memory.py`

新增 3 个可选方法（默认实现，100% 向后兼容）：

```python
async def retrieve(query: str, top_k: int = 5, tier: str = None) -> str:
    """语义检索相关记忆，返回 XML 格式结果"""

async def add_to_longterm(content: str, metadata: dict = None) -> None:
    """添加到长期记忆并向量化"""

async def get_by_tier(tier: str, limit: int = None) -> List[Message]:
    """按层级获取记忆（ephemeral/working/session/longterm）"""
```

### 2. HierarchicalMemory 实现

**新文件**: `loom/builtin/memory/hierarchical_memory.py` (~650 lines)

完整的 4 层记忆系统实现：

**核心功能**：
- 自动晋升机制（Working → Long-term）
- 语义检索（向量搜索 + 关键词降级）
- 工具记忆管理（Ephemeral Memory）
- 持久化支持（可选）
- MemoryEntry 数据类（带 embedding 字段）

**配置示例**：
```python
from loom.builtin.memory import HierarchicalMemory
from loom.builtin.embeddings import OpenAIEmbedding
from loom.builtin.vector_store import InMemoryVectorStore

# 完整配置（带 RAG）
embedding = OpenAIEmbedding(model="text-embedding-3-small")
vector_store = InMemoryVectorStore(dimension=1536)
await vector_store.initialize()

memory = HierarchicalMemory(
    embedding=embedding,
    vector_store=vector_store,
    auto_promote=True,
    working_memory_size=10,
)

# 零配置（关键词检索）
memory = HierarchicalMemory()  # 开箱即用
```

### 3. 向量存储基础设施

#### InMemoryVectorStore

**新文件**: `loom/builtin/vector_store/in_memory_vector_store.py` (~350 lines)

- 双后端：NumPy（默认）+ FAISS（可选加速）
- 余弦相似度搜索（归一化内积）
- 元数据过滤支持
- 优雅降级（FAISS 失败自动回退 NumPy）

**性能**：
- FAISS: ~100ms (10k 向量)
- NumPy: ~500ms (10k 向量)

#### OpenAIEmbedding

**新文件**: `loom/builtin/embeddings/openai_embedding.py` (~150 lines)

- 支持 3 种模型：text-embedding-3-small, text-embedding-3-large, ada-002
- 批量 embedding 支持
- 可配置维度（3-small/3-large）
- 自动从环境变量读取 API Key

### 4. Context 系统 RAG 集成

**修改文件**:
- `loom/core/context_assembler.py` (lines 498-552)
- `loom/core/context.py` (lines 220-260)

**关键改进**：
- ✅ 自动调用 `memory.retrieve()` 检索相关知识
- ✅ RAG 结果作为 ESSENTIAL (90) 优先级组件
- ✅ **修复关键优先级问题**：RAG 必须在对话历史之前（避免 Lost in the Middle）
- ✅ 智能截断：优先保留 RAG 结果

**组装顺序**（已优化）：
```
1. System Prompt (ESSENTIAL/90)
2. RAG Retrieved Memory (ESSENTIAL/90) ⭐ 黄金位置
3. Recent Session History (HIGH/70) - 最近 5 条
4. Middle Session History (MEDIUM/50) - 6-20 条
5. Early Session History (LOW/30) - 优先截断
```

### 5. AgentExecutor 工具记忆集成

**修改文件**: `loom/core/executor.py` (lines 335-474)

**Ephemeral Memory 生命周期**（自动管理）：
```python
# 1. 工具调用开始
await memory.add_ephemeral(key=f"tool_{id}", content="Calling...")

# 2. 执行工具
result = await tool.execute(**args)

# 3. 保存结果到 Session Memory
await memory.add_message(result_message)

# 4. 清理临时记忆
await memory.clear_ephemeral(key=f"tool_{id}")
```

**优势**：
- 中间状态不污染对话历史
- 错误处理完善（所有路径都清理）
- 向后兼容（使用 hasattr 检查）

### 6. 事件系统扩展

**修改文件**: `loom/core/events.py`

新增 6 个 RAG 事件类型：
- `MEMORY_RETRIEVE_START`
- `MEMORY_RETRIEVE_COMPLETE`
- `MEMORY_VECTORIZE_START`
- `MEMORY_VECTORIZE_COMPLETE`
- `EPHEMERAL_ADD`
- `EPHEMERAL_CLEAR`

---

## 🔧 关键修复

### Critical RAG Priority Fix

**问题**：
- RAG Retrieved Memory 与 Session History 优先级相同（HIGH/70）
- 添加顺序导致 RAG 可能出现在长对话之后
- 触发 "Lost in the Middle" 现象，LLM 忽略检索知识

**解决方案**：
- RAG 优先级提升至 ESSENTIAL (90)
- 调整添加顺序：先 RAG，后 Session History
- Session History 分 3 层优先级（70/50/30）

**结果**：
- RAG 结果始终在"黄金位置"（Primacy Effect）
- 永远不会被长对话淹没
- 符合 Knowledge-First 原则

**详细说明**: 见 `docs/CONTEXT_ASSEMBLER_FINAL_FORM.md`

---

## 📚 文档和示例

### 技术文档

1. **HierarchicalMemory 完整指南**
   - 文件：`docs/guides/advanced/hierarchical_memory_rag.md` (1,100+ lines)
   - 内容：架构详解、API 参考、最佳实践、FAQ

2. **ContextAssembler 最终形态**
   - 文件：`docs/CONTEXT_ASSEMBLER_FINAL_FORM.md`
   - 内容：组装逻辑可视化、优先级系统、Lost in the Middle 分析

3. **v0.1.9 改进计划**
   - 文件：`docs/V0_1_9_IMPROVEMENT_PLAN.md`
   - 内容：智能晋升、异步向量化、调试模式

### 示例代码

**文件**: `examples/hierarchical_memory_rag_example.py` (650+ lines)

6 个渐进式示例：
1. 基础用法（零配置关键词检索）
2. RAG 语义检索（OpenAI Embedding）
3. 工具记忆（Ephemeral Memory 生命周期）
4. 自动晋升（Working → Long-term）
5. ContextAssembler 集成
6. 完整工作流（对话 + 工具 + RAG）

---

## 📊 性能指标

| 组件 | 操作 | 性能 |
|------|------|------|
| InMemoryVectorStore | 搜索 (10k 向量) | ~100ms (FAISS) / ~500ms (NumPy) |
| OpenAIEmbedding | 单次查询 | ~200-300ms |
| OpenAIEmbedding | 批量 (10 文档) | ~500-800ms |
| HierarchicalMemory | 关键词检索 | <10ms |
| HierarchicalMemory | 向量检索 | ~150-400ms |
| Memory 晋升 | Working → Long-term | ~200-400ms (含向量化) |

---

## 🔄 迁移指南

### 从 v0.1.7 到 v0.1.8

**100% 向后兼容** - 无破坏性变更，所有新功能为可选。

#### 继续使用现有 Memory

```python
# v0.1.7 代码无需修改
from loom.builtin.memory import InMemoryMemory
memory = InMemoryMemory()

# retrieve() 方法可用（返回空字符串）
result = await memory.retrieve(query="anything")  # Returns ""
```

#### 升级到 HierarchicalMemory（基础）

```python
from loom.builtin.memory import HierarchicalMemory

# 零配置（关键词检索，无向量化）
memory = HierarchicalMemory(
    enable_persistence=False,
    auto_promote=True,
)
```

#### 启用 RAG（语义检索）

```python
from loom.builtin.memory import HierarchicalMemory
from loom.builtin.embeddings import OpenAIEmbedding
from loom.builtin.vector_store import InMemoryVectorStore

embedding = OpenAIEmbedding()
vector_store = InMemoryVectorStore(dimension=1536)
await vector_store.initialize()

memory = HierarchicalMemory(
    embedding=embedding,
    vector_store=vector_store,
    auto_promote=True,
)
```

#### 工具记忆自动管理

```python
# 无需手动代码 - AgentExecutor 自动管理
context_manager = create_enhanced_context_manager(memory=memory)
agent = loom.agent(llm=llm, tools=tools, context_manager=context_manager)

# Ephemeral 生命周期自动处理
```

---

## 📈 代码统计

- **新增代码**: ~1,500 lines
  - HierarchicalMemory: ~650 lines
  - InMemoryVectorStore: ~350 lines
  - OpenAIEmbedding: ~150 lines
  - 集成代码: ~150 lines
  - __init__.py 和导出: ~50 lines
  - 事件类型: ~20 lines

- **修改代码**: ~150 lines
  - BaseMemory Protocol: +80 lines
  - ContextAssembler: ~30 lines (+ 优先级修复)
  - ContextManager: ~40 lines
  - AgentExecutor: ~100 lines (工具记忆生命周期)
  - Events: ~15 lines

- **文档**: ~1,750 lines
  - hierarchical_memory_rag.md: ~1,100 lines
  - hierarchical_memory_rag_example.py: ~650 lines

- **总计**: ~3,400 lines

---

## 🎯 架构清晰度提升

v0.1.8 显著提升了架构透明度：

1. **清晰的记忆层级**: 4 层明确分离，晋升规则显式
2. **透明的 RAG 流程**: Embedding → VectorStore → Retrieve → Context Assembly
3. **可观测的工具记忆**: Ephemeral 生命周期完整可追踪
4. **模块化组件**: Embedding、VectorStore、Memory 清晰解耦
5. **零魔法设计**: 所有降级策略明确，升级路径清晰

---

## 🐛 已知限制和未来改进

### 当前设计权衡

1. **记忆晋升**: FIFO + 长度过滤（简单但可能晋升低价值内容）
   - **v0.1.9 计划**: LLM 摘要化再晋升
   - **目标**: 存储高密度事实而非冗长片段

2. **同步向量化**: Embedding 调用阻塞主执行路径
   - **v0.1.9 计划**: 后台任务队列异步向量化
   - **目标**: 用户立即得到响应，记忆后台巩固

3. **Ephemeral 调试**: 工具执行后删除临时记忆
   - **v0.1.9 计划**: Debug 模式归档而非删除
   - **目标**: 保留中间状态用于排查幻觉

---

## 🚀 下一步（v0.1.9）

- 🔄 **智能记忆晋升**: LLM 摘要化再存储
- ⚡ **异步向量化**: 后台任务队列，非阻塞
- 🐛 **调试模式**: 归档 Ephemeral Memory 用于追溯
- 🗄️ **ChromaDB 适配器**: 外部向量数据库支持
- 🔌 **Pinecone 支持**: 云向量数据库
- 🔍 **混合检索**: 向量 + 关键词结合
- 📊 **记忆分析**: 使用统计和优化建议

---

## 👥 贡献者

- **kongusen** - 架构设计和实现
- **Community feedback** - RAG 集成需求

---

## 🔗 资源链接

- **GitHub**: https://github.com/kongusen/loom-agent
- **PyPI**: https://pypi.org/project/loom-agent/
- **文档**: [docs/guides/advanced/hierarchical_memory_rag.md](docs/guides/advanced/hierarchical_memory_rag.md)
- **示例**: [examples/hierarchical_memory_rag_example.py](examples/hierarchical_memory_rag_example.py)
- **架构说明**: [docs/CONTEXT_ASSEMBLER_FINAL_FORM.md](docs/CONTEXT_ASSEMBLER_FINAL_FORM.md)

---

## ⚖️ 许可证

MIT License

---

**结论**: v0.1.8 是一个重大的架构升级，引入了类人记忆系统和 RAG 集成，同时保持 100% 向后兼容。架构清晰、机制透明，为未来优化奠定了坚实基础。

---

**发布时间**: 2024-12-15
**版本**: 0.1.8
**状态**: ✅ 生产就绪
