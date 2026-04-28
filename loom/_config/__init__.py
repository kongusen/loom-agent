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
from .memory import (
    MemoryBackend,
    MemoryConfig,
    MemoryExtractor,
    MemoryProvider,
    MemoryQuery,
    MemoryRecall,
    MemoryRecord,
    MemoryResolver,
    MemorySource,
    MemoryStore,
)
from .model import ModelRef
from .orchestration import OrchestrationConfig
from .policy import PolicyConfig, PolicyContext
from .runtime import RuntimeConfig, RuntimeFallback, RuntimeFeatures, RuntimeLimits
from .safety import SafetyEvaluator, SafetyRule
from .schedule import ScheduleConfig, ScheduledJob
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
    "MemoryQuery",
    "MemoryRecord",
    "MemoryRecall",
    "MemoryStore",
    "MemoryResolver",
    "MemoryExtractor",
    "MemorySource",
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
    "OrchestrationConfig",
    "ScheduleConfig",
    "ScheduledJob",
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
