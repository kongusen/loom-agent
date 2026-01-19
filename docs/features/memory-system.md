# Memory System

## Overview

Loom implements a **four-layer hierarchical memory system (L1-L4)** inspired by human cognitive architecture. This system enables agents to maintain context across conversations, learn from experience, and retrieve relevant information efficiently.

The memory system solves **Temporal Entropy** (Coherence Decay) by metabolizing raw experience into structured knowledge, ensuring agents can operate indefinitely without context degradation.

## Core Concept: Metabolic Memory

Just as biological organisms metabolize food into energy and waste, Loom metabolizes **Experience** into **Knowledge** and **Noise**.

- **Experience**: Raw stream of interactions (messages, tool outputs, events)
- **Knowledge**: Distilled facts, plans, and insights worth retaining
- **Noise**: Transient information with no long-term value

The system automatically moves information through a digestion process, retaining signal and excreting noise.

## Memory Hierarchy

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ L1: Working Memory (Recent Context)                     │
│ • Capacity: 10 items                                     │
│ • Retention: 1 hour                                      │
│ • Auto-included in every LLM call                        │
└─────────────────────────────────────────────────────────┘
                         ↓ (promotion)
┌─────────────────────────────────────────────────────────┐
│ L2: Session Memory (Important Tasks)                    │
│ • Capacity: 50 items                                     │
│ • Retention: 24 hours                                    │
│ • Accessible via search tools                            │
└─────────────────────────────────────────────────────────┘
                         ↓ (promotion)
┌─────────────────────────────────────────────────────────┐
│ L3: Episodic Memory (Cross-Session Events)              │
│ • Capacity: 200 items                                    │
│ • Retention: 7 days                                      │
│ • Accessible via search tools                            │
└─────────────────────────────────────────────────────────┘
                         ↓ (promotion)
┌─────────────────────────────────────────────────────────┐
│ L4: Semantic Memory (Long-Term Knowledge)               │
│ • Capacity: 1000 items                                   │
│ • Retention: Permanent                                   │
│ • Vector search enabled                                  │
└─────────────────────────────────────────────────────────┘
```

### Layer Comparison

| Layer | Name | Purpose | Retention | Capacity | Access Method |
|-------|------|---------|-----------|----------|---------------|
| **L1** | Working Memory | Current conversation context | 1 hour | 10 items | Auto-included |
| **L2** | Session Memory | Important session events | 24 hours | 50 items | Tool search |
| **L3** | Episodic Memory | Cross-session events | 7 days | 200 items | Tool search |
| **L4** | Semantic Memory | Long-term knowledge | Permanent | 1000 items | Vector search |

## Metabolic Process

The memory system follows a natural metabolic flow:

1. **Ingest (L1)**: New information enters L1 as raw, unprocessed tasks
2. **Digest (L2)**: Frequently accessed items are promoted to L2 working memory
3. **Assimilate (L3)**: Important events are consolidated into episodic memory
4. **Sediment (L4)**: High-value insights are compressed and vectorized for long-term storage

### Automatic Promotion

Tasks are automatically promoted between layers based on access patterns:

```python
# Promotion thresholds (configurable)
L1 → L2: access_count >= 3
L2 → L3: access_count >= 5
L3 → L4: access_count >= 10
```

### Compression

When layers reach capacity, older items are compressed:

```python
# Full task format (L1/L2)
{
    "task_id": "task_123",
    "action": "file_read",
    "parameters": {"path": "/data/file.txt"},
    "result": "File content: ..."
}

# Compressed format (L3/L4)
"Read file /data/file.txt successfully"
```

## Layer Details

### L1: Working Memory

**Purpose**: Maintains immediate conversation context.

**Characteristics**:
- **Circular buffer**: Automatically evicts oldest items when full
- **Auto-included**: Always included in LLM context (no tool call needed)
- **Fast access**: In-memory storage for instant retrieval
- **Short retention**: 1 hour by default

**Use Cases**:
- Current conversation turns
- Recent tool calls and results
- Immediate context for decision-making

**Configuration**:
```python
from loom.config.memory import MemoryConfig, MemoryLayerConfig

memory_config = MemoryConfig(
    l1=MemoryLayerConfig(
        capacity=10,
        retention_hours=1,
        auto_compress=True,
        promote_threshold=3
    )
)
```

### L2: Session Memory

**Purpose**: Stores important events from the current session.

**Characteristics**:
- **Priority-based**: Items promoted from L1 based on access frequency
- **Tool-accessible**: LLM can search L2 using `search_l2_memory` tool
- **Compressed format**: Stored as concise statements
- **Medium retention**: 24 hours by default

**Promotion Criteria**:
- Access count ≥ 3 (configurable)
- Marked as important by LLM
- Contains critical information (errors, decisions)

**Configuration**:
```python
memory_config = MemoryConfig(
    l2=MemoryLayerConfig(
        capacity=50,
        retention_hours=24,
        auto_compress=True,
        promote_threshold=5
    )
)
```

### L3: Episodic Memory

**Purpose**: Preserves significant events across multiple sessions.

**Characteristics**:
- **Cross-session**: Survives beyond single conversation
- **Event-based**: Stores complete task records
- **Searchable**: Full-text and semantic search
- **Long retention**: 7 days by default

**Configuration**:
```python
memory_config = MemoryConfig(
    l3=MemoryLayerConfig(
        capacity=200,
        retention_hours=168,  # 7 days
        auto_compress=True,
        promote_threshold=10
    )
)
```

### L4: Semantic Memory

**Purpose**: Long-term knowledge base with semantic search capabilities.

**Characteristics**:
- **Permanent storage**: No automatic eviction
- **Vector search**: Embedding-based semantic retrieval
- **Compressed knowledge**: Consolidated facts and learnings
- **No promotion**: Terminal layer in hierarchy

**Configuration**:
```python
memory_config = MemoryConfig(
    l4=MemoryLayerConfig(
        capacity=1000,
        retention_hours=None,  # Permanent
        auto_compress=False,
        promote_threshold=0  # No promotion from L4
    )
)
```

## Memory Operations

### Automatic Operations

**L1 Auto-Inclusion**:
```python
# L1 is automatically included in every LLM call
messages = context_manager.build_context(current_task)
# L1 tasks are already in messages
```

### Tool-Based Access

**Search L2 Memory**:
```python
{
    "tool": "search_l2_memory",
    "arguments": {
        "query": "user preferences",
        "limit": 5
    }
}
```

**Search L3 Memory**:
```python
{
    "tool": "search_l3_memory",
    "arguments": {
        "query": "previous configurations",
        "limit": 5
    }
}
```

**Search L4 Memory (Semantic)**:
```python
{
    "tool": "search_l4_memory",
    "arguments": {
        "query": "how to authenticate API requests",
        "limit": 5
    }
}
```

## Vector Search

### Overview

L4 memory supports **semantic search** using embeddings and vector similarity.

**Architecture**:
```
Query → Embedding → Vector Search → Ranked Results
```

### Embedding Providers

**OpenAI Embeddings (Default)**:
```python
from loom.providers.embedding.openai import OpenAIEmbeddingProvider

embedding_provider = OpenAIEmbeddingProvider(
    api_key="your-api-key",
    model="text-embedding-3-small"
)
```

### Vector Stores

**In-Memory Store (Default)**:
```python
from loom.memory.vector_store import InMemoryVectorStore

vector_store = InMemoryVectorStore()
```

## External Knowledge Base

### Overview

Loom supports **external knowledge bases** that integrate with the memory system.

**Position in Context**:
```
System Prompt → L1 Memory → External Knowledge → Tools → User Question
```

### Built-in Implementations

**In-Memory Knowledge Base**:
```python
from loom.providers.knowledge import InMemoryKnowledgeBase

kb = InMemoryKnowledgeBase()
kb.add_item(KnowledgeItem(
    id="kb_1",
    content="API authentication uses Bearer tokens",
    source="API docs"
))
```

**Vector Knowledge Base**:
```python
from loom.providers.knowledge import VectorKnowledgeBase

kb = VectorKnowledgeBase(
    embedding_provider=embedding_provider,
    vector_store=vector_store
)
```

**Graph Knowledge Base**:
```python
from loom.providers.knowledge import GraphKnowledgeBase

kb = GraphKnowledgeBase(
    graph_rag_service=graph_service,
    search_mode="hybrid",  # vector, graph, or hybrid
    max_hops=2
)
```

### Configuration

```python
memory_config = MemoryConfig(
    knowledge_base=kb,
    enable_auto_migration=True,
    enable_compression=True
)
```

## Complete Example

```python
from loom.api import LoomApp, AgentConfig
from loom.config.memory import MemoryConfig, MemoryLayerConfig, MemoryStrategyType
from loom.providers.embedding.openai import OpenAIEmbeddingProvider
from loom.memory.vector_store import InMemoryVectorStore
from loom.providers.knowledge import VectorKnowledgeBase

# 1. Create embedding provider
embedding_provider = OpenAIEmbeddingProvider(
    api_key="your-api-key",
    model="text-embedding-3-small"
)

# 2. Create vector store
vector_store = InMemoryVectorStore()

# 3. Create knowledge base
knowledge_base = VectorKnowledgeBase(
    embedding_provider=embedding_provider,
    vector_store=vector_store
)

# 4. Configure memory system
memory_config = MemoryConfig(
    strategy=MemoryStrategyType.SIMPLE,
    l1=MemoryLayerConfig(capacity=10, retention_hours=1),
    l2=MemoryLayerConfig(capacity=50, retention_hours=24),
    l3=MemoryLayerConfig(capacity=200, retention_hours=168),
    l4=MemoryLayerConfig(capacity=1000, retention_hours=None),
    knowledge_base=knowledge_base,
    enable_auto_migration=True,
    enable_compression=True
)

# 5. Create agent with memory
agent_config = AgentConfig(
    name="memory_agent",
    system_prompt="You are an AI assistant with long-term memory",
    memory=memory_config
)

app = LoomApp()
agent = app.create_agent(agent_config)
```

## Best Practices

### Memory Configuration

1. **Start with defaults**: The default configuration works well for most use cases
2. **Adjust capacity based on use case**: Increase L4 capacity for knowledge-intensive applications
3. **Enable compression**: Keeps memory footprint manageable
4. **Use appropriate strategy**: Simple for general use, importance-based for critical applications

### Performance Optimization

1. **L1 auto-inclusion**: Ensures fast context building without search overhead
2. **Lazy L2/L3/L4 access**: Only search when needed via tools
3. **Vector search for L4**: Use semantic search for large knowledge bases
4. **Batch operations**: Add multiple items to L4 in batches when possible

### Memory Hygiene

1. **Regular cleanup**: Set appropriate retention times for each layer
2. **Compression**: Enable auto-compression to prevent memory bloat
3. **Promotion thresholds**: Adjust based on access patterns
4. **Monitor capacity**: Track memory usage and adjust limits as needed

## Related Documentation

- [Context Management](../framework/context-management.md)
- [Search & Retrieval](search-and-retrieval.md)
- [External Knowledge Base](external-knowledge-base.md)
- [API Reference](../usage/api-reference.md)
