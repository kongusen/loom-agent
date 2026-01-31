# 智能RAG（检索增强生成）功能

## 概述

Loom Agent框架现在支持智能RAG功能，允许Agent在执行任务时自动查询外部知识库，并利用Fractal Memory进行智能缓存。

## 核心特性

### 1. 按需查询
- Agent根据任务内容自动查询相关知识
- 无需手动触发，完全自动化

### 2. 智能缓存
- 使用Fractal Memory缓存查询结果
- 避免重复查询，提高效率
- 子节点可以继承父节点的知识缓存

### 3. 可配置
- `knowledge_max_items`: 每次查询返回的最大条目数（默认3，范围1-10）
- `knowledge_relevance_threshold`: 知识相关度阈值（默认0.7，范围0.0-1.0）

## 快速开始

### 1. 实现知识库提供者

```python
from loom.config.knowledge import KnowledgeBaseProvider, KnowledgeItem

class MyKnowledgeBase(KnowledgeBaseProvider):
    async def query(self, query: str, limit: int = 3) -> list[KnowledgeItem]:
        # 实现你的查询逻辑
        # 可以连接到向量数据库、Elasticsearch等
        results = []
        # ... 查询逻辑 ...
        return results
```

### 2. 配置LoomApp

```python
from loom.api import LoomApp
from loom.api.models import AgentConfig

# 创建应用
app = LoomApp()

# 配置LLM
app.set_llm_provider(your_llm_provider)

# 配置知识库
knowledge_base = MyKnowledgeBase()
app.set_knowledge_base(knowledge_base)
```

### 3. 创建Agent

```python
# 创建Agent配置
config = AgentConfig(
    agent_id="my-agent",
    name="My Agent",
    knowledge_max_items=5,  # 可选：自定义查询条目数
    knowledge_relevance_threshold=0.8,  # 可选：自定义相关度阈值
)

# 创建Agent
agent = app.create_agent(config)
```

### 4. 使用Agent

```python
from loom.protocol import Task

# 创建任务
task = Task(
    task_id="task_1",
    action="query",
    parameters={"content": "Python编程"},
)

# Agent会自动查询知识库并使用相关知识
result = await agent.execute(task)
```

## 工作原理

### 查询流程

```
Task创建 → TaskContextManager → KnowledgeContextSource
                                        ↓
                                  检查Fractal Memory缓存
                                        ↓
                            缓存命中？ ─── 是 → 返回缓存知识
                                 │
                                 否
                                 ↓
                          查询KnowledgeBase
                                 ↓
                          过滤低相关度知识
                                 ↓
                          缓存到Fractal Memory
                                 ↓
                            返回知识上下文
```

### 缓存机制

- **缓存键**: 基于查询内容的MD5哈希
- **缓存作用域**: SHARED（子节点可继承）
- **缓存格式**: JSON序列化的知识条目列表

## 配置参数

### AgentConfig参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `knowledge_max_items` | int | 3 | 每次查询返回的最大条目数（1-10） |
| `knowledge_relevance_threshold` | float | 0.7 | 知识相关度阈值（0.0-1.0） |

### KnowledgeItem属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | str | 知识条目唯一标识 |
| `content` | str | 知识内容 |
| `source` | str | 知识来源 |
| `relevance` | float | 相关度分数（0.0-1.0） |
| `metadata` | dict | 可选的元数据 |

## 示例

完整示例请参考：`examples/knowledge_rag_demo.py`

## 集成建议

### 向量数据库集成

```python
# 示例：集成Pinecone
import pinecone
from loom.config.knowledge import KnowledgeBaseProvider, KnowledgeItem

class PineconeKnowledgeBase(KnowledgeBaseProvider):
    def __init__(self, index_name: str):
        pinecone.init(api_key="your-api-key")
        self.index = pinecone.Index(index_name)

    async def query(self, query: str, limit: int = 3) -> list[KnowledgeItem]:
        # 生成查询向量
        query_vector = await self.embed(query)

        # 查询Pinecone
        results = self.index.query(
            vector=query_vector,
            top_k=limit,
            include_metadata=True
        )

        # 转换为KnowledgeItem
        items = []
        for match in results.matches:
            items.append(KnowledgeItem(
                id=match.id,
                content=match.metadata["content"],
                source=match.metadata["source"],
                relevance=match.score,
            ))

        return items
```

### Elasticsearch集成

```python
# 示例：集成Elasticsearch
from elasticsearch import AsyncElasticsearch
from loom.config.knowledge import KnowledgeBaseProvider, KnowledgeItem

class ElasticsearchKnowledgeBase(KnowledgeBaseProvider):
    def __init__(self, index_name: str):
        self.es = AsyncElasticsearch(["http://localhost:9200"])
        self.index_name = index_name

    async def query(self, query: str, limit: int = 3) -> list[KnowledgeItem]:
        # 执行全文搜索
        response = await self.es.search(
            index=self.index_name,
            body={
                "query": {
                    "match": {
                        "content": query
                    }
                },
                "size": limit
            }
        )

        # 转换为KnowledgeItem
        items = []
        for hit in response["hits"]["hits"]:
            items.append(KnowledgeItem(
                id=hit["_id"],
                content=hit["_source"]["content"],
                source=hit["_source"]["source"],
                relevance=hit["_score"] / 10.0,  # 归一化分数
            ))

        return items
```

## 最佳实践

1. **相关度阈值设置**
   - 高精度场景（如医疗、法律）：0.85-0.95
   - 一般场景：0.7-0.8
   - 探索性场景：0.5-0.7

2. **查询条目数设置**
   - 简单问答：1-3条
   - 复杂分析：3-5条
   - 综合研究：5-10条

3. **缓存策略**
   - 利用Fractal Memory的层级结构
   - 父节点查询的知识会自动缓存给子节点
   - 适合多轮对话和递归任务

4. **性能优化**
   - 使用向量数据库加速语义搜索
   - 合理设置相关度阈值，过滤无关知识
   - 利用缓存机制减少重复查询

## 故障排查

### 问题：知识库未被查询

**可能原因**：
- 任务参数中没有`content`字段
- `content`为空字符串

**解决方案**：
确保任务参数包含`content`字段：
```python
task = Task(
    task_id="task_1",
    action="query",
    parameters={"content": "你的查询内容"},  # 必须包含content
)
```

### 问题：缓存未生效

**可能原因**：
- 未提供`fractal_memory`参数
- 查询内容略有不同（缓存键基于MD5哈希）

**解决方案**：
- 确保Agent使用了Fractal Memory
- 保持查询内容完全一致以命中缓存

### 问题：返回的知识不相关

**可能原因**：
- 相关度阈值设置过低
- 知识库实现的相关度计算不准确

**解决方案**：
- 提高`knowledge_relevance_threshold`参数
- 改进知识库的相关度计算逻辑
- 使用向量相似度而不是关键词匹配

## 技术架构

### 组件关系

```
LoomApp
  ├── set_knowledge_base() → 设置全局知识库
  └── create_agent()
        ↓
      Agent
        ├── knowledge_base: KnowledgeBaseProvider
        ├── knowledge_max_items: int
        ├── knowledge_relevance_threshold: float
        └── context_manager: TaskContextManager
              └── sources: [
                    MemoryContextSource,
                    FractalMemoryContextSource,
                    KnowledgeContextSource ← 智能RAG
                  ]
```

### 数据流

```
Task → TaskContextManager.get_context()
         ↓
       KnowledgeContextSource.get_context()
         ↓
       1. 检查Fractal Memory缓存
       2. 缓存未命中 → 查询KnowledgeBase
       3. 过滤低相关度知识
       4. 缓存到Fractal Memory
       5. 返回知识上下文
         ↓
       合并到完整上下文
         ↓
       传递给LLM
```

## 相关文档

- [KnowledgeBaseProvider接口](../loom/config/knowledge.py)
- [KnowledgeContextSource实现](../loom/memory/knowledge_context.py)
- [AgentConfig配置](../loom/api/models.py)
- [完整示例](../examples/knowledge_rag_demo.py)

## 更新日志

### v4.6.0 (2026-01-31)
- ✨ 新增智能RAG功能
- ✨ 支持知识库集成
- ✨ 实现智能缓存机制
- ✨ 添加可配置的RAG参数
- ✅ 完整的测试覆盖（8个测试用例）
