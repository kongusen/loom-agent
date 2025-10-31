from .components.agent import Agent
from .core.subagent_pool import SubAgentPool
from .llm import (
    LLMConfig,
    LLMProvider,
    LLMCapabilities,
    LLMFactory,
    ModelPool,
    ModelRegistry,
)
from .agent import agent, agent_from_env
from .tooling import tool
from .agents import AgentSpec, register_agent, list_agent_types, get_agent_by_type
from .agents.refs import AgentRef, ModelRef, agent_ref, model_ref

# P2 Features - Production Ready
from .builtin.memory import InMemoryMemory, PersistentMemory
from .core.error_classifier import ErrorClassifier, RetryPolicy
from .core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState

# P3 Features - Optimization
from .core.structured_logger import StructuredLogger, get_logger, set_correlation_id
from .core.system_reminders import SystemReminderManager, get_reminder_manager
from .callbacks.observability import ObservabilityCallback, MetricsAggregator
from .llm.model_health import ModelHealthChecker, HealthStatus
from .llm.model_pool_advanced import ModelPoolLLM, ModelConfig, FallbackChain

# Loom 0.0.3 - Unified Coordination & Performance
from .core.agent_executor import AgentExecutor, TaskHandler
from .core.unified_coordination import (
    UnifiedExecutionContext,
    IntelligentCoordinator,
    CoordinationConfig
)
from .core.events import (
    AgentEvent,
    AgentEventType,
    EventCollector,
    EventFilter,
    EventProcessor,
    ToolCall,
    ToolResult
)
from .core.turn_state import TurnState
from .core.execution_context import ExecutionContext
from .core.context_assembly import (
    ContextAssembler,
    ComponentPriority,
    ContextComponent
)

# Back-compat alias (prefer `agent`)
loom_agent = agent

try:
    from importlib.metadata import version as _pkg_version

    __version__ = _pkg_version("loom-agent")
except Exception:  # pragma: no cover - best-effort
    __version__ = "0"

__all__ = [
    "Agent",
    "SubAgentPool",
    "LLMConfig",
    "LLMProvider",
    "LLMCapabilities",
    "LLMFactory",
    "ModelPool",
    "ModelRegistry",
    "agent",
    "tool",
    "agent_from_env",
    "AgentSpec",
    "register_agent",
    "list_agent_types",
    "get_agent_by_type",
    "AgentRef",
    "ModelRef",
    "agent_ref",
    "model_ref",
    # P2 exports
    "InMemoryMemory",
    "PersistentMemory",
    "ErrorClassifier",
    "RetryPolicy",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    # P3 exports
    "StructuredLogger",
    "get_logger",
    "set_correlation_id",
    "SystemReminderManager",
    "get_reminder_manager",
    "ObservabilityCallback",
    "MetricsAggregator",
    "ModelHealthChecker",
    "HealthStatus",
    "ModelPoolLLM",
    "ModelConfig",
    "FallbackChain",
    # Loom 0.0.3 exports - Core
    "AgentExecutor",
    "TaskHandler",
    "UnifiedExecutionContext",
    "IntelligentCoordinator",
    "CoordinationConfig",
    # Loom 0.0.3 exports - Events
    "AgentEvent",
    "AgentEventType",
    "EventCollector",
    "EventFilter",
    "EventProcessor",
    "ToolCall",
    "ToolResult",
    # Loom 0.0.3 exports - Context & State
    "TurnState",
    "ExecutionContext",
    "ContextAssembler",
    "ComponentPriority",
    "ContextComponent",
    # Back-compat alias
    "loom_agent",
    "__version__",
]
