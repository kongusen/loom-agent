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
    "__version__",
]
