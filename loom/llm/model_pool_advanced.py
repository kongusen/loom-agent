"""US8: Advanced Model Pool with Fallback Chain

Provides intelligent model selection with health-aware fallback.

Features:
- Fallback chain: [primary, fallback1, fallback2]
- Automatic fallback on 5xx errors
- Health-based model selection
- Connection pooling for reduced latency
"""

from __future__ import annotations

import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from loom.interfaces.llm import BaseLLM
from loom.llm.model_health import ModelHealthChecker, HealthStatus
from loom.core.error_classifier import ErrorClassifier, ErrorCategory


@dataclass
class ModelConfig:
    """Configuration for a model in the pool."""
    model_id: str
    llm: BaseLLM
    priority: int = 0  # Higher priority = preferred (for same health status)
    max_concurrent: int = 10  # Max concurrent requests to this model


class FallbackChain:
    """Manages fallback chain for model selection.

    Example:
        chain = FallbackChain([
            ModelConfig("gpt-4", gpt4_llm, priority=100),
            ModelConfig("gpt-3.5-turbo", gpt35_llm, priority=50),
            ModelConfig("claude-2", claude_llm, priority=30),
        ])

        # Automatically selects best available model
        llm = await chain.get_next_model()
    """

    def __init__(
        self,
        models: List[ModelConfig],
        health_checker: Optional[ModelHealthChecker] = None,
    ):
        """Initialize fallback chain.

        Args:
            models: List of model configurations (ordered by preference)
            health_checker: Health checker instance
        """
        self.models = models
        self.health_checker = health_checker or ModelHealthChecker()
        self._model_map = {m.model_id: m for m in models}
        self._semaphores: Dict[str, asyncio.Semaphore] = {}

        # Create semaphores for rate limiting
        for model in models:
            self._semaphores[model.model_id] = asyncio.Semaphore(model.max_concurrent)

    def get_next_model(
        self,
        skip_unhealthy: bool = True,
        prefer_healthy: bool = True,
    ) -> Optional[ModelConfig]:
        """Get next best model from fallback chain.

        Args:
            skip_unhealthy: Skip models marked as unhealthy
            prefer_healthy: Prefer healthy models over degraded

        Returns:
            ModelConfig or None if no models available
        """
        # Categorize models by health
        healthy = []
        degraded = []
        unhealthy = []
        unknown = []

        for model in self.models:
            status = self.health_checker.get_status(model.model_id)

            if status == HealthStatus.HEALTHY:
                healthy.append(model)
            elif status == HealthStatus.DEGRADED:
                degraded.append(model)
            elif status == HealthStatus.UNHEALTHY:
                unhealthy.append(model)
            else:
                unknown.append(model)

        # Select based on preference
        candidates = []

        if prefer_healthy and healthy:
            candidates = healthy
        elif healthy or degraded:
            candidates = healthy + degraded
        elif unknown:
            candidates = unknown
        elif not skip_unhealthy:
            candidates = unhealthy

        if not candidates:
            return None

        # Sort by priority (highest first)
        candidates.sort(key=lambda m: m.priority, reverse=True)

        return candidates[0]

    async def call_with_fallback(
        self,
        operation: str,  # "generate" or "generate_with_tools"
        *args: Any,
        max_fallback_attempts: int = 3,
        **kwargs: Any,
    ) -> Any:
        """Call model with automatic fallback on failure.

        Args:
            operation: LLM method name
            *args: Positional arguments
            max_fallback_attempts: Max models to try
            **kwargs: Keyword arguments

        Returns:
            Result from successful model call

        Raises:
            Exception if all models fail
        """
        attempts = 0
        last_exception = None

        while attempts < max_fallback_attempts:
            model_config = self.get_next_model()

            if not model_config:
                break

            try:
                # Acquire semaphore for rate limiting
                async with self._semaphores[model_config.model_id]:
                    # Call the model
                    import time
                    start = time.time()

                    method = getattr(model_config.llm, operation)
                    result = await method(*args, **kwargs)

                    latency_ms = (time.time() - start) * 1000

                    # Record success
                    self.health_checker.record_success(
                        model_config.model_id,
                        latency_ms=latency_ms
                    )

                    return result

            except Exception as e:
                last_exception = e

                # Record failure
                self.health_checker.record_failure(
                    model_config.model_id,
                    error=str(e)
                )

                # Check if error is retryable
                category = ErrorClassifier.classify(e)

                if category == ErrorCategory.SERVICE_ERROR:
                    # 5xx error - try fallback
                    attempts += 1
                    continue
                else:
                    # Non-retryable error - propagate
                    raise

            attempts += 1

        # All models failed
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError("No healthy models available")

    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all models.

        Returns:
            Dict with health information
        """
        summary = {}

        for model in self.models:
            metrics = self.health_checker.get_metrics(model.model_id)
            if metrics:
                summary[model.model_id] = {
                    "status": metrics.status.value,
                    "success_rate": metrics.success_rate,
                    "avg_latency_ms": metrics.avg_latency_ms,
                    "consecutive_failures": metrics.consecutive_failures,
                }
            else:
                summary[model.model_id] = {"status": "unknown"}

        return summary


class ModelPoolLLM(BaseLLM):
    """LLM wrapper that uses fallback chain.

    Drop-in replacement for any BaseLLM with automatic fallback.

    Example:
        # Create pool with fallback chain
        pool_llm = ModelPoolLLM([
            ModelConfig("gpt-4", gpt4_llm, priority=100),
            ModelConfig("gpt-3.5-turbo", gpt35_llm, priority=50),
        ])

        # Use like any LLM
        agent = Agent(llm=pool_llm, tools=tools)
    """

    def __init__(
        self,
        models: List[ModelConfig],
        max_fallback_attempts: int = 3,
    ):
        """Initialize model pool LLM.

        Args:
            models: List of model configurations
            max_fallback_attempts: Max models to try on failure
        """
        self.fallback_chain = FallbackChain(models)
        self.max_fallback_attempts = max_fallback_attempts

        # Use first model's capabilities as default
        if models:
            self._supports_tools = models[0].llm.supports_tools
            self._model_name = f"pool({','.join([m.model_id for m in models])})"
        else:
            self._supports_tools = False
            self._model_name = "pool(empty)"

    @property
    def model_name(self) -> str:
        """Get pool model name."""
        return self._model_name

    @property
    def supports_tools(self) -> bool:
        """Check if pool supports tools."""
        return self._supports_tools

    async def generate(self, messages: List[dict]) -> str:
        """Generate completion with automatic fallback."""
        return await self.fallback_chain.call_with_fallback(
            "generate",
            messages,
            max_fallback_attempts=self.max_fallback_attempts,
        )

    async def generate_with_tools(
        self,
        messages: List[dict],
        tools: List[dict],
    ) -> dict:
        """Generate with tools, with automatic fallback."""
        return await self.fallback_chain.call_with_fallback(
            "generate_with_tools",
            messages,
            tools,
            max_fallback_attempts=self.max_fallback_attempts,
        )

    async def stream(self, messages: List[dict]):
        """Stream responses (uses first healthy model)."""
        model_config = self.fallback_chain.get_next_model()
        if not model_config:
            raise RuntimeError("No healthy models available")

        # Delegate to model's stream
        if hasattr(model_config.llm, 'stream'):
            async for chunk in model_config.llm.stream(messages):
                yield chunk
        else:
            # Fallback to non-streaming
            result = await self.generate(messages)
            yield result

    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for pool."""
        return self.fallback_chain.get_health_summary()
