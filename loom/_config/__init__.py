"""Internal configuration modules behind the public ``loom.config`` facade."""

from __future__ import annotations

from .agent import AgentConfig
from .enums import FilesystemWatchMethod, RuntimeFallbackMode, WatchKind
from .generation import GenerationConfig
from .heartbeat import (
    HeartbeatConfig,
    HeartbeatInterruptPolicy,
    ResourceThresholds,
    WatchConfig,
)
from .knowledge import (
    KnowledgeBundle,
    KnowledgeCitation,
    KnowledgeDocument,
    KnowledgeEvidence,
    KnowledgeEvidenceItem,
    KnowledgeQuery,
    KnowledgeResolver,
    KnowledgeSource,
)
from .memory import MemoryBackend, MemoryConfig, MemoryProvider
from .model import ModelRef
from .policy import PolicyConfig, PolicyContext
from .runtime import RuntimeConfig, RuntimeFallback, RuntimeFeatures, RuntimeLimits
from .safety import SafetyEvaluator, SafetyRule
from .tools import (
    ToolAccessPolicy,
    ToolHandler,
    ToolParameterSpec,
    ToolPolicy,
    ToolRateLimitPolicy,
    Toolset,
    ToolSpec,
)

Model = ModelRef
Generation = GenerationConfig
Memory = MemoryConfig
Runtime = RuntimeConfig
AgentSpec = AgentConfig

__all__ = [
    "ModelRef",
    "Model",
    "GenerationConfig",
    "Generation",
    "ToolParameterSpec",
    "ToolHandler",
    "ToolSpec",
    "Toolset",
    "ToolAccessPolicy",
    "ToolRateLimitPolicy",
    "ToolPolicy",
    "PolicyContext",
    "PolicyConfig",
    "MemoryBackend",
    "MemoryConfig",
    "MemoryProvider",
    "Memory",
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
    "Runtime",
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
    "AgentConfig",
    "AgentSpec",
]
