# L2-L4层记忆获取指南

## 核心机制

### 记忆层级

```
L1: 最近对话（自动包含）
L2: 重要任务（主动查询）
L3: 任务摘要（主动查询）
L4: 全局知识（主动查询/语义搜索）
```

### 获取策略

- **L1**：框架自动包含在上下文中
- **L2-L4**：LLM通过工具主动查询

## 方式1：传统查询（直接获取完整内容）

### L2记忆查询

**工具**：`query_l2_memory`

**功能**：查询重要任务，返回压缩陈述句

**LLM调用示例**：
```json
{
  "tool": "query_l2_memory",
  "arguments": {
    "limit": 10
  }
}
```

**返回格式**（压缩陈述句）：
```json
{
  "layer": "L2",
  "description": "Important tasks",
  "count": 3,
  "statements": [
    "执行了file_read操作，参数{'path': '/config.json'}，结果配置已加载",
    "执行了api_call操作，参数{'endpoint': '/api/data'}，结果数据已获取",
    "执行了data_process操作，参数{'type': 'transform'}，结果处理完成"
  ]
}
```

### L3记忆查询

**工具**：`query_l3_memory`

**功能**：查询任务摘要，返回高度压缩陈述句

**LLM调用示例**：
```json
{
  "tool": "query_l3_memory",
  "arguments": {
    "limit": 20
  }
}
```

**返回格式**（高度压缩）：
```json
{
  "layer": "L3",
  "description": "Task summaries",
  "count": 5,
  "statements": [
    "file_read: 配置文件读取成功",
    "api_call: 数据获取完成",
    "data_process: 数据转换完成"
  ]
}
```

### L4记忆查询（语义搜索）

**工具**：`search_l4_memory`

**功能**：基于embedding的语义搜索，查找相关任务

**LLM调用示例**：
```json
{
  "tool": "search_l4_memory",
  "arguments": {
    "query": "查找所有文件读取相关的操作",
    "limit": 5
  }
}
```

**返回格式**（极简压缩）：
```json
{
  "layer": "L4",
  "description": "Semantic search results",
  "count": 3,
  "statements": [
    "file_read完成",
    "config_load执行",
    "data_fetch完成"
  ]
}
```

**特点**：
- 使用embedding向量进行语义匹配
- 不需要精确关键词，理解查询意图
- 适合查找历史相关任务

## 方式2：索引查询（推荐，节省50-70% token）

### 核心思想

**两阶段查询**：
1. 阶段1：列出索引+简短预览（减少token）
2. 阶段2：根据索引选择完整内容（精确控制）

### L2索引查询

**阶段1：列出索引**

```json
{
  "tool": "list_l2_memory",
  "arguments": {
    "limit": 10
  }
}
```

**返回**（只有索引和预览）：
```json
{
  "layer": "L2",
  "count": 10,
  "items": [
    {"index": 1, "preview": "file_read(path=...)", "importance": 0.8},
    {"index": 2, "preview": "file_write(path=...)", "importance": 0.7},
    {"index": 3, "preview": "api_call(endpoint=...)", "importance": 0.9}
  ],
  "hint": "Use select_memory_by_index([1,3]) to get full content"
}
```

**阶段2：选择索引**

```json
{
  "tool": "select_memory_by_index",
  "arguments": {
    "layer": "L2",
    "indices": [1, 3, 5]
  }
}
```

**返回**（完整陈述句）：
```json
{
  "layer": "L2",
  "count": 3,
  "selected": [
    {"index": 1, "statement": "执行了file_read操作，参数{'path': '/config.json'}，结果配置已加载"},
    {"index": 3, "statement": "执行了api_call操作，参数{'endpoint': '/api/data'}，结果数据已获取"},
    {"index": 5, "statement": "执行了data_process操作，参数{'type': 'transform'}，结果处理完成"}
  ]
}
```

### L3索引查询

**阶段1：列出索引**

```json
{
  "tool": "list_l3_memory",
  "arguments": {
    "limit": 20
  }
}
```

**返回**（索引+预览）：
```json
{
  "layer": "L3",
  "count": 20,
  "items": [
    {"index": 1, "preview": "file_read", "tags": ["config", "init"]},
    {"index": 2, "preview": "data_process", "tags": ["transform"]}
  ]
}
```

**阶段2：选择索引**（同L2，使用`select_memory_by_index`）

### Token节省对比

| 场景 | 传统方式 | 索引方式 | 节省 |
|------|---------|---------|------|
| 查询10项L2 | ~500 tokens | ~100 tokens | 80% |
| 选择3项 | 已包含 | ~150 tokens | - |
| **总计** | **500 tokens** | **250 tokens** | **50%** |

**优势**：
- LLM只需输出索引号（如`[1,3,5]`），大幅减少输出token
- 精确控制获取哪些内容
- 适合需要浏览后选择的场景

## 使用建议

### 何时使用传统查询

- 需要快速获取所有内容
- 记忆项数量少（<5项）
- 不确定需要哪些内容

### 何时使用索引查询（推荐）

- 需要浏览后选择
- 记忆项数量多（>5项）
- 关注token成本优化

## 工具注册

### 注册传统查询工具

```python
from loom.tools.context_tools import create_all_context_tools

# 创建所有上下文查询工具
context_tools = create_all_context_tools()

# 注册到agent
for tool in context_tools:
    agent.register_tool(tool)
```

### 注册索引查询工具

```python
from loom.tools.index_context_tools import (
    create_all_index_context_tools,
    IndexContextToolExecutor
)

# 创建索引工具
index_tools = create_all_index_context_tools()
index_executor = IndexContextToolExecutor(memory=agent.memory)

# 注册到agent
for tool in index_tools:
    agent.register_tool(tool, index_executor.execute)
```

## 总结

### 记忆获取机制

| 层级 | 获取方式 | 压缩程度 | 适用场景 |
|------|---------|---------|---------|
| L1 | 自动包含 | 无压缩 | 最近对话 |
| L2 | 主动查询 | 中等压缩 | 重要任务 |
| L3 | 主动查询 | 高度压缩 | 任务摘要 |
| L4 | 语义搜索 | 极简压缩 | 历史知识 |

### 推荐方案

**默认使用索引查询**：节省50-70% token，提高效率

**工具组合**：
- `list_l2_memory` + `select_memory_by_index` (L2层)
- `list_l3_memory` + `select_memory_by_index` (L3层)
- `search_l4_memory` (L4层语义搜索)

---

**文档完成时间**：2026-01-19
