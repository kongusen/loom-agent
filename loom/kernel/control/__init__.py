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

from .base import Interceptor, TracingInterceptor, AuthInterceptor
from .timeout import TimeoutInterceptor
from .depth import DepthInterceptor, RecursionLimitExceededError
from .budget import BudgetInterceptor, BudgetExceededError
from .hitl import HITLInterceptor
from .adaptive import (
    AdaptiveLLMInterceptor,
    AdaptiveConfig,
    AnomalyDetector,
    AnomalyType,
    AnomalyContext,
    RecoveryAction,
    RecoveryStrategy,
    StrategyExecutor,
    create_default_config,
)

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
