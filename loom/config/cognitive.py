"""
Unified Cognitive System Configuration

Consolidates configuration for the entire cognitive system (routing, memory,
context) into a single entry point to reduce configuration nesting and
simplify initialization.

Replaces:
- Multiple config imports in builder and node initialization
- Nested config object structures (RouterConfig, ContextConfig, CurationConfig)
- Scattered default configurations across modules
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Pattern
import re

from loom.config.router import RouterRule, RouterConfig
from loom.config.memory import (
    CurationConfig,
    ContextConfig,
    VectorStoreConfig,
    EmbeddingConfig,
)


@dataclass
class CognitiveSystemConfig:
    """
    Unified configuration for the cognitive system.

    Replaces the need to configure RouterConfig, ContextConfig, and
    CurationConfig separately. Provides a single entry point that
    initializes all sub-systems consistently.

    Reduces configuration nesting from:
        RouterConfig + ContextConfig(CurationConfig(...))
    To:
        CognitiveSystemConfig(...)

    Benefits:
    - Single import: from loom.config import CognitiveSystemConfig
    - Consistent defaults across all subsystems
    - Factory methods for common configuration patterns
    - Easier testing and configuration management
    """

    # ========================================================================
    # Router Configuration
    # ========================================================================
    # Default system if no rules match
    router_default_system: str = "SYSTEM_2"

    # Confidence thresholds
    router_s1_confidence_threshold: float = 0.8

    # Classification rules (will be populated by default() factory)
    router_rules: List[RouterRule] = field(default_factory=list)

    # Heuristics
    router_enable_heuristics: bool = True
    router_max_s1_length: int = 100

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
    memory_vector_store_config: Dict[str, Any] = field(default_factory=dict)
    memory_vector_store_enabled: bool = True
    memory_vector_store_batch_size: int = 100

    memory_embedding_provider: str = "mock"
    memory_embedding_config: Dict[str, Any] = field(default_factory=dict)
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

    def get_router_config(self) -> RouterConfig:
        """
        Build RouterConfig from this unified config.

        Returns:
            RouterConfig with all settings applied
        """
        config = RouterConfig(
            default_system=self.router_default_system,
            s1_confidence_threshold=self.router_s1_confidence_threshold,
            rules=self.router_rules.copy(),
            enable_heuristics=self.router_enable_heuristics,
            max_s1_length=self.router_max_s1_length,
        )
        return config

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
        vector_store = VectorStoreConfig(
            provider=self.memory_vector_store_provider,
            provider_config=self.memory_vector_store_config.copy(),
            enabled=self.memory_vector_store_enabled,
            batch_size=self.memory_vector_store_batch_size,
        )

        embedding = EmbeddingConfig(
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
        config.router_rules = [
            # System 1 Rules (Simple/Factual)
            RouterRule(
                name="greeting",
                keywords=["hi", "hello", "hey", "greeting"],
                target_system="SYSTEM_1",
            ),
            RouterRule(
                name="factual_questions",
                regex_patterns=[r"^what is", r"^who is", r"^when did"],
                target_system="SYSTEM_1",
            ),
            RouterRule(
                name="simple_math",
                regex_patterns=[r"\d+\s*[\+\-\*\/]\s*\d+"],
                target_system="SYSTEM_1",
            ),
            # System 2 Rules (Complex/Reasoning)
            RouterRule(
                name="complex_reasoning",
                keywords=[
                    "plan",
                    "strategy",
                    "design",
                    "analyze",
                    "compare",
                    "code",
                    "implement",
                ],
                target_system="SYSTEM_2",
            ),
        ]

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
        config.router_rules = [
            RouterRule(
                name="test_rule",
                keywords=["test"],
                target_system="SYSTEM_1",
            )
        ]

        return config

    @staticmethod
    def fast_mode() -> "CognitiveSystemConfig":
        """
        Create a configuration optimized for System 1 (fast, reflexive responses).

        - Favors System 1 routing
        - Minimal context (500 tokens)
        - Reduced S1 confidence threshold
        - Optimized for quick responses

        Returns:
            CognitiveSystemConfig for fast mode
        """
        config = CognitiveSystemConfig.default()

        # Favor System 1
        config.router_max_s1_length = 100  # Allow longer queries in S1
        config.router_s1_confidence_threshold = 0.6  # Lower threshold for S1

        # Minimal context for speed
        config.curation_max_tokens = 500
        config.context_max_tokens = 2000

        # Disable expensive features
        config.context_enable_dynamic_budget = False
        config.memory_auto_vectorize_l4 = False

        return config

    @staticmethod
    def balanced_mode() -> "CognitiveSystemConfig":
        """
        Create a balanced configuration (default behavior).

        - Balanced System 1/2 routing
        - Standard context (4000 tokens)
        - Standard confidence thresholds
        - Enables most optimizations

        Returns:
            CognitiveSystemConfig for balanced mode
        """
        return CognitiveSystemConfig.default()

    @staticmethod
    def deep_mode() -> "CognitiveSystemConfig":
        """
        Create a configuration optimized for System 2 (deep, analytical responses).

        - Favors System 2 routing
        - Maximum context (8000+ tokens)
        - High S1 confidence threshold
        - Enables all optimizations

        Returns:
            CognitiveSystemConfig for deep mode
        """
        config = CognitiveSystemConfig.default()

        # Favor System 2
        config.router_max_s1_length = 20  # Restrict S1 to very short queries
        config.router_s1_confidence_threshold = 0.9  # High threshold for S1

        # Maximum context for depth
        config.curation_max_tokens = 8000
        config.context_max_tokens = 16000

        # Enable all optimizations
        config.context_enable_dynamic_budget = True
        config.context_enable_prompt_caching = True
        config.memory_auto_vectorize_l4 = True
        config.memory_enable_auto_compression = True

        # Allocate more budget to global knowledge
        config.context_tokens_budget_l4 = 0.3  # Increase global facts
        config.context_tokens_budget_l3 = 0.3  # Session history
        config.context_tokens_budget_l2 = 0.3  # Working memory
        config.context_tokens_budget_l1 = 0.1  # Raw IO

        return config

    def get_s1_context_config(self) -> ContextConfig:
        """
        Build ContextConfig specifically for System 1 (fast, minimal context).

        Returns:
            ContextConfig optimized for System 1
        """
        config = self.get_context_config()
        # Override for System 1
        config.strategy = "system1"
        config.curation_config.max_tokens = 500
        return config

    def get_s2_context_config(self) -> ContextConfig:
        """
        Build ContextConfig specifically for System 2 (deep, full context).

        Returns:
            ContextConfig optimized for System 2
        """
        config = self.get_context_config()
        # Override for System 2
        config.strategy = "system2"
        config.curation_config.max_tokens = self.curation_max_tokens
        return config

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
        if not (0.0 <= self.router_s1_confidence_threshold <= 1.0):
            raise ValueError(
                f"router_s1_confidence_threshold must be between 0.0 and 1.0"
            )

        # Validate positive integers
        if self.curation_max_tokens <= 0:
            raise ValueError("curation_max_tokens must be positive")
        if self.context_max_tokens <= 0:
            raise ValueError("context_max_tokens must be positive")

        return True


# Convenience alias for shorter import
CognitiveConfig = CognitiveSystemConfig
