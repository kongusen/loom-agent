"""
Unified Cognitive System Configuration

Consolidates configuration for the entire cognitive system (memory, context)
into a single entry point to reduce configuration nesting and simplify
initialization.

Replaces:
- Multiple config imports in builder and node initialization
- Nested config object structures (ContextConfig, CurationConfig)
- Scattered default configurations across modules
"""

from dataclasses import dataclass, field
from typing import Any

from loom.config.memory import (
    ContextConfig,
    CurationConfig,
    EmbeddingConfig,
    VectorStoreConfig,
)


@dataclass
class CognitiveSystemConfig:
    """
    Unified configuration for the cognitive system.

    Replaces the need to configure ContextConfig and CurationConfig
    separately. Provides a single entry point that initializes all
    sub-systems consistently.

    Reduces configuration nesting from:
        ContextConfig(CurationConfig(...))
    To:
        CognitiveSystemConfig(...)

    Benefits:
    - Single import: from loom.config import CognitiveSystemConfig
    - Consistent defaults across all subsystems
    - Factory methods for common configuration patterns
    - Easier testing and configuration management
    """

    # ========================================================================
    # Feature Extraction Configuration
    # ========================================================================
    # Enable QueryFeatureExtractor for consistent feature extraction
    feature_extractor_enabled: bool = True

    # Cache size for feature extraction
    feature_extractor_cache_size: int = 1024

    # ========================================================================
    # Context Configuration
    # ========================================================================
    # LLM & Tokenizer Settings
    context_model_name: str = "gpt-4"
    context_max_tokens: int = 8192

    # Tokenizer encoding (used by TokenCounter)
    context_tokenizer_encoding: str = "cl100k_base"

    # Strategy Selection
    context_strategy: str = "auto"  # 'auto', 'snippets', 'focused'

    # ========================================================================
    # Curation Configuration
    # ========================================================================
    curation_max_tokens: int = 4000
    curation_use_snippets: bool = True
    curation_focus_distance: int = 2
    curation_include_tools: bool = True
    curation_include_facts: bool = True
    curation_auto_summarize_l3: bool = True
    curation_l3_summary_threshold: int = 20

    # ========================================================================
    # Memory Tier Token Budget Allocation
    # ========================================================================
    # Percentages that should sum to 1.0
    context_tokens_budget_l4: float = 0.2  # Global Facts
    context_tokens_budget_l3: float = 0.3  # Session History
    context_tokens_budget_l2: float = 0.4  # Working Memory
    context_tokens_budget_l1: float = 0.1  # Raw IO

    # ========================================================================
    # Advanced Optimizations
    # ========================================================================
    context_enable_prompt_caching: bool = True
    context_enable_dynamic_budget: bool = True

    # ========================================================================
    # Vector Store & Embedding
    # ========================================================================
    memory_vector_store_provider: str = "inmemory"
    memory_vector_store_config: dict[str, Any] = field(default_factory=dict)
    memory_vector_store_enabled: bool = True
    memory_vector_store_batch_size: int = 100

    memory_embedding_provider: str = "mock"
    memory_embedding_config: dict[str, Any] = field(default_factory=dict)
    memory_embedding_cache_enabled: bool = True
    memory_embedding_cache_size: int = 10000
    memory_embedding_batch_size: int = 50

    # ========================================================================
    # Memory Compression
    # ========================================================================
    memory_max_l1_size: int = 50
    memory_auto_vectorize_l4: bool = True
    memory_enable_auto_compression: bool = True
    memory_l1_to_l3_threshold: int = 30
    memory_l3_to_l4_threshold: int = 50

    # ========================================================================
    # Token Counter Configuration
    # ========================================================================
    tokenizer_cache_size: int = 2048
    tokenizer_fallback_enabled: bool = True

    def get_curation_config(self) -> CurationConfig:
        """
        Build CurationConfig from this unified config.

        Returns:
            CurationConfig with all settings applied
        """
        return CurationConfig(
            max_tokens=self.curation_max_tokens,
            use_snippets=self.curation_use_snippets,
            focus_distance=self.curation_focus_distance,
            include_tools=self.curation_include_tools,
            include_facts=self.curation_include_facts,
            auto_summarize_l3=self.curation_auto_summarize_l3,
            l3_summary_threshold=self.curation_l3_summary_threshold,
        )

    def get_context_config(self) -> ContextConfig:
        """
        Build ContextConfig from this unified config.

        Returns:
            ContextConfig with all settings applied
        """
        VectorStoreConfig(
            provider=self.memory_vector_store_provider,
            provider_config=self.memory_vector_store_config.copy(),
            enabled=self.memory_vector_store_enabled,
            batch_size=self.memory_vector_store_batch_size,
        )

        EmbeddingConfig(
            provider=self.memory_embedding_provider,
            provider_config=self.memory_embedding_config.copy(),
            enable_cache=self.memory_embedding_cache_enabled,
            cache_size=self.memory_embedding_cache_size,
            batch_size=self.memory_embedding_batch_size,
        )

        curation = self.get_curation_config()

        config = ContextConfig(
            model_name=self.context_model_name,
            max_context_tokens=self.context_max_tokens,
            tokenizer_encoding=self.context_tokenizer_encoding,
            strategy=self.context_strategy,
            curation_config=curation,
            tokens_budget_l4=self.context_tokens_budget_l4,
            tokens_budget_l3=self.context_tokens_budget_l3,
            tokens_budget_l2=self.context_tokens_budget_l2,
            tokens_budget_l1=self.context_tokens_budget_l1,
            enable_prompt_caching=self.context_enable_prompt_caching,
            enable_dynamic_budget=self.context_enable_dynamic_budget,
        )

        return config

    @staticmethod
    def default() -> "CognitiveSystemConfig":
        """
        Create a default configuration with standard settings.

        This is the recommended way to get a working configuration:
            config = CognitiveSystemConfig.default()

        Returns:
            CognitiveSystemConfig with sensible defaults
        """
        config = CognitiveSystemConfig()

        # Add default router rules

        return config

    @staticmethod
    def for_performance() -> "CognitiveSystemConfig":
        """
        Create a configuration optimized for performance.

        - Smaller token budgets for faster processing
        - Reduced caching overhead
        - Simpler feature extraction

        Returns:
            CognitiveSystemConfig optimized for speed
        """
        config = CognitiveSystemConfig.default()

        # Reduce memory footprint
        config.curation_max_tokens = 2000
        config.tokenizer_cache_size = 512
        config.feature_extractor_cache_size = 256

        # Disable expensive features
        config.context_enable_prompt_caching = False
        config.memory_auto_vectorize_l4 = False
        config.memory_enable_auto_compression = False

        return config

    @staticmethod
    def for_accuracy() -> "CognitiveSystemConfig":
        """
        Create a configuration optimized for accuracy and completeness.

        - Larger token budgets for complete context
        - More aggressive caching
        - More comprehensive feature extraction

        Returns:
            CognitiveSystemConfig optimized for accuracy
        """
        config = CognitiveSystemConfig.default()

        # Increase token budgets
        config.curation_max_tokens = 8000
        config.context_max_tokens = 16000

        # More aggressive caching
        config.tokenizer_cache_size = 4096
        config.feature_extractor_cache_size = 4096

        # Enable all optimizations
        config.context_enable_prompt_caching = True
        config.context_enable_dynamic_budget = True
        config.memory_auto_vectorize_l4 = True

        return config

    @staticmethod
    def for_testing() -> "CognitiveSystemConfig":
        """
        Create a configuration for testing purposes.

        - Minimal token budgets for fast test execution
        - Disabled expensive operations
        - Mock providers

        Returns:
            CognitiveSystemConfig suitable for testing
        """
        config = CognitiveSystemConfig()

        # Minimal budgets
        config.curation_max_tokens = 500
        config.context_max_tokens = 1000
        config.memory_max_l1_size = 5

        # Disable expensive features
        config.memory_auto_vectorize_l4 = False
        config.memory_enable_auto_compression = False
        config.context_enable_prompt_caching = False

        # Use mock providers
        config.memory_embedding_provider = "mock"
        config.memory_vector_store_provider = "inmemory"

        # Add test rules

        return config

    @staticmethod
    def fast_mode() -> "CognitiveSystemConfig":
        """
        [DEPRECATED] Create a configuration optimized for fast mode.
        """
        # Kept for backward compatibility but effectively standard
        config = CognitiveSystemConfig.default()
        config.curation_max_tokens = 500
        config.context_max_tokens = 2000
        return config

    @staticmethod
    def deep_mode() -> "CognitiveSystemConfig":
        """
        [DEPRECATED] Create a configuration optimized for deep mode.
        """
        config = CognitiveSystemConfig.default()
        config.curation_max_tokens = 8000
        config.context_max_tokens = 16000
        config.context_enable_dynamic_budget = True
        return config

    # Removed specific S1/S2 context config getters to enforce unified context

    def validate(self) -> bool:
        """
        Validate configuration consistency.

        Returns:
            True if configuration is valid
            Raises ValueError if invalid
        """
        # Validate token budget allocation
        total_budget = (
            self.context_tokens_budget_l4
            + self.context_tokens_budget_l3
            + self.context_tokens_budget_l2
            + self.context_tokens_budget_l1
        )

        if not (0.95 < total_budget < 1.05):  # Allow small floating point error
            raise ValueError(
                f"Token budget allocation must sum to 1.0, got {total_budget}"
            )

        # Validate thresholds
            raise ValueError(
            )

        # Validate positive integers
        if self.curation_max_tokens <= 0:
            raise ValueError("curation_max_tokens must be positive")
        if self.context_max_tokens <= 0:
            raise ValueError("context_max_tokens must be positive")

        return True


# Convenience alias for shorter import
CognitiveConfig = CognitiveSystemConfig
