"""Loom — minimal self-organizing multi-agent framework."""

from .types import (
    Message, SystemMessage, UserMessage, AssistantMessage, ToolMessage, ToolCall,
    ToolDefinition, ToolSchema, ToolContext,
    MemoryEntry, MemoryLayer, ContextFragment, ContextSource, ContextProvider,
    AgentEvent, TextDeltaEvent, ToolCallStartEvent, ToolCallDeltaEvent, ToolCallEndEvent,
    StepStartEvent, StepEndEvent, StepEvent, ErrorEvent, DoneEvent, TokenUsage,
    CompletionParams, StreamChunk, LLMProvider,
    AgentNode, CapabilityProfile, RewardSignal, RewardRecord, TaskAd, Bid, SubTask,
    Document, Chunk, RetrievalResult, RetrieverOptions, SkillTrigger, SkillActivation,
)
from .config import AgentConfig, ClusterConfig
from .agent import (
    Agent, DelegateHandler, InterceptorChain, InterceptorContext, Interceptor,
    LoopStrategy, LoopContext, ToolUseStrategy,
)
from .memory import MemoryManager, SlidingWindow, WorkingMemory, PersistentStore
from .context import ContextOrchestrator, MemoryContextProvider, MitosisContextProvider
from .events import EventBus
from .tools import ToolRegistry, define_tool
from .tools.builtin import done_tool, delegate_tool
from .cluster import ClusterManager
from .cluster.reward import RewardBus
from .cluster.lifecycle import LifecycleManager, HealthReport, HealthStatus
from .cluster.planner import TaskPlanner
from .cluster.amoeba_loop import AmoebaLoop
from .providers.base import BaseLLMProvider, RetryConfig, CircuitBreakerConfig
from .errors import (
    LoomError, LLMError, LLMRateLimitError, LLMAuthError, LLMStreamInterruptedError,
    ToolError, ToolTimeoutError, ToolResultTooLargeError,
    AgentAbortError, AgentMaxStepsError,
    AuctionNoWinnerError, MitosisError, ApoptosisRejectedError,
)
from .session import SessionContext, get_current_session, set_session, reset_session
from .knowledge import KnowledgeBase, KnowledgeProvider, FixedSizeChunker, RecursiveChunker
from .skills import SkillRegistry, SkillProvider
from .runtime import Runtime

__version__ = "0.6.0"

__all__ = [
    # Agent
    "Agent", "AgentConfig", "DelegateHandler",
    "InterceptorChain", "InterceptorContext", "Interceptor",
    "LoopStrategy", "LoopContext", "ToolUseStrategy",
    # Types — messages
    "Message", "SystemMessage", "UserMessage", "AssistantMessage", "ToolMessage", "ToolCall",
    "ToolDefinition", "ToolSchema", "ToolContext",
    "MemoryEntry", "MemoryLayer", "ContextFragment", "ContextSource", "ContextProvider",
    # Types — events
    "AgentEvent", "TextDeltaEvent", "ToolCallStartEvent", "ToolCallDeltaEvent", "ToolCallEndEvent",
    "StepStartEvent", "StepEndEvent", "StepEvent", "ErrorEvent", "DoneEvent", "TokenUsage",
    # Types — LLM
    "CompletionParams", "StreamChunk", "LLMProvider",
    # Types — cluster
    "AgentNode", "CapabilityProfile", "RewardSignal", "RewardRecord", "TaskAd", "Bid", "SubTask",
    # Config
    "ClusterConfig",
    # Memory
    "MemoryManager", "SlidingWindow", "WorkingMemory", "PersistentStore",
    # Context
    "ContextOrchestrator", "MemoryContextProvider", "MitosisContextProvider",
    # Events
    "EventBus",
    # Tools
    "ToolRegistry", "define_tool", "done_tool", "delegate_tool",
    # Providers
    "BaseLLMProvider", "RetryConfig", "CircuitBreakerConfig",
    # Errors
    "LoomError", "LLMError", "LLMRateLimitError", "LLMAuthError", "LLMStreamInterruptedError",
    "ToolError", "ToolTimeoutError", "ToolResultTooLargeError",
    "AgentAbortError", "AgentMaxStepsError",
    "AuctionNoWinnerError", "MitosisError", "ApoptosisRejectedError",
    # Session
    "SessionContext", "get_current_session", "set_session", "reset_session",
    # Cluster
    "ClusterManager", "RewardBus", "LifecycleManager", "HealthReport", "HealthStatus", "TaskPlanner", "AmoebaLoop",
    # Knowledge
    "KnowledgeBase", "KnowledgeProvider", "FixedSizeChunker", "RecursiveChunker",
    "Document", "Chunk", "RetrievalResult", "RetrieverOptions",
    # Skills
    "SkillRegistry", "SkillProvider", "SkillTrigger", "SkillActivation",
    # Runtime
    "Runtime",
]
