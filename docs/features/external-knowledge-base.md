# External Knowledge Base

## Overview

Loom supports **external knowledge bases** that seamlessly integrate with the memory system, providing agents with access to domain-specific knowledge, documentation, and facts.

**Key Benefits**:
- Inject domain knowledge into agent context
- Separate knowledge from conversation memory
- Support multiple knowledge sources (documents, APIs, databases)
- Automatic or on-demand knowledge retrieval

## Position in Context

External knowledge is positioned strategically in the context structure:

```
System Prompt → L1 Memory → External Knowledge → Tools → User Question
```

**Rationale**:
- **After L1 Memory**: Conversation context comes first
- **Before Tools**: Knowledge informs tool usage
- **System Role**: Knowledge presented as system information

## Interface

### KnowledgeBaseProvider

**Location**: `loom/config/knowledge.py`

**Purpose**: Abstract interface for all knowledge base implementations.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class KnowledgeItem:
    """Knowledge entry"""
    id: str
    content: str  # Knowledge content
    source: str   # Source (document, API, database)
    relevance: float = 0.0  # Relevance score (0.0-1.0)
    metadata: dict[str, Any] = field(default_factory=dict)

class KnowledgeBaseProvider(ABC):
    """External knowledge base provider interface"""

    @abstractmethod
    async def query(
        self,
        query: str,
        limit: int = 5,
        filters: dict[str, Any] | None = None
    ) -> list[KnowledgeItem]:
        """Query knowledge base"""
        pass

    @abstractmethod
    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None:
        """Get knowledge entry by ID"""
        pass
```

## Built-in Implementations

### InMemoryKnowledgeBase

**Purpose**: Simple keyword-based knowledge base for development and testing.

**Location**: `loom/providers/knowledge/memory.py`

**Features**:
- Keyword matching
- Fast in-memory storage
- No external dependencies
- Ideal for prototyping

**Usage**:
```python
from loom.providers.knowledge import InMemoryKnowledgeBase
from loom.config.knowledge import KnowledgeItem

kb = InMemoryKnowledgeBase()

# Add knowledge items
kb.add_item(KnowledgeItem(
    id="kb_1",
    content="API authentication uses Bearer tokens in the Authorization header",
    source="API Documentation"
))

kb.add_item(KnowledgeItem(
    id="kb_2",
    content="Rate limit is 100 requests per minute",
    source="API Documentation"
))

# Query
results = await kb.query("authentication", limit=5)
```

### VectorKnowledgeBase

**Purpose**: Semantic search using embeddings for production use.

**Location**: `loom/providers/knowledge/vector.py`

**Features**:
- Semantic understanding
- High recall rate
- Embedding-based similarity
- Production-ready

**Usage**:
```python
from loom.providers.knowledge import VectorKnowledgeBase
from loom.providers.embedding.openai import OpenAIEmbeddingProvider
from loom.memory.vector_store import InMemoryVectorStore

# Create components
embedding_provider = OpenAIEmbeddingProvider(api_key="your-key")
vector_store = InMemoryVectorStore()

# Create knowledge base
kb = VectorKnowledgeBase(
    embedding_provider=embedding_provider,
    vector_store=vector_store
)

# Add items (automatically generates embeddings)
await kb.add_item(KnowledgeItem(
    id="kb_1",
    content="API authentication uses Bearer tokens",
    source="API Docs"
))

# Query (semantic search)
results = await kb.query("how to authenticate", limit=5)
```

### GraphKnowledgeBase

**Purpose**: Advanced hybrid search combining vector similarity and graph traversal.

**Location**: `loom/providers/knowledge/graph.py`

**Features**:
- Hybrid search (vector + graph)
- Multi-hop graph expansion
- Automatic reranking
- Configurable weights

**Usage**:
```python
from loom.providers.knowledge import GraphKnowledgeBase

kb = GraphKnowledgeBase(
    graph_rag_service=graph_service,
    search_mode="hybrid",  # "vector", "graph", or "hybrid"
    max_hops=2,
    vector_weight=0.5,
    graph_weight=0.5,
    rerank_enabled=True
)

# Query (hybrid search with graph expansion)
results = await kb.query("API authentication flow", limit=5)
```

**Comparison**:

| Implementation | Search Method | Use Case | Performance |
|----------------|---------------|----------|-------------|
| InMemory | Keyword matching | Development/Testing | Fast |
| Vector | Semantic similarity | Production | Medium |
| Graph | Hybrid (vector+graph) | Complex knowledge | Slower but comprehensive |

## Query Modes

### Auto-Query Mode (Recommended)

**Mechanism**: Framework automatically queries knowledge base when building context.

**Advantages**:
- No LLM tool call required
- Guaranteed knowledge availability
- Faster response time
- Similar to L1 auto-inclusion

**Best For**:
- Small knowledge bases (<1000 items)
- Fast queries (<100ms)
- High relevance knowledge

**Configuration**:
```python
from loom.config.memory import MemoryConfig

memory_config = MemoryConfig(
    knowledge_base=kb,  # Automatically queried
    enable_auto_migration=True
)
```

### Tool-Based Mode

**Mechanism**: LLM actively calls tool to query knowledge base.

**Advantages**:
- LLM decides when to query
- Reduces unnecessary queries
- More flexible

**Best For**:
- Large knowledge bases (>1000 items)
- Expensive queries
- Uncertain relevance

**Implementation**:
```python
# Register knowledge query tool
def query_knowledge_tool(query: str, limit: int = 5):
    return await knowledge_base.query(query, limit)

agent.register_tool("query_knowledge", query_knowledge_tool)
```

## Complete Example

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.config.memory import MemoryConfig
from loom.providers.knowledge import VectorKnowledgeBase
from loom.providers.embedding.openai import OpenAIEmbeddingProvider
from loom.memory.vector_store import InMemoryVectorStore
from loom.config.knowledge import KnowledgeItem

# 1. Create LLM provider
llm = OpenAIProvider(api_key="your-api-key")

# 2. Create embedding provider
embedding_provider = OpenAIEmbeddingProvider(
    api_key="your-api-key",
    model="text-embedding-3-small"
)

# 3. Create vector store
vector_store = InMemoryVectorStore()

# 4. Create and populate knowledge base
kb = VectorKnowledgeBase(
    embedding_provider=embedding_provider,
    vector_store=vector_store
)

# Add knowledge items
await kb.add_item(KnowledgeItem(
    id="auth_1",
    content="API authentication requires Bearer token in Authorization header",
    source="API Documentation"
))

await kb.add_item(KnowledgeItem(
    id="rate_1",
    content="Rate limit is 100 requests per minute per API key",
    source="API Documentation"
))

# 5. Configure agent with knowledge base
memory_config = MemoryConfig(knowledge_base=kb)

# 6. Create agent
agent = Agent.create(
    llm,
    node_id="api_assistant",
    system_prompt="You are an API documentation assistant",
    memory_config=memory_config
)

# Knowledge is automatically included in context
```

## Best Practices

### Knowledge Base Design

1. **Keep items focused**: One concept per knowledge item
2. **Use clear language**: Write for semantic search
3. **Include context**: Add source and metadata
4. **Avoid duplication**: Merge similar items

### Performance Optimization

1. **Choose appropriate implementation**: InMemory for dev, Vector for production
2. **Optimize query speed**: Keep queries under 100ms for auto-query mode
3. **Limit result count**: Return only most relevant items (3-5)
4. **Cache embeddings**: Reuse embeddings when possible

### Integration Tips

1. **Start with auto-query**: Simplest and fastest for most cases
2. **Monitor relevance**: Track if returned knowledge is useful
3. **Adjust limits**: Tune result count based on token budget
4. **Combine with memory**: Knowledge complements L1-L4 memory

## Related Documentation

- [Memory System](memory-system.md)
- [Context Management](../framework/context-management.md)
- [Search & Retrieval](search-and-retrieval.md)
- [API Reference](../usage/api-reference.md)

