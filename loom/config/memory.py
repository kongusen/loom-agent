"""
LoomMemory Configuration
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CurationConfig:
    """
    Configuration for Context Curation strategies.
    """

    max_tokens: int = 4000  # Target maximum context size in tokens
    use_snippets: bool = True  # Whether to use Progressive Disclosure (Snippets)
    focus_distance: int = 2  # Graph distance for focus (0=self, 1=parent, 2=grandparent+)
    include_tools: bool = True  # Whether to include available tools in context
    include_facts: bool = True  # Whether to include relevant facts from L4

    # Summarization thresholds
    auto_summarize_l3: bool = True
    l3_summary_threshold: int = 20  # Number of turns before summarizing L3


@dataclass
class ContextConfig:
    """
    Global Configuration for the LoomContext system.
    """

    # LLM & Tokenizer Settings
    model_name: str = "gpt-4"
    max_context_tokens: int = 8192  # Absolute hard limit
    tokenizer_encoding: str = "cl100k_base"

    # Strategy Selection
    strategy: str = "auto"  # 'auto', 'snippets', 'focused'
    curation_config: CurationConfig = field(default_factory=CurationConfig)

    # Token Budget Allocation (Percentages 0.0 - 1.0)
    # The total of these should sum to 1.0
    # How the max_tokens should be distributed among tiers
    tokens_budget_l4: float = 0.2  # Global Facts
    tokens_budget_l3: float = 0.3  # Session History
    tokens_budget_l2: float = 0.4  # Working Memory (Target)
    tokens_budget_l1: float = 0.1  # Raw IO

    # Advanced Optimizations
    enable_prompt_caching: bool = True  # Reorder prompt for KV cache hit rate
    enable_dynamic_budget: bool = True  # Allow borrowing budget between tiers if unused


@dataclass
class VectorStoreConfig:
    """
    Configuration for Vector Store backend.
    Users can specify their preferred vector database.
    """

    # Provider type: 'inmemory', 'qdrant', 'chroma', 'postgres', or custom class path
    provider: str = "inmemory"

    # Provider-specific configuration
    provider_config: dict[str, Any] = field(default_factory=dict)

    # Examples:
    # For Qdrant:
    #   provider = "qdrant"
    #   provider_config = {
    #       "url": "http://localhost:6333",
    #       "collection_name": "loom_memory",
    #       "vector_size": 512
    #   }
    #
    # For Chroma:
    #   provider = "chroma"
    #   provider_config = {
    #       "persist_directory": "./chroma_db",
    #       "collection_name": "loom_memory"
    #   }
    #
    # For PostgreSQL + pgvector:
    #   provider = "postgres"
    #   provider_config = {
    #       "host": "localhost",
    #       "port": 5432,
    #       "database": "loom_db",
    #       "user": "loom_user",
    #       "password": "your_password",
    #       "table_name": "loom_vectors",
    #       "vector_dimensions": 512
    #   }

    # Enable/disable vector search entirely
    enabled: bool = True

    # Batch size for bulk operations
    batch_size: int = 100


@dataclass
class EmbeddingConfig:
    """
    Configuration for Embedding provider.
    Users can specify their preferred embedding service.
    """

    # Provider type: 'bge', 'openai', 'mock', or custom class path
    provider: str = "bge"

    # Provider-specific configuration
    provider_config: dict[str, Any] = field(default_factory=dict)

    # Examples:
    # For BGE (default, optimized for CPU):
    #   provider = "bge"
    #   provider_config = {
    #       "model_name": "BAAI/bge-small-zh-v1.5",
    #       "use_onnx": True,
    #       "use_quantization": True
    #   }
    #
    # For OpenAI:
    #   provider = "openai"
    #   provider_config = {
    #       "api_key": "sk-...",
    #       "model": "text-embedding-3-small",
    #       "dimensions": 1536
    #   }

    # Enable caching to avoid redundant API calls
    enable_cache: bool = True
    cache_size: int = 10000

    # Batch processing
    batch_size: int = 50


@dataclass
class MemoryConfig:
    """
    Unified configuration for the entire LoomMemory system.
    """

    # L1 Buffer Settings
    max_l1_size: int = 50

    # Vector Store
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)

    # Embedding Provider
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    # Auto-vectorization: Automatically embed and index L4 content
    auto_vectorize_l4: bool = True

    # Compression Settings
    enable_auto_compression: bool = True
    l1_to_l3_threshold: int = 30  # Compress L1 to L3 after N messages
    l3_to_l4_threshold: int = 50  # Extract facts to L4 after N L3 items
