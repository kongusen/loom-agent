"""Stable configuration vocabulary for the Loom agent API.

`loom.config` is the extension layer under the primary `loom` entry point.
Application developers import advanced configuration objects from here when
they need richer control than the top-level defaults exposed from `loom`.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class WatchKind(StrEnum):
    """Supported public heartbeat watch kinds."""

    FILESYSTEM = "filesystem"
    PROCESS = "process"
    RESOURCE = "resource"
    MF_EVENTS = "mf_events"


class FilesystemWatchMethod(StrEnum):
    """Supported filesystem watch strategies."""

    HASH = "hash"


class RuntimeFallbackMode(StrEnum):
    """Supported runtime fallback behaviors."""

    LOCAL_SUMMARY = "local_summary"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Tool declarations and governance
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ToolAccessPolicy:
    """Stable tool access controls."""

    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)
    read_only_only: bool = False
    allow_destructive: bool = False


@dataclass(slots=True)
class ToolRateLimitPolicy:
    """Stable tool rate-limit controls."""

    max_calls_per_minute: int = 60


@dataclass(slots=True)
class ToolPolicy:
    """Tool governance settings exposed on the public API."""

    access: ToolAccessPolicy = field(default_factory=ToolAccessPolicy)
    rate_limits: ToolRateLimitPolicy = field(default_factory=ToolRateLimitPolicy)
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolParameterSpec:
    """Stable tool parameter schema."""

    name: str
    type: str
    required: bool = True
    description: str = ""
    default: Any = None


@dataclass(slots=True)
class ToolHandler:
    """Adapter for local callable-backed tool execution."""

    func: Callable[..., Any]
    mode: str = "callable"
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def callable(
        cls,
        func: Callable[..., Any],
        *,
        extensions: dict[str, Any] | None = None,
    ) -> ToolHandler:
        return cls(func=func, mode="callable", extensions=dict(extensions or {}))

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


@dataclass(slots=True)
class ToolSpec:
    """Stable public tool declaration."""

    name: str
    description: str = ""
    parameters: list[ToolParameterSpec] = field(default_factory=list)
    read_only: bool = False
    destructive: bool = False
    concurrency_safe: bool = False
    requires_permission: bool = True
    handler: ToolHandler | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_function(
        cls,
        func: Callable[..., Any],
        *,
        name: str | None = None,
        description: str | None = None,
        read_only: bool = False,
        destructive: bool = False,
        concurrency_safe: bool = False,
        requires_permission: bool | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ToolSpec:
        permission_required = requires_permission if requires_permission is not None else not read_only
        return cls(
            name=name or func.__name__,
            description=description or (func.__doc__ or "").strip(),
            parameters=_build_tool_parameter_specs(inspect.signature(func)),
            read_only=read_only,
            destructive=destructive,
            concurrency_safe=concurrency_safe,
            requires_permission=permission_required,
            handler=ToolHandler.callable(func),
            extensions=dict(extensions or {}),
        )

    def to_input_schema(self) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        required: list[str] = []
        for parameter in self.parameters:
            schema: dict[str, Any] = {"type": parameter.type}
            if parameter.description:
                schema["description"] = parameter.description
            if parameter.default is not None:
                schema["default"] = parameter.default
            properties[parameter.name] = schema
            if parameter.required:
                required.append(parameter.name)
        return {"type": "object", "properties": properties, "required": required}

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self.handler is None:
            raise RuntimeError(f"Tool '{self.name}' does not have a local handler")
        return self.handler.invoke(*args, **kwargs)


def _build_tool_parameter_specs(sig: inspect.Signature) -> list[ToolParameterSpec]:
    parameters: list[ToolParameterSpec] = []
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        json_type = "string"
        if param.annotation is int:
            json_type = "integer"
        elif param.annotation is float:
            json_type = "number"
        elif param.annotation is bool:
            json_type = "boolean"

        default = None if param.default == inspect.Parameter.empty else param.default
        parameters.append(
            ToolParameterSpec(
                name=param_name,
                type=json_type,
                required=param.default == inspect.Parameter.empty,
                default=default,
            )
        )
    return parameters


# ---------------------------------------------------------------------------
# Model and generation
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ModelRef:
    """Stable model reference for one provider-backed model."""

    provider: str
    name: str
    api_base: str | None = None
    organization: str | None = None
    api_key_env: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def anthropic(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        return cls(
            provider="anthropic",
            name=name,
            api_base=api_base,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def openai(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        organization: str | None = None,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        return cls(
            provider="openai",
            name=name,
            api_base=api_base,
            organization=organization,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def gemini(
        cls,
        name: str,
        *,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        return cls(
            provider="gemini",
            name=name,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def qwen(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        return cls(
            provider="qwen",
            name=name,
            api_base=api_base,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def deepseek(
        cls,
        name: str = "deepseek-chat",
        *,
        api_base: str | None = None,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        """DeepSeek provider.  Use ``deepseek-chat`` for tool calling and
        ``deepseek-reasoner`` for chain-of-thought reasoning (R1)."""
        return cls(
            provider="deepseek",
            name=name,
            api_base=api_base,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def minimax(
        cls,
        name: str = "MiniMax-Text-01",
        *,
        api_base: str | None = None,
        api_key_env: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        """MiniMax provider.  Supports ``MiniMax-Text-01``, ``MiniMax-M1``
        (thinking), and ``abab6.5s-chat``."""
        return cls(
            provider="minimax",
            name=name,
            api_base=api_base,
            api_key_env=api_key_env,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def ollama(
        cls,
        name: str,
        *,
        api_base: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ModelRef:
        return cls(
            provider="ollama",
            name=name,
            api_base=api_base,
            extensions=dict(extensions or {}),
        )

    @property
    def identifier(self) -> str:
        return f"{self.provider}:{self.name}"


@dataclass(slots=True)
class GenerationConfig:
    """Stable model generation controls."""

    temperature: float = 0.7
    max_output_tokens: int | None = None
    extensions: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Policy and memory
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PolicyContext:
    """Stable policy execution context."""

    name: str = "default"
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def default(
        cls,
        *,
        extensions: dict[str, Any] | None = None,
    ) -> PolicyContext:
        return cls(name="default", extensions=dict(extensions or {}))

    @classmethod
    def named(
        cls,
        name: str,
        *,
        extensions: dict[str, Any] | None = None,
    ) -> PolicyContext:
        return cls(name=name, extensions=dict(extensions or {}))


@dataclass(slots=True)
class PolicyConfig:
    """Top-level policy configuration for one agent."""

    tools: ToolPolicy = field(default_factory=ToolPolicy)
    context: PolicyContext = field(default_factory=PolicyContext.default)
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryBackend:
    """Stable memory backend definition."""

    name: str
    options: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def in_memory(
        cls,
        *,
        extensions: dict[str, Any] | None = None,
    ) -> MemoryBackend:
        return cls(name="in_memory", extensions=dict(extensions or {}))

    @classmethod
    def custom(
        cls,
        name: str,
        *,
        options: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> MemoryBackend:
        return cls(
            name=name,
            options=dict(options or {}),
            extensions=dict(extensions or {}),
        )


@dataclass(slots=True)
class MemoryConfig:
    """Session memory configuration."""

    enabled: bool = True
    backend: MemoryBackend = field(default_factory=MemoryBackend.in_memory)
    namespace: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Heartbeat and runtime controls
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ResourceThresholds:
    """Stable resource thresholds for heartbeat monitoring."""

    cpu_pct: float | None = None
    memory_pct: float | None = None
    disk_pct: float | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_runtime_config(self) -> dict[str, Any]:
        payload = dict(self.extensions)
        if self.cpu_pct is not None:
            payload["cpu_pct"] = self.cpu_pct
        if self.memory_pct is not None:
            payload["memory_pct"] = self.memory_pct
        if self.disk_pct is not None:
            payload["disk_pct"] = self.disk_pct
        return payload


@dataclass(slots=True)
class WatchConfig:
    """One heartbeat watch source."""

    kind: WatchKind
    paths: list[str] = field(default_factory=list)
    method: FilesystemWatchMethod | None = None
    pid_file: str | None = None
    watch_pids: list[int] = field(default_factory=list)
    thresholds: ResourceThresholds | None = None
    topics: list[str] = field(default_factory=list)
    event_bus: Any | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def filesystem(
        cls,
        *,
        paths: list[str],
        method: FilesystemWatchMethod = FilesystemWatchMethod.HASH,
        extensions: dict[str, Any] | None = None,
    ) -> WatchConfig:
        return cls(
            kind=WatchKind.FILESYSTEM,
            paths=list(paths),
            method=method,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def process(
        cls,
        *,
        pid_file: str | None = None,
        watch_pids: list[int] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> WatchConfig:
        return cls(
            kind=WatchKind.PROCESS,
            pid_file=pid_file,
            watch_pids=list(watch_pids or []),
            extensions=dict(extensions or {}),
        )

    @classmethod
    def resource(
        cls,
        *,
        thresholds: ResourceThresholds,
        extensions: dict[str, Any] | None = None,
    ) -> WatchConfig:
        return cls(
            kind=WatchKind.RESOURCE,
            thresholds=thresholds,
            extensions=dict(extensions or {}),
        )

    @classmethod
    def mf_events(
        cls,
        *,
        topics: list[str] | None = None,
        event_bus: Any | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> WatchConfig:
        return cls(
            kind=WatchKind.MF_EVENTS,
            topics=list(topics or []),
            event_bus=event_bus,
            extensions=dict(extensions or {}),
        )

    def to_runtime_config(self) -> dict[str, Any]:
        payload = dict(self.extensions)
        if self.paths:
            payload["paths"] = list(self.paths)
        if self.method is not None:
            payload["method"] = self.method.value
        if self.pid_file is not None:
            payload["pid_file"] = self.pid_file
        if self.watch_pids:
            payload["watch_pids"] = list(self.watch_pids)
        if self.thresholds is not None:
            payload["thresholds"] = self.thresholds.to_runtime_config()
        if self.topics:
            payload["topics"] = list(self.topics)
        if self.event_bus is not None:
            payload["event_bus"] = self.event_bus
        return payload


@dataclass(slots=True)
class HeartbeatInterruptPolicy:
    """Stable heartbeat interrupt behavior by urgency."""

    low: str = "queue"
    high: str = "request"
    critical: str = "force"
    extensions: dict[str, str] = field(default_factory=dict)

    def to_runtime_config(self) -> dict[str, str]:
        payload = {
            "low": self.low,
            "high": self.high,
            "critical": self.critical,
        }
        payload.update(self.extensions)
        return payload


@dataclass(slots=True)
class HeartbeatConfig:
    """Heartbeat configuration exposed on the public API."""

    interval: float = 5.0
    min_entropy_delta: float = 0.1
    watch_sources: list[WatchConfig] = field(default_factory=list)
    interrupt_policy: HeartbeatInterruptPolicy = field(default_factory=HeartbeatInterruptPolicy)


@dataclass(slots=True)
class RuntimeFallback:
    """Stable runtime fallback behavior."""

    mode: RuntimeFallbackMode = RuntimeFallbackMode.LOCAL_SUMMARY
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeLimits:
    """Stable execution limits for the runtime."""

    max_iterations: int = 100
    max_context_tokens: int | None = None
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeFeatures:
    """Stable runtime feature flags."""

    enable_safety: bool = True
    fallback: RuntimeFallback = field(default_factory=RuntimeFallback)
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeConfig:
    """Execution-engine configuration exposed on the public API."""

    limits: RuntimeLimits = field(default_factory=RuntimeLimits)
    features: RuntimeFeatures = field(default_factory=RuntimeFeatures)
    extensions: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Safety controls
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SafetyEvaluator:
    """Adapter for local callable-backed safety evaluation."""

    handler: Callable[[str, dict[str, Any]], bool]
    mode: str = "callable"
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def callable(
        cls,
        handler: Callable[[str, dict[str, Any]], bool],
        *,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyEvaluator:
        return cls(handler=handler, mode="callable", extensions=dict(extensions or {}))

    def evaluate(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        return bool(self.handler(tool_name, arguments))


@dataclass(slots=True)
class SafetyRule:
    """Public declarative safety rule."""

    name: str
    reason: str
    tool_names: list[str] = field(default_factory=list)
    arg_equals: dict[str, Any] = field(default_factory=dict)
    arg_prefixes: dict[str, str] = field(default_factory=dict)
    arg_contains_any: dict[str, list[str]] = field(default_factory=dict)
    evaluator: SafetyEvaluator | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def block_tool(
        cls,
        *,
        name: str,
        tool_names: list[str],
        reason: str,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyRule:
        return cls(
            name=name,
            reason=reason,
            tool_names=list(tool_names),
            extensions=dict(extensions or {}),
        )

    @classmethod
    def when_argument_equals(
        cls,
        *,
        name: str,
        tool_name: str,
        argument: str,
        value: Any,
        reason: str,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyRule:
        return cls(
            name=name,
            reason=reason,
            tool_names=[tool_name],
            arg_equals={argument: value},
            extensions=dict(extensions or {}),
        )

    @classmethod
    def when_argument_startswith(
        cls,
        *,
        name: str,
        tool_name: str,
        argument: str,
        prefix: str,
        reason: str,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyRule:
        return cls(
            name=name,
            reason=reason,
            tool_names=[tool_name],
            arg_prefixes={argument: prefix},
            extensions=dict(extensions or {}),
        )

    @classmethod
    def when_argument_contains_any(
        cls,
        *,
        name: str,
        tool_name: str,
        argument: str,
        values: list[str],
        reason: str,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyRule:
        return cls(
            name=name,
            reason=reason,
            tool_names=[tool_name],
            arg_contains_any={argument: list(values)},
            extensions=dict(extensions or {}),
        )

    @classmethod
    def custom(
        cls,
        *,
        name: str,
        reason: str,
        evaluator: SafetyEvaluator,
        tool_names: list[str] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> SafetyRule:
        return cls(
            name=name,
            reason=reason,
            tool_names=list(tool_names or []),
            evaluator=evaluator,
            extensions=dict(extensions or {}),
        )

    def matches(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        if self.tool_names and tool_name not in self.tool_names:
            return False

        for argument, expected in self.arg_equals.items():
            if arguments.get(argument) != expected:
                return False

        for argument, prefix in self.arg_prefixes.items():
            if not str(arguments.get(argument, "")).startswith(prefix):
                return False

        for argument, values in self.arg_contains_any.items():
            candidate = str(arguments.get(argument, ""))
            if not any(value in candidate for value in values):
                return False

        if self.evaluator is not None and not self.evaluator.evaluate(tool_name, arguments):
            return False

        return bool(
            self.tool_names
            or self.arg_equals
            or self.arg_prefixes
            or self.arg_contains_any
            or self.evaluator is not None
        )


# ---------------------------------------------------------------------------
# Knowledge contracts
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class KnowledgeDocument:
    """Stable declarative knowledge document."""

    content: str
    title: str = ""
    uri: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload = {
            "content": self.content,
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.title:
            payload["title"] = self.title
        if self.uri:
            payload["uri"] = self.uri
        return payload


@dataclass(slots=True)
class KnowledgeQuery:
    """Stable retrieval request for one execution."""

    text: str
    goal: str = ""
    top_k: int = 5
    source_names: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload = {
            "text": self.text,
            "top_k": self.top_k,
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.goal:
            payload["goal"] = self.goal
        if self.source_names:
            payload["source_names"] = list(self.source_names)
        return payload


@dataclass(slots=True)
class KnowledgeCitation:
    """Stable citation attached to evidence."""

    source_name: str
    title: str = ""
    uri: str = ""
    snippet: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload = {
            "source_name": self.source_name,
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.title:
            payload["title"] = self.title
        if self.uri:
            payload["uri"] = self.uri
        if self.snippet:
            payload["snippet"] = self.snippet
        return payload


@dataclass(slots=True)
class KnowledgeEvidenceItem:
    """Stable evidence item used at execution time."""

    source_name: str
    content: str
    title: str = ""
    uri: str = ""
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_name": self.source_name,
            "content": self.content,
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.title:
            payload["title"] = self.title
        if self.uri:
            payload["uri"] = self.uri
        if self.score is not None:
            payload["score"] = self.score
        return payload


@dataclass(slots=True)
class KnowledgeEvidence:
    """Stable retrieval evidence contract."""

    query: KnowledgeQuery
    items: list[KnowledgeEvidenceItem] = field(default_factory=list)
    citations: list[KnowledgeCitation] = field(default_factory=list)
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": self.query.to_context_payload(),
            "items": [item.to_context_payload() for item in self.items],
            "citations": [citation.to_context_payload() for citation in self.citations],
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.relevance_score is not None:
            payload["relevance_score"] = self.relevance_score
        return payload


@dataclass(slots=True)
class KnowledgeBundle:
    """Stable aggregated knowledge bundle for one run."""

    query: KnowledgeQuery
    evidences: list[KnowledgeEvidence] = field(default_factory=list)
    items: list[KnowledgeEvidenceItem] = field(default_factory=list)
    citations: list[KnowledgeCitation] = field(default_factory=list)
    relevance_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_context_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": self.query.to_context_payload(),
            "evidences": [evidence.to_context_payload() for evidence in self.evidences],
            "items": [item.to_context_payload() for item in self.items],
            "citations": [citation.to_context_payload() for citation in self.citations],
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.relevance_score is not None:
            payload["relevance_score"] = self.relevance_score
        return payload


@dataclass(slots=True)
class KnowledgeResolver:
    """Adapter for dynamic knowledge access."""

    handler: Callable[[KnowledgeQuery], KnowledgeEvidence]
    mode: str = "callable"
    description: str = ""
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def callable(
        cls,
        handler: Callable[[KnowledgeQuery], KnowledgeEvidence],
        *,
        description: str = "",
        extensions: dict[str, Any] | None = None,
    ) -> KnowledgeResolver:
        return cls(
            handler=handler,
            mode="callable",
            description=description,
            extensions=dict(extensions or {}),
        )

    def resolve(self, query: KnowledgeQuery) -> KnowledgeEvidence:
        evidence = self.handler(query)
        if not isinstance(evidence, KnowledgeEvidence):
            raise TypeError(f"knowledge resolver must return KnowledgeEvidence, got {type(evidence).__name__}")
        return evidence

    def to_context_payload(self) -> dict[str, Any]:
        payload = {
            "mode": self.mode,
            "description": self.description,
            "extensions": dict(self.extensions),
        }
        return payload


@dataclass(slots=True)
class KnowledgeSource:
    """Public declarative knowledge source definition."""

    name: str
    description: str = ""
    documents: list[KnowledgeDocument] = field(default_factory=list)
    resolver: KnowledgeResolver | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def inline(
        cls,
        name: str,
        documents: list[str] | list[KnowledgeDocument],
        *,
        description: str = "",
        metadata: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> KnowledgeSource:
        normalized_documents: list[KnowledgeDocument] = []
        for document in documents:
            if isinstance(document, KnowledgeDocument):
                normalized_documents.append(document)
            else:
                normalized_documents.append(KnowledgeDocument(content=document))
        return cls(
            name=name,
            description=description,
            documents=normalized_documents,
            metadata=dict(metadata or {}),
            extensions=dict(extensions or {}),
        )

    @classmethod
    def dynamic(
        cls,
        name: str,
        resolver: KnowledgeResolver,
        *,
        description: str = "",
        metadata: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> KnowledgeSource:
        return cls(
            name=name,
            description=description,
            resolver=resolver,
            metadata=dict(metadata or {}),
            extensions=dict(extensions or {}),
        )

    def resolve(self, query: KnowledgeQuery) -> KnowledgeEvidence:
        if query.source_names and self.name not in query.source_names:
            return KnowledgeEvidence(query=query)

        if self.resolver is not None:
            return self.resolver.resolve(query)

        items = [
            KnowledgeEvidenceItem(
                source_name=self.name,
                content=document.content,
                title=document.title,
                uri=document.uri,
                metadata=dict(document.metadata),
                extensions=dict(document.extensions),
            )
            for document in self.documents[: query.top_k]
        ]
        citations = [
            KnowledgeCitation(
                source_name=self.name,
                title=item.title,
                uri=item.uri,
                metadata=dict(item.metadata),
            )
            for item in items
        ]
        return KnowledgeEvidence(
            query=query,
            items=items,
            citations=citations,
            metadata=dict(self.metadata),
            relevance_score=1.0 if items else 0.0,
        )

    def to_context_payload(self) -> dict[str, Any]:
        """Serialize a knowledge source for prompt/runtime context."""
        payload: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "metadata": dict(self.metadata),
            "extensions": dict(self.extensions),
        }
        if self.documents:
            payload["documents"] = [document.to_context_payload() for document in self.documents]
        if self.resolver is not None:
            payload["resolver"] = self.resolver.to_context_payload()
        return payload


# ---------------------------------------------------------------------------
# Top-level agent assembly
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AgentConfig:
    """Top-level public configuration for one Loom agent."""

    model: ModelRef
    instructions: str = ""
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    tools: list[ToolSpec] = field(default_factory=list)
    policy: PolicyConfig | None = None
    memory: MemoryConfig | None = None
    heartbeat: HeartbeatConfig | None = None
    runtime: RuntimeConfig | None = None
    safety_rules: list[SafetyRule] | None = None
    knowledge: list[KnowledgeSource] = field(default_factory=list)


__all__ = [
    "ModelRef",
    "GenerationConfig",
    "ToolParameterSpec",
    "ToolHandler",
    "ToolSpec",
    "ToolAccessPolicy",
    "ToolRateLimitPolicy",
    "ToolPolicy",
    "PolicyContext",
    "PolicyConfig",
    "MemoryBackend",
    "MemoryConfig",
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
]
