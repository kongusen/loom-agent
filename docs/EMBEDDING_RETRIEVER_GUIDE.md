# EmbeddingRetriever User Guide

## Overview

The `EmbeddingRetriever` provides semantic search capabilities using embeddings and vector stores. It's designed to be:
- **Universal**: Works with any domain (SQL Schema, Code, Docs, APIs, etc.)
- **Efficient**: Supports lazy loading and caching
- **Flexible**: Multiple indexing strategies and vector store backends

## Quick Start

### Basic Usage

```python
from loom.retrieval import (
    EmbeddingRetriever,
    SimpleDomainAdapter,
    IndexStrategy,
    RetrievalConfig
)
from loom.builtin.embeddings import OpenAIEmbedding
from loom.builtin.retriever import FAISSVectorStore
from loom.interfaces.retriever import Document

# 1. Prepare your documents
documents = [
    Document(
        id="doc1",
        content="Loom is an AI agent framework",
        metadata={"source": "docs"}
    ),
    Document(
        id="doc2",
        content="It supports tool calling and RAG",
        metadata={"source": "docs"}
    ),
]

# 2. Create domain adapter
adapter = SimpleDomainAdapter(documents)

# 3. Create retriever
retriever = EmbeddingRetriever(
    embedding=OpenAIEmbedding(model="text-embedding-3-small"),
    vector_store=FAISSVectorStore(dimension=1536),
    domain_adapter=adapter,
    config=RetrievalConfig(
        index_strategy=IndexStrategy.LAZY,
        top_k=5
    )
)

# 4. Initialize
await retriever.initialize()

# 5. Retrieve
results = await retriever.retrieve("What is Loom?", top_k=3)

for doc in results:
    print(f"[{doc.score:.2f}] {doc.content}")
```

## Indexing Strategies

### EAGER - Index all at initialization

Best for:
- Small to medium datasets
- Fast retrieval response time
- When all documents fit in memory

```python
config = RetrievalConfig(
    index_strategy=IndexStrategy.EAGER
)
```

**Pros**:
- Fastest retrieval
- All documents fully indexed

**Cons**:
- Slower initialization
- Higher memory usage

### LAZY - Index metadata, load on demand

Best for:
- Large datasets
- Memory-constrained environments
- When only a small subset of documents are accessed

```python
config = RetrievalConfig(
    index_strategy=IndexStrategy.LAZY
)
```

**Pros**:
- Fast initialization
- Lower memory usage
- Scales to large datasets

**Cons**:
- Slightly slower first retrieval per document
- Requires domain adapter support

### INCREMENTAL - Index on access

Best for:
- Dynamic datasets
- When documents are added frequently
- Streaming scenarios

```python
config = RetrievalConfig(
    index_strategy=IndexStrategy.INCREMENTAL
)
```

## Domain Adapters

Domain adapters allow you to adapt any data source for retrieval.

### Implementing a Custom Adapter

```python
from loom.retrieval import DomainAdapter
from loom.interfaces.retriever import Document
from typing import List

class MySchemaDomainAdapter(DomainAdapter):
    """Adapter for SQL Schema"""

    def __init__(self, data_source_id: int):
        self.data_source_id = data_source_id

    async def extract_documents(
        self,
        source=None,
        metadata_only: bool = False,
        **kwargs
    ) -> List[Document]:
        """Extract table schemas as documents"""
        tables = await self._get_tables()

        documents = []
        for table in tables:
            if metadata_only:
                # Lightweight version for lazy loading
                doc = Document(
                    id=f"table_{table}",
                    content=f"Table: {table}",
                    metadata={"table": table, "type": "table_name"}
                )
            else:
                # Full schema
                schema = await self._get_table_schema(table)
                doc = Document(
                    id=f"table_{table}",
                    content=self._format_schema(table, schema),
                    metadata={"table": table, "type": "schema"}
                )

            documents.append(doc)

        return documents

    async def load_document_details(
        self,
        document_id: str,
        **kwargs
    ) -> Document:
        """Lazy load full schema"""
        table_name = document_id.replace("table_", "")
        schema = await self._get_table_schema(table_name)

        return Document(
            id=document_id,
            content=self._format_schema(table_name, schema),
            metadata={"table": table_name, "type": "schema"}
        )

    async def _get_tables(self) -> List[str]:
        # Your logic to get table names
        pass

    async def _get_table_schema(self, table: str) -> dict:
        # Your logic to get table schema
        pass

    def _format_schema(self, table: str, schema: dict) -> str:
        # Format schema as text for embedding
        lines = [f"Table: {table}", ""]
        for column in schema.get("columns", []):
            lines.append(f"- {column['name']} ({column['type']})")
        return "\n".join(lines)
```

### Using the Custom Adapter

```python
# Create your adapter
adapter = MySchemaDomainAdapter(data_source_id=123)

# Create retriever
retriever = EmbeddingRetriever(
    embedding=OpenAIEmbedding(...),
    vector_store=FAISSVectorStore(...),
    domain_adapter=adapter,
    config=RetrievalConfig(index_strategy=IndexStrategy.LAZY)
)

# Use it
await retriever.initialize()
results = await retriever.retrieve("Find user-related tables")
```

## Vector Store Backends

### FAISS (In-Memory)

Best for development and small to medium datasets.

```python
from loom.builtin.retriever import FAISSVectorStore

# Flat index (exact search)
store = FAISSVectorStore(
    dimension=1536,
    index_type="Flat"
)

# IVF index (approximate search, faster for large datasets)
store = FAISSVectorStore(
    dimension=1536,
    index_type="IVF",
    nlist=100  # Number of clusters
)

# HNSW index (graph-based, fast approximate search)
store = FAISSVectorStore(
    dimension=1536,
    index_type="HNSW"
)
```

### Other Backends

For production use, consider:
- **Milvus**: Distributed vector database
- **Qdrant**: Cloud-native vector search
- **Chroma**: Simple persistent vector store

All backends implement the same `BaseVectorStore` interface.

## Integration with Agent

### Using with ContextRetriever

```python
from loom import agent
from loom.core.context_retriever import ContextRetriever
from loom.retrieval import EmbeddingRetriever

# Create embedding retriever
embedding_retriever = EmbeddingRetriever(
    embedding=OpenAIEmbedding(...),
    vector_store=FAISSVectorStore(...),
    domain_adapter=my_adapter
)

await embedding_retriever.initialize()

# Wrap in ContextRetriever
context_retriever = ContextRetriever(
    retriever=embedding_retriever,
    top_k=3,
    auto_retrieve=True  # Automatically inject context
)

# Create agent
my_agent = agent(
    provider="openai",
    model="gpt-4o",
    context_retriever=context_retriever
)

# Use agent - context will be automatically injected
result = await my_agent.ainvoke("Generate SQL for user orders")
```

### Manual Context Injection

```python
# Retrieve relevant context
docs = await retriever.retrieve("user orders", top_k=3)

# Format as context
context = "\n\n".join([
    f"Document {i+1}:\n{doc.content}"
    for i, doc in enumerate(docs)
])

# Use in agent
result = await my_agent.ainvoke(
    f"Context:\n{context}\n\nQuestion: Generate SQL for user orders"
)
```

## Configuration Options

### RetrievalConfig

```python
from loom.retrieval import RetrievalConfig, IndexStrategy

config = RetrievalConfig(
    # Number of documents to retrieve
    top_k=5,

    # Minimum similarity score (0-1)
    # Lower scores = more results, higher scores = more relevant
    similarity_threshold=0.7,

    # Indexing strategy
    index_strategy=IndexStrategy.LAZY,

    # Enable caching
    enable_cache=True,

    # Cache time-to-live (seconds)
    cache_ttl=3600,

    # Batch size for embedding generation
    batch_size=100
)
```

## Advanced Usage

### Metadata Filtering

```python
# Retrieve only documents matching metadata
results = await retriever.retrieve(
    query="user tables",
    top_k=5,
    filters={"category": "schema", "database": "prod"}
)
```

### Custom Embedding Format

```python
class MyAdapter(DomainAdapter):
    def format_for_embedding(self, document: Document) -> str:
        """Custom formatting for embedding generation"""
        # Include metadata in embedding
        metadata_str = ", ".join([
            f"{k}: {v}"
            for k, v in document.metadata.items()
        ])
        return f"{document.content} | {metadata_str}"
```

### Conditional Indexing

```python
class MyAdapter(DomainAdapter):
    def should_index(self, document: Document) -> bool:
        """Filter documents during indexing"""
        # Only index documents with specific metadata
        return document.metadata.get("status") == "published"
```

### Cache Management

```python
# Get current cache size
stats = retriever.get_stats()
print(f"Embedding cache: {stats['embedding_cache_size']}")
print(f"Document cache: {stats['document_cache_size']}")

# Clear caches
retriever.clear_cache()
```

### Persistence (FAISS)

```python
# Save index to disk
await store.persist("/path/to/index")

# Load index from disk
store = await FAISSVectorStore.load("/path/to/index")
```

## Performance Tips

### 1. Choose the Right Index Strategy

- **EAGER**: Use for < 10K documents
- **LAZY**: Use for > 10K documents
- **INCREMENTAL**: Use for dynamic datasets

### 2. Enable Caching

```python
config = RetrievalConfig(
    enable_cache=True,  # Cache embeddings and documents
    cache_ttl=3600      # 1 hour TTL
)
```

### 3. Use Appropriate Vector Store

- **< 100K documents**: FAISS (in-memory)
- **100K - 1M documents**: FAISS IVF or HNSW
- **> 1M documents**: Milvus or Qdrant (distributed)

### 4. Optimize Embedding Dimension

- Smaller dimensions = faster search
- Larger dimensions = better accuracy
- Use `text-embedding-3-small` (1536D) for good balance

### 5. Batch Operations

```python
# Process documents in batches
config = RetrievalConfig(
    batch_size=100  # Process 100 documents at a time
)
```

## Troubleshooting

### "FAISS not installed"

```bash
pip install faiss-cpu  # For CPU
# or
pip install faiss-gpu  # For GPU
```

### Slow initialization

- Use `IndexStrategy.LAZY` instead of `EAGER`
- Reduce `batch_size` if memory is limited
- Use simpler index type (Flat vs IVF/HNSW)

### Low retrieval accuracy

- Increase `top_k` to get more candidates
- Lower `similarity_threshold`
- Use better embedding model
- Improve document formatting in `DomainAdapter`

### High memory usage

- Use `IndexStrategy.LAZY`
- Enable caching with lower `cache_ttl`
- Use IVF or HNSW index (approximate search)
- Split large datasets across multiple indices

## Examples

See `/examples/retrieval/` for complete examples:
- `basic_usage.py`: Simple retrieval
- `custom_adapter.py`: Custom domain adapter
- `agent_integration.py`: Integration with Agent
- `performance_tuning.py`: Performance optimization

## API Reference

See the inline documentation in:
- `loom/retrieval/embedding_retriever.py`
- `loom/retrieval/domain_adapter.py`
- `loom/builtin/retriever/faiss_store.py`
