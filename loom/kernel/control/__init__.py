"""
Kernel Control - Layer 2: Control Capabilities

Interceptors provide AOP-style cross-cutting concerns:
- Budget control (cost management)
- Depth limiting (recursion protection)
- Timeout control (execution time limits)
- HITL (human-in-the-loop approval)
- Tracing (distributed tracing)
- Auth (authorization)
- Adaptive control (anomaly detection & recovery)
"""

from .adaptive import (
    AdaptiveConfig,
    AdaptiveLLMInterceptor,
    AnomalyContext,
    AnomalyDetector,
    AnomalyType,
    RecoveryAction,
    RecoveryStrategy,
    StrategyExecutor,
    create_default_config,
)
from .base import AuthInterceptor, Interceptor, TracingInterceptor
from .budget import BudgetExceededError, BudgetInterceptor
from .depth import DepthInterceptor, RecursionLimitExceededError
from .hitl import HITLInterceptor
from .timeout import TimeoutInterceptor

__all__ = [
    # Base
    "Interceptor",
    "TracingInterceptor",
    "AuthInterceptor",
    # Timeout
    "TimeoutInterceptor",
    # Depth
    "DepthInterceptor",
    "RecursionLimitExceededError",
    # Budget
    "BudgetInterceptor",
    "BudgetExceededError",
    # HITL
    "HITLInterceptor",
    # Adaptive
    "AdaptiveLLMInterceptor",
    "AdaptiveConfig",
    "AnomalyDetector",
    "AnomalyType",
    "AnomalyContext",
    "RecoveryAction",
    "RecoveryStrategy",
    "StrategyExecutor",
    "create_default_config",
]
