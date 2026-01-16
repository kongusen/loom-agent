"""
Adaptive Control Interceptor (SDE Noise Control)

Refactored with Human Factors Engineering Principles:
- Framework: DETECTS anomalies (what happened)
- Developer: CONFIGURES strategies (how to respond)
- System: EXECUTES strategies (action)

This separates concerns and gives developers full control over
recovery behaviors while framework handles detection logic.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from loom.kernel.control.base import Interceptor
from loom.protocol.cloudevents import CloudEvent

# =============================================================================
# 1. ANOMALY TYPES (Framework defines WHAT can be detected)
# =============================================================================


class AnomalyType(Enum):
    """
    Types of anomalies that the framework can detect.
    Framework responsibility: Detection only.
    """

    REPETITIVE_REASONING = auto()  # Agent repeating same thoughts
    HALLUCINATION = auto()  # Agent producing unreliable content
    STALLED = auto()  # Agent stuck, no progress
    VALIDATION_FAILED = auto()  # Output failed quality checks
    DEPTH_EXCEEDED = auto()  # Fractal depth limit hit
    BUDGET_EXHAUSTED = auto()  # Token/resource budget depleted
    TIMEOUT_APPROACHING = auto()  # Deadline pressure
    TOOL_ERROR = auto()  # Tool execution failed
    CONVERGENCE_DETECTED = auto()  # Agent successfully converging (positive)


# =============================================================================
# 2. RECOVERY ACTIONS (Framework defines WHAT can be done)
# =============================================================================


class RecoveryAction(Enum):
    """
    Atomic recovery actions that framework can execute.
    These are building blocks; developers compose them into strategies.
    """

    # Temperature Control
    INCREASE_TEMPERATURE = auto()  # Add noise to escape local minima
    DECREASE_TEMPERATURE = auto()  # Reduce noise for convergence
    RESET_TEMPERATURE = auto()  # Return to default

    # Prompt Engineering
    INJECT_REFLECTION_PROMPT = auto()  # Force agent to reflect
    INJECT_SIMPLIFY_PROMPT = auto()  # Ask agent to simplify approach
    INJECT_ALTERNATIVE_PROMPT = auto()  # Suggest trying different approach

    # Control Flow
    TRIGGER_HITL = auto()  # Human-in-the-Loop approval
    FORCE_TERMINATE = auto()  # Stop execution immediately
    RETRY_CURRENT_STEP = auto()  # Retry the same step
    ROLLBACK_TO_CHECKPOINT = auto()  # Restore previous state

    # Model/Resource Control
    SWITCH_MODEL = auto()  # Try different LLM
    REDUCE_MAX_TOKENS = auto()  # Limit output length
    EXTEND_TIMEOUT = auto()  # Give more time

    # Observability
    EMIT_WARNING_EVENT = auto()  # Alert but continue
    LOG_FOR_ANALYSIS = auto()  # Record for post-mortem

    # Developer Extension
    CUSTOM_HANDLER = auto()  # Execute developer callback


# =============================================================================
# 3. RECOVERY STRATEGY (Developer configures HOW to respond)
# =============================================================================


@dataclass
class RecoveryStrategy:
    """
    A strategy is a sequence of actions with parameters.

    Developers configure these to define recovery behavior.
    """

    actions: list[RecoveryAction]
    params: dict[str, Any] = field(default_factory=dict)

    # Optional custom handler for CUSTOM_HANDLER action
    custom_handler: (
        Callable[[CloudEvent, "AnomalyContext"], Awaitable[CloudEvent | None]] | None
    ) = None

    # Strategy metadata
    description: str = ""
    max_retries: int = 3  # How many times to try this strategy


@dataclass
class AnomalyContext:
    """
    Context passed to custom handlers with full anomaly information.
    """

    anomaly_type: AnomalyType
    event: CloudEvent
    agent_id: str
    occurrence_count: int  # How many times this anomaly occurred for this agent
    history: list[dict]  # Recent anomaly history
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 4. ADAPTIVE CONFIG (Developer's control surface)
# =============================================================================


@dataclass
class AdaptiveConfig:
    """
    Developer-facing configuration for adaptive control.

    Maps anomaly types to recovery strategies.

    Example Usage:
    ```python
    config = AdaptiveConfig(
        strategies={
            AnomalyType.REPETITIVE_REASONING: RecoveryStrategy(
                actions=[RecoveryAction.INJECT_REFLECTION_PROMPT, RecoveryAction.INCREASE_TEMPERATURE],
                params={"temperature_delta": 0.2, "reflection_prompt": "你似乎在重复。请尝试不同的方法。"}
            ),
            AnomalyType.STALLED: RecoveryStrategy(
                actions=[RecoveryAction.TRIGGER_HITL],
                description="让人工介入处理停滞情况"
            ),
            AnomalyType.HALLUCINATION: RecoveryStrategy(
                actions=[RecoveryAction.CUSTOM_HANDLER],
                custom_handler=my_hallucination_handler
            )
        }
    )
    ```
    """

    # Core strategy mapping
    strategies: dict[AnomalyType, RecoveryStrategy] = field(default_factory=dict)

    # Global defaults
    default_temperature: float = 0.5
    temperature_bounds: tuple = (0.0, 1.0)  # (min, max)

    # Detection thresholds (developer can tune sensitivity)
    repetition_threshold: int = 3  # N similar thoughts = repetitive
    stall_threshold_seconds: float = 30.0  # No progress for N seconds = stalled

    # Escalation config
    escalation_enabled: bool = True
    escalation_after_failures: int = 3  # After N failed recoveries, escalate
    escalation_strategy: RecoveryStrategy | None = None  # Ultimate fallback

    def get_strategy(self, anomaly: AnomalyType) -> RecoveryStrategy | None:
        """Get configured strategy for an anomaly type."""
        return self.strategies.get(anomaly)


# =============================================================================
# 5. DEFAULT STRATEGIES (Sensible defaults, fully overridable)
# =============================================================================


def create_default_config() -> AdaptiveConfig:
    """
    Factory for default configuration.

    Developers can use this as a starting point:
    ```python
    config = create_default_config()
    config.strategies[AnomalyType.STALLED] = my_custom_strategy
    ```
    """
    return AdaptiveConfig(
        strategies={
            AnomalyType.REPETITIVE_REASONING: RecoveryStrategy(
                actions=[
                    RecoveryAction.EMIT_WARNING_EVENT,
                    RecoveryAction.INJECT_REFLECTION_PROMPT,
                ],
                params={
                    "reflection_prompt": "I notice you may be repeating yourself. Please try a different approach."
                },
                description="Warn and suggest reflection on repetition",
            ),
            AnomalyType.STALLED: RecoveryStrategy(
                actions=[RecoveryAction.EMIT_WARNING_EVENT, RecoveryAction.RETRY_CURRENT_STEP],
                params={"max_retries": 2},
                description="Warn and retry on stall",
            ),
            AnomalyType.VALIDATION_FAILED: RecoveryStrategy(
                actions=[RecoveryAction.LOG_FOR_ANALYSIS, RecoveryAction.RETRY_CURRENT_STEP],
                description="Log and retry on validation failure",
            ),
            AnomalyType.CONVERGENCE_DETECTED: RecoveryStrategy(
                actions=[RecoveryAction.DECREASE_TEMPERATURE],
                params={"temperature_delta": -0.2},
                description="Reduce noise when converging",
            ),
        },
        escalation_strategy=RecoveryStrategy(
            actions=[RecoveryAction.TRIGGER_HITL, RecoveryAction.FORCE_TERMINATE],
            description="Ultimate fallback: human intervention then terminate",
        ),
    )


# =============================================================================
# 6. ANOMALY DETECTOR (Framework's detection logic)
# =============================================================================


class AnomalyDetector:
    """
    Detects anomalies based on event patterns.

    Framework responsibility: Detection ONLY.
    Does NOT decide how to handle - that's the Strategy's job.
    """

    def __init__(self, config: AdaptiveConfig):
        self.config = config
        self._thought_history: dict[str, list[str]] = {}  # agent_id -> recent thoughts
        self._last_progress: dict[str, float] = {}  # agent_id -> timestamp

    def detect(self, event: CloudEvent, agent_id: str) -> AnomalyType | None:
        """
        Analyze event and return detected anomaly type (if any).
        """
        import time

        if event.type == "agent.thought":
            data = event.data or {}
            thought = data.get("thought", "")
            if self._is_repetitive(agent_id, thought):
                return AnomalyType.REPETITIVE_REASONING

        elif event.type == "agent.stalled":
            return AnomalyType.STALLED

        elif event.type == "validation.failed":
            return AnomalyType.VALIDATION_FAILED

        elif event.type == "task.completed" or event.type == "agent.success":
            return AnomalyType.CONVERGENCE_DETECTED

        # Check for stall by time
        current_time = time.time()
        last = self._last_progress.get(agent_id, current_time)
        if current_time - last > self.config.stall_threshold_seconds:
            return AnomalyType.STALLED

        self._last_progress[agent_id] = current_time
        return None

    def _is_repetitive(self, agent_id: str, thought: str) -> bool:
        """Check if agent is repeating similar thoughts."""
        history = self._thought_history.setdefault(agent_id, [])

        # Simple similarity check (can be enhanced with embeddings)
        similar_count = sum(1 for h in history[-10:] if self._similarity(h, thought) > 0.8)

        history.append(thought)
        if len(history) > 50:
            history.pop(0)

        return similar_count >= self.config.repetition_threshold

    def _similarity(self, a: str, b: str) -> float:
        """Simple text similarity (placeholder for more sophisticated methods)."""
        if not a or not b:
            return 0.0
        # Jaccard similarity on word sets
        set_a, set_b = set(a.lower().split()), set(b.lower().split())
        if not set_a or not set_b:
            return 0.0
        return len(set_a & set_b) / len(set_a | set_b)

    def reset(self, agent_id: str):
        """Clear state for an agent."""
        self._thought_history.pop(agent_id, None)
        self._last_progress.pop(agent_id, None)


# =============================================================================
# 7. STRATEGY EXECUTOR (Framework executes developer's choices)
# =============================================================================


class StrategyExecutor:
    """
    Executes recovery strategies.

    Framework responsibility: Execute actions as configured.
    Does NOT make decisions - follows developer's strategy.
    """

    def __init__(self, config: AdaptiveConfig, dispatcher=None):
        self.config = config
        self.dispatcher = dispatcher
        self._current_temps: dict[str, float] = {}  # agent_id -> temperature

    async def execute(
        self, strategy: RecoveryStrategy, context: AnomalyContext, event: CloudEvent
    ) -> CloudEvent | None:
        """
        Execute a recovery strategy, returning modified event (or None to block).
        """
        modified_event = event

        for action in strategy.actions:
            result = await self._execute_action(action, strategy, context, modified_event)

            if result is None:
                # Action requested to block event
                return None
            modified_event = result

        return modified_event

    async def _execute_action(
        self,
        action: RecoveryAction,
        strategy: RecoveryStrategy,
        context: AnomalyContext,
        event: CloudEvent,
    ) -> CloudEvent | None:
        """Execute a single recovery action."""

        params = strategy.params
        agent_id = context.agent_id

        if action == RecoveryAction.INCREASE_TEMPERATURE:
            delta = params.get("temperature_delta", 0.2)
            return self._adjust_temperature(event, agent_id, delta)

        elif action == RecoveryAction.DECREASE_TEMPERATURE:
            delta = params.get("temperature_delta", -0.2)
            return self._adjust_temperature(event, agent_id, delta)

        elif action == RecoveryAction.RESET_TEMPERATURE:
            self._current_temps[agent_id] = self.config.default_temperature
            return self._inject_temperature(event, self.config.default_temperature)

        elif action == RecoveryAction.INJECT_REFLECTION_PROMPT:
            prompt = params.get("reflection_prompt", "Please reflect on your approach.")
            return self._inject_system_hint(event, prompt)

        elif action == RecoveryAction.INJECT_SIMPLIFY_PROMPT:
            prompt = params.get("simplify_prompt", "Try a simpler approach.")
            return self._inject_system_hint(event, prompt)

        elif action == RecoveryAction.INJECT_ALTERNATIVE_PROMPT:
            prompt = params.get("alternative_prompt", "Consider an alternative method.")
            return self._inject_system_hint(event, prompt)

        elif action == RecoveryAction.TRIGGER_HITL:
            # Emit HITL request event
            if self.dispatcher:
                await self.dispatcher.dispatch(
                    CloudEvent.create(
                        source="/kernel/adaptive",
                        type="hitl.request",
                        subject=agent_id,
                        data={
                            "anomaly": context.anomaly_type.name,
                            "reason": strategy.description,
                            "context": context.metadata,
                        },
                    )
                )
            # Block until approved (or let HITL interceptor handle)
            event.extensions = event.extensions or {}
            event.extensions["requires_hitl"] = True
            return event

        elif action == RecoveryAction.FORCE_TERMINATE:
            # Return None to block the event
            if self.dispatcher:
                await self.dispatcher.dispatch(
                    CloudEvent.create(
                        source="/kernel/adaptive",
                        type="agent.terminated",
                        subject=agent_id,
                        data={
                            "reason": f"Force terminated due to: {context.anomaly_type.name}",
                            "strategy": strategy.description,
                        },
                    )
                )
            return None

        elif action == RecoveryAction.EMIT_WARNING_EVENT:
            if self.dispatcher:
                await self.dispatcher.dispatch(
                    CloudEvent.create(
                        source="/kernel/adaptive",
                        type="agent.warning",
                        subject=agent_id,
                        data={
                            "anomaly": context.anomaly_type.name,
                            "occurrence_count": context.occurrence_count,
                            "message": strategy.description,
                        },
                    )
                )
            return event

        elif action == RecoveryAction.LOG_FOR_ANALYSIS:
            # Log for post-mortem (implement logging)
            event.extensions = event.extensions or {}
            event.extensions.setdefault("anomaly_log", []).append(
                {
                    "type": context.anomaly_type.name,
                    "count": context.occurrence_count,
                    "timestamp": event.time,
                }
            )
            return event

        elif action == RecoveryAction.CUSTOM_HANDLER:
            if strategy.custom_handler:
                return await strategy.custom_handler(event, context)
            return event

        # Default: pass through unchanged
        return event

    def _adjust_temperature(self, event: CloudEvent, agent_id: str, delta: float) -> CloudEvent:
        """Adjust temperature by delta, respecting bounds."""
        current = self._current_temps.get(agent_id, self.config.default_temperature)
        new_temp = max(
            self.config.temperature_bounds[0],
            min(self.config.temperature_bounds[1], current + delta),
        )
        self._current_temps[agent_id] = new_temp
        return self._inject_temperature(event, new_temp)

    def _inject_temperature(self, event: CloudEvent, temperature: float) -> CloudEvent:
        """Inject temperature into event extensions."""
        extensions = event.extensions or {}
        llm_config = extensions.get("llm_config_override", {})
        llm_config["temperature"] = temperature
        extensions["llm_config_override"] = llm_config
        event.extensions = extensions
        return event

    def _inject_system_hint(self, event: CloudEvent, hint: str) -> CloudEvent:
        """Inject a system hint for the agent."""
        extensions = event.extensions or {}
        extensions["system_hint"] = hint
        event.extensions = extensions
        return event


# =============================================================================
# 8. MAIN INTERCEPTOR (Orchestrates Detection → Strategy → Execution)
# =============================================================================


class AdaptiveLLMInterceptor(Interceptor):
    """
    Implements the "Dynamic Feedback" term of the Controlled Fractal equation.

    Refactored with Human Factors Engineering Principles:
    - Framework DETECTS (AnomalyDetector)
    - Developer CONFIGURES (AdaptiveConfig)
    - Framework EXECUTES (StrategyExecutor)

    Usage:
    ```python
    # Use defaults
    interceptor = AdaptiveLLMInterceptor()

    # Or customize
    config = create_default_config()
    config.strategies[AnomalyType.STALLED] = RecoveryStrategy(
        actions=[RecoveryAction.CUSTOM_HANDLER],
        custom_handler=my_stall_handler
    )
    interceptor = AdaptiveLLMInterceptor(config=config)

    app.dispatcher.add_interceptor(interceptor)
    ```
    """

    def __init__(self, config: AdaptiveConfig | None = None, dispatcher=None):
        self.config = config or create_default_config()
        self.detector = AnomalyDetector(self.config)
        self.executor = StrategyExecutor(self.config, dispatcher)

        # Track anomaly occurrences per agent
        self._anomaly_counts: dict[str, dict[AnomalyType, int]] = {}
        self._anomaly_history: dict[str, list[dict]] = {}

    def set_dispatcher(self, dispatcher):
        """Set dispatcher after construction (for DI)."""
        self.executor.dispatcher = dispatcher

    async def pre_invoke(self, event: CloudEvent) -> CloudEvent | None:
        """
        Detect anomalies and execute configured strategies.
        """
        # Identify agent
        agent_id = event.subject or event.source
        if not agent_id:
            return event

        # Detect anomaly
        anomaly = self.detector.detect(event, agent_id)

        if anomaly is None:
            return event

        # Update occurrence count
        agent_counts = self._anomaly_counts.setdefault(agent_id, {})
        agent_counts[anomaly] = agent_counts.get(anomaly, 0) + 1
        occurrence_count = agent_counts[anomaly]

        # Build context
        context = AnomalyContext(
            anomaly_type=anomaly,
            event=event,
            agent_id=agent_id,
            occurrence_count=occurrence_count,
            history=self._anomaly_history.get(agent_id, []),
            metadata={"extensions": event.extensions},
        )

        # Record in history
        history = self._anomaly_history.setdefault(agent_id, [])
        history.append({"type": anomaly.name, "count": occurrence_count})
        if len(history) > 100:
            history.pop(0)

        # Get strategy (developer configured)
        strategy = self.config.get_strategy(anomaly)

        # Check for escalation
        if (
            strategy
            and occurrence_count > strategy.max_retries
            and self.config.escalation_enabled
            and occurrence_count > self.config.escalation_after_failures
        ):
            strategy = self.config.escalation_strategy

        if strategy is None:
            # No strategy configured for this anomaly - pass through
            return event

        # Execute strategy
        return await self.executor.execute(strategy, context, event)

    async def post_invoke(self, event: CloudEvent) -> None:
        """
        Post-processing: reset state on success.
        """
        if event.type in ("task.completed", "agent.success", "node.response"):
            agent_id = event.source
            if agent_id:
                self.detector.reset(agent_id)
                self._anomaly_counts.pop(agent_id, None)
                self._anomaly_history.pop(agent_id, None)

    async def on_feedback_event(self, event: CloudEvent):
        """
        External event handler for feedback events.
        Register this with the event bus:

        ```python
        bus.subscribe("agent.stalled/*", interceptor.on_feedback_event)
        bus.subscribe("validation.failed/*", interceptor.on_feedback_event)
        ```
        """
        # Detection is handled in pre_invoke via detector
        # This is for external feedback that triggers state updates
        pass
