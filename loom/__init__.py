"""Loom — minimal self-organizing multi-agent framework."""

from .agent import (
    Agent,
    DelegateHandler,
    Interceptor,
    InterceptorChain,
    InterceptorContext,
    LoopContext,
    LoopStrategy,
    ToolUseStrategy,
)
from .cluster import ClusterManager
from .cluster.amoeba_loop import AmoebaLoop
from .cluster.lifecycle import HealthReport, HealthStatus, LifecycleManager
from .cluster.planner import TaskPlanner
from .cluster.reward import RewardBus
from .config import AgentConfig, ClusterConfig
from .context import ContextOrchestrator, MemoryContextProvider, MitosisContextProvider
from .errors import (
    AgentAbortError,
    AgentMaxStepsError,
    ApoptosisRejectedError,
    AuctionNoWinnerError,
    LLMAuthError,
    LLMError,
    LLMRateLimitError,
    LLMStreamInterruptedError,
    LoomError,
    MitosisError,
    ToolError,
    ToolResultTooLargeError,
    ToolTimeoutError,
)
from .events import EventBus
from .knowledge import FixedSizeChunker, KnowledgeBase, KnowledgeProvider, RecursiveChunker
from .memory import MemoryManager, PersistentStore, SlidingWindow, WorkingMemory
from .providers.base import BaseLLMProvider, CircuitBreakerConfig, RetryConfig
from .runtime import Runtime
from .session import SessionContext, get_current_session, reset_session, set_session
from .skills import SkillCatalogProvider, SkillProvider, SkillRegistry
from .tools import ToolRegistry, define_tool
from .tools.builtin import delegate_tool, done_tool
from .types import (
    AgentEvent,
    AgentNode,
    AssistantMessage,
    Bid,
    CapabilityProfile,
    Chunk,
    CompletionParams,
    ContextFragment,
    ContextProvider,
    ContextSource,
    Document,
    DoneEvent,
    ErrorEvent,
    LLMProvider,
    MemoryEntry,
    MemoryLayer,
    Message,
    RetrievalResult,
    RetrieverOptions,
    RewardRecord,
    RewardSignal,
    SkillActivation,
    SkillTrigger,
    StepEndEvent,
    StepEvent,
    StepStartEvent,
    StreamChunk,
    SubTask,
    SystemMessage,
    TaskAd,
    TextDeltaEvent,
    TokenUsage,
    ToolCall,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolContext,
    ToolDefinition,
    ToolMessage,
    ToolSchema,
    UserMessage,
)

__version__ = "0.6.3"

__all__ = [
    # Agent
    "Agent",
    "AgentConfig",
    "DelegateHandler",
    "InterceptorChain",
    "InterceptorContext",
    "Interceptor",
    "LoopStrategy",
    "LoopContext",
    "ToolUseStrategy",
    # Types — messages
    "Message",
    "SystemMessage",
    "UserMessage",
    "AssistantMessage",
    "ToolMessage",
    "ToolCall",
    "ToolDefinition",
    "ToolSchema",
    "ToolContext",
    "MemoryEntry",
    "MemoryLayer",
    "ContextFragment",
    "ContextSource",
    "ContextProvider",
    # Types — events
    "AgentEvent",
    "TextDeltaEvent",
    "ToolCallStartEvent",
    "ToolCallDeltaEvent",
    "ToolCallEndEvent",
    "StepStartEvent",
    "StepEndEvent",
    "StepEvent",
    "ErrorEvent",
    "DoneEvent",
    "TokenUsage",
    # Types — LLM
    "CompletionParams",
    "StreamChunk",
    "LLMProvider",
    # Types — cluster
    "AgentNode",
    "CapabilityProfile",
    "RewardSignal",
    "RewardRecord",
    "TaskAd",
    "Bid",
    "SubTask",
    # Config
    "ClusterConfig",
    # Memory
    "MemoryManager",
    "SlidingWindow",
    "WorkingMemory",
    "PersistentStore",
    # Context
    "ContextOrchestrator",
    "MemoryContextProvider",
    "MitosisContextProvider",
    # Events
    "EventBus",
    # Tools
    "ToolRegistry",
    "define_tool",
    "done_tool",
    "delegate_tool",
    # Providers
    "BaseLLMProvider",
    "RetryConfig",
    "CircuitBreakerConfig",
    # Errors
    "LoomError",
    "LLMError",
    "LLMRateLimitError",
    "LLMAuthError",
    "LLMStreamInterruptedError",
    "ToolError",
    "ToolTimeoutError",
    "ToolResultTooLargeError",
    "AgentAbortError",
    "AgentMaxStepsError",
    "AuctionNoWinnerError",
    "MitosisError",
    "ApoptosisRejectedError",
    # Session
    "SessionContext",
    "get_current_session",
    "set_session",
    "reset_session",
    # Cluster
    "ClusterManager",
    "RewardBus",
    "LifecycleManager",
    "HealthReport",
    "HealthStatus",
    "TaskPlanner",
    "AmoebaLoop",
    # Knowledge
    "KnowledgeBase",
    "KnowledgeProvider",
    "FixedSizeChunker",
    "RecursiveChunker",
    "Document",
    "Chunk",
    "RetrievalResult",
    "RetrieverOptions",
    # Skills
    "SkillCatalogProvider",
    "SkillRegistry",
    "SkillProvider",
    "SkillTrigger",
    "SkillActivation",
    # Runtime
    "Runtime",
]
