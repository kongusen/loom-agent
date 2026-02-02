# Search & Retrieval

## Overview

Loom's search system enables agents to retrieve relevant information from memory layers (L2-L4) using **semantic search** powered by embeddings and vector similarity.

**Key Capabilities**:
- Semantic understanding (not just keyword matching)
- Multi-layer search (L2, L3, L4)
- Vector-based similarity
- Tool-based access for LLM

## Architecture

### Search Flow

```
Query → Embedding → Vector Search → Similarity Ranking → Results
```

**Process**:
1. **Query**: LLM provides natural language query
2. **Embedding**: Convert query to vector representation
3. **Vector Search**: Find similar vectors in memory
4. **Ranking**: Sort by cosine similarity score
5. **Results**: Return top-k most relevant items

### Search Layers

| Layer | Search Method | Use Case | Access |
|-------|---------------|----------|--------|
| L1 | Auto-included | Recent context | Automatic |
| L2 | Text/Vector | Session events | Tool: `search_l2_memory` |
| L3 | Text/Vector | Cross-session events | Tool: `search_l3_memory` |
| L4 | Vector (semantic) | Long-term knowledge | Tool: `search_l4_memory` |

## L4 Vector Search

### Primary Search Mode

L4 uses **embedding-based semantic search** as the primary mechanism.

**Advantages**:
- Understands query intent
- Finds semantically similar content
- High recall rate
- Language-agnostic

**Algorithm**: Cosine Similarity
```python
similarity = dot(query_vec, task_vec) / (norm(query_vec) * norm(task_vec))
```

### Fallback Mode

When embeddings are not configured, the system falls back to **simple text matching**:

```python
# Search in L1 and L2 for keyword matches
for task in all_tasks:
    if query in task.action or query in task.parameters:
        matches.append(task)
```

## Embedding Providers

### OpenAI Embeddings (Default)

**Model**: `text-embedding-3-small`

**Features**:
- 1536 dimensions
- Low cost
- Fast performance
- High quality

**Configuration**:
```python
from loom.providers.embedding.openai import OpenAIEmbeddingProvider

embedding_provider = OpenAIEmbeddingProvider(
    api_key="your-api-key",
    model="text-embedding-3-small"
)
```

### Custom Embeddings

Implement the `EmbeddingProvider` interface:

```python
from loom.memory.vector_store import EmbeddingProvider

class CustomEmbeddingProvider(EmbeddingProvider):
    async def embed(self, text: str) -> list[float]:
        # Your embedding logic
        return embedding_vector
```

## Vector Stores

### InMemoryVectorStore (Default)

**Features**:
- NumPy-based implementation
- Cosine similarity calculation
- In-memory storage
- Ideal for development

**Usage**:
```python
from loom.memory.vector_store import InMemoryVectorStore

vector_store = InMemoryVectorStore()
```

### Custom Vector Stores

Implement the `VectorStoreProvider` interface:

```python
from loom.memory.vector_store import VectorStoreProvider

class PineconeVectorStore(VectorStoreProvider):
    async def add(self, id: str, embedding: list[float],
                  metadata: dict | None = None) -> bool:
        # Your implementation
        pass

    async def search(self, query_embedding: list[float],
                     top_k: int = 5) -> list[VectorSearchResult]:
        # Your implementation
        pass
```

## Search Tools

### search_l2_memory

**Purpose**: Search session memory for important events.

**Usage**:
```python
# LLM calls this tool
{
    "tool": "search_l2_memory",
    "arguments": {
        "query": "user preferences",
        "limit": 5
    }
}
```

**Returns**: Compressed statements from L2 memory.

### search_l3_memory

**Purpose**: Search episodic memory for cross-session events.

**Usage**:
```python
{
    "tool": "search_l3_memory",
    "arguments": {
        "query": "previous API configurations",
        "limit": 5
    }
}
```

**Returns**: Task summaries from L3 memory.

### search_l4_memory

**Purpose**: Semantic search of long-term knowledge.

**Usage**:
```python
{
    "tool": "search_l4_memory",
    "arguments": {
        "query": "how to authenticate API requests",
        "limit": 5
    }
}
```

**Returns**: Semantically similar knowledge from L4 memory.

**Note**: This tool uses vector search and requires embedding provider configuration.

## Configuration Example

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.config.memory import MemoryConfig
from loom.providers.embedding.openai import OpenAIEmbeddingProvider
from loom.memory.vector_store import InMemoryVectorStore

# 1. Create LLM provider
llm = OpenAIProvider(api_key="your-api-key")

# 2. Create embedding provider
embedding_provider = OpenAIEmbeddingProvider(
    api_key="your-api-key",
    model="text-embedding-3-small"
)

# 3. Create vector store
vector_store = InMemoryVectorStore()

# 4. Configure memory with search enabled
memory_config = MemoryConfig(
    embedding_provider=embedding_provider,
    vector_store=vector_store,
    enable_l4_vector_search=True
)

# 5. Create agent
agent = Agent.create(
    llm,
    node_id="search_agent",
    system_prompt="You are a helpful assistant with search capabilities",
    memory_config=memory_config
)
```

## Best Practices

### Search Strategy

1. **L1 Auto-Inclusion**: Recent context is automatically included
2. **L2/L3 for Events**: Search for specific past events
3. **L4 for Knowledge**: Use semantic search for concepts and facts
4. **Limit Results**: Return 3-5 most relevant items

### Performance Optimization

1. **Enable Vector Search**: Use embeddings for L4 semantic search
2. **Optimize Embeddings**: Use fast models (text-embedding-3-small)
3. **Cache Results**: Reuse search results when possible
4. **Monitor Costs**: Track embedding API usage

### Query Design

1. **Be Specific**: Clear queries get better results
2. **Use Natural Language**: Semantic search understands intent
3. **Avoid Jargon**: Unless it's in your knowledge base
4. **Test Queries**: Verify search quality with sample queries

## Related Documentation

- [Memory System](memory-system.md)
- [Context Management](../framework/context-management.md)
- [External Knowledge Base](external-knowledge-base.md)
- [API Reference](../usage/api-reference.md)

