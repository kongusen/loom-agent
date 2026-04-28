"""Legacy 0.x public API surface.

These names are kept through the 0.8 release line.  The 0.9 public API should
prefer ``loom.Agent`` with the shorter configuration vocabulary exported from
``loom`` and ``loom.config``.
"""

from __future__ import annotations

from ..agent import Agent, create_agent, tool
from ..config import (
    AgentConfig,
    FilesystemWatchMethod,
    GenerationConfig,
    HeartbeatConfig,
    HeartbeatInterruptPolicy,
    KnowledgeBundle,
    KnowledgeCitation,
    KnowledgeDocument,
    KnowledgeEvidence,
    KnowledgeEvidenceItem,
    KnowledgeQuery,
    KnowledgeResolver,
    KnowledgeSource,
    MemoryBackend,
    MemoryConfig,
    MemoryProvider,
    ModelRef,
    PolicyConfig,
    PolicyContext,
    ResourceThresholds,
    RuntimeConfig,
    RuntimeFallback,
    RuntimeFallbackMode,
    RuntimeFeatures,
    RuntimeLimits,
    SafetyEvaluator,
    SafetyRule,
    ToolAccessPolicy,
    ToolHandler,
    ToolParameterSpec,
    ToolPolicy,
    ToolRateLimitPolicy,
    ToolSpec,
    WatchConfig,
    WatchKind,
)

# --- 0.8 compatibility aliases (renamed in 0.8.0) ---
# Context three-layer rename:
#   ContextProtocol → ContextPolicy
#   RuntimeContextProtocol → RuntimeContextPolicy
#   ManagedContextProtocol → ManagedContextAdapter
# These aliases are re-exported from loom.runtime.context so existing imports
# continue to work.  Will be removed in 0.9.0.
from ..runtime.context import (
    ContextPolicy,  # noqa: F401
    ManagedContextAdapter,  # noqa: F401
    RuntimeContextPolicy,  # noqa: F401
)

# SkillInjectionPolicy → SkillInjection
# The old name is kept as an alias in loom.runtime.skills.
from ..runtime.skills import SkillInjection  # noqa: F401

# Backward-compatible re-exports under old names
ContextProtocol = ContextPolicy
ManagedContextProtocol = ManagedContextAdapter
RuntimeContextProtocol = RuntimeContextPolicy
SkillInjectionPolicy = SkillInjection

__all__ = [
    "Agent",
    "create_agent",
    "tool",
    "AgentConfig",
    "ModelRef",
    "GenerationConfig",
    "ToolParameterSpec",
    "ToolHandler",
    "ToolSpec",
    "ToolAccessPolicy",
    "ToolRateLimitPolicy",
    "ToolPolicy",
    "PolicyContext",
    "PolicyConfig",
    "MemoryBackend",
    "MemoryConfig",
    "MemoryProvider",
    "WatchKind",
    "FilesystemWatchMethod",
    "ResourceThresholds",
    "WatchConfig",
    "HeartbeatInterruptPolicy",
    "HeartbeatConfig",
    "RuntimeFallbackMode",
    "RuntimeFallback",
    "RuntimeLimits",
    "RuntimeFeatures",
    "RuntimeConfig",
    "SafetyEvaluator",
    "SafetyRule",
    "KnowledgeDocument",
    "KnowledgeQuery",
    "KnowledgeCitation",
    "KnowledgeEvidenceItem",
    "KnowledgeEvidence",
    "KnowledgeBundle",
    "KnowledgeResolver",
    "KnowledgeSource",
    # 0.8 compat aliases (old names)
    "ContextProtocol",
    "ManagedContextProtocol",
    "RuntimeContextProtocol",
    "SkillInjectionPolicy",
    # 0.8 new names
    "ContextPolicy",
    "ManagedContextAdapter",
    "RuntimeContextPolicy",
    "SkillInjection",
]
