"""Public Agent configuration normalization helpers."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Any, TypeVar

from ..config import (
    FilesystemWatchMethod,
    GenerationConfig,
    HeartbeatConfig,
    HeartbeatInterruptPolicy,
    KnowledgeDocument,
    KnowledgeResolver,
    KnowledgeSource,
    MemoryBackend,
    MemoryConfig,
    MemoryExtractor,
    MemoryProvider,
    MemoryResolver,
    MemorySource,
    MemoryStore,
    ModelRef,
    PolicyConfig,
    PolicyContext,
    ResourceThresholds,
    RuntimeConfig,
    RuntimeFallback,
    RuntimeFallbackMode,
    RuntimeFeatures,
    RuntimeLimits,
    SafetyEvaluator,
    SafetyRule,
    ToolAccessPolicy,
    ToolHandler,
    ToolPolicy,
    ToolRateLimitPolicy,
    Toolset,
    ToolSpec,
    WatchConfig,
    WatchKind,
)
from ..context import CompressionPolicy
from ..runtime.capability import CapabilitySource, CapabilitySpec

logger = logging.getLogger(__name__)


T = TypeVar("T")


def _normalize_config(value: T, expected_type: type[T], field_name: str) -> T:
    if not isinstance(value, expected_type):
        raise TypeError(
            f"{field_name} must be {expected_type.__name__}, got {type(value).__name__}"
        )
    return value


def _normalize_optional_config(
    value: T | None, expected_type: type[T], field_name: str
) -> T | None:
    if value is None:
        return None
    return _normalize_config(value, expected_type, field_name)


def _normalize_mapping(value: dict[str, Any], field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be dict, got {type(value).__name__}")
    return dict(value)


def _normalize_string_mapping(value: dict[str, str], field_name: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be dict, got {type(value).__name__}")
    return dict(value)


def _normalize_policy_config(value: PolicyConfig | None) -> PolicyConfig | None:
    policy = _normalize_optional_config(value, PolicyConfig, "policy")
    if policy is None:
        return None
    return replace(
        policy,
        tools=_normalize_tool_policy(policy.tools),
        context=_normalize_policy_context(policy.context),
        extensions=_normalize_mapping(policy.extensions, "policy.extensions"),
    )


def _normalize_model_ref(value: ModelRef) -> ModelRef:
    model = _normalize_config(value, ModelRef, "model")
    return replace(
        model,
        extensions=_normalize_mapping(model.extensions, "model.extensions"),
    )


def _normalize_memory_config(value: MemoryConfig | None) -> MemoryConfig | None:
    memory = _normalize_optional_config(value, MemoryConfig, "memory")
    if memory is None:
        return None
    sources: list[MemorySource] = []
    for index, source in enumerate(memory.sources):
        if not isinstance(source, MemorySource):
            raise TypeError(
                f"memory.sources[{index}] must be MemorySource, got {type(source).__name__}"
            )
        if not isinstance(source.resolver, MemoryResolver):
            raise TypeError(
                f"memory.sources[{index}].resolver must be MemoryResolver, "
                f"got {type(source.resolver).__name__}"
            )
        if not isinstance(source.extractor, MemoryExtractor):
            raise TypeError(
                f"memory.sources[{index}].extractor must be MemoryExtractor, "
                f"got {type(source.extractor).__name__}"
            )
        if source.store is not None and not isinstance(source.store, MemoryStore):
            raise TypeError(
                f"memory.sources[{index}].store must be MemoryStore, "
                f"got {type(source.store).__name__}"
            )
        sources.append(source)
    providers: list[MemoryProvider] = []
    for index, provider in enumerate(memory.providers):
        if not isinstance(provider, MemoryProvider):
            raise TypeError(
                f"memory.providers[{index}] must be MemoryProvider, got {type(provider).__name__}"
            )
        providers.append(provider)
    return replace(
        memory,
        backend=_normalize_memory_backend(memory.backend),
        sources=sources,
        providers=providers,
        extensions=_normalize_mapping(memory.extensions, "memory.extensions"),
    )


def _normalize_runtime_config(value: RuntimeConfig | None) -> RuntimeConfig | None:
    runtime = _normalize_optional_config(value, RuntimeConfig, "runtime")
    if runtime is None:
        return None
    return replace(
        runtime,
        limits=_normalize_runtime_limits(runtime.limits),
        features=_normalize_runtime_features(runtime.features),
        extensions=_normalize_mapping(runtime.extensions, "runtime.extensions"),
    )


def _resolve_session_ttl_hours(runtime: RuntimeConfig | None) -> float:
    if runtime is None:
        return 24.0

    raw_value = runtime.extensions.get("session_ttl_hours")
    if raw_value is None:
        return 24.0

    try:
        ttl_hours = float(raw_value)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid runtime.extensions.session_ttl_hours=%r, falling back to 24 hours",
            raw_value,
        )
        return 24.0

    if ttl_hours <= 0:
        logger.warning(
            "Non-positive runtime.extensions.session_ttl_hours=%r, falling back to 24 hours",
            raw_value,
        )
        return 24.0
    return ttl_hours


def _is_provider_health_check_enabled(runtime: RuntimeConfig | None) -> bool:
    if runtime is None:
        return True

    raw_value = runtime.extensions.get("provider_health_check", True)
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        return raw_value.strip().lower() not in {"0", "false", "off", "no"}
    return bool(raw_value)


def _resolve_compression_policy(runtime: RuntimeConfig | None) -> CompressionPolicy | None:
    if runtime is None:
        return None

    raw_value = runtime.extensions.get("compression_policy")
    if raw_value is None:
        return None
    if isinstance(raw_value, CompressionPolicy):
        return raw_value
    if not isinstance(raw_value, dict):
        logger.warning(
            "Invalid runtime.extensions.compression_policy=%r, expected dict",
            raw_value,
        )
        return None

    try:
        return CompressionPolicy(
            snip_at=float(raw_value.get("snip_at", 0.7)),
            micro_at=float(raw_value.get("micro_at", 0.8)),
            collapse_at=float(raw_value.get("collapse_at", 0.9)),
            auto_compact_at=float(raw_value.get("auto_compact_at", 0.95)),
        )
    except (TypeError, ValueError) as exc:
        logger.warning(
            "Invalid runtime.extensions.compression_policy=%r (%s), using defaults",
            raw_value,
            exc,
        )
        return None


def _normalize_generation_config(value: GenerationConfig) -> GenerationConfig:
    generation = _normalize_config(value, GenerationConfig, "generation")
    return replace(
        generation,
        extensions=_normalize_mapping(generation.extensions, "generation.extensions"),
    )


def _normalize_heartbeat_config(value: HeartbeatConfig | None) -> HeartbeatConfig | None:
    heartbeat = _normalize_optional_config(value, HeartbeatConfig, "heartbeat")
    if heartbeat is None:
        return None
    interrupt_policy = _normalize_config(
        heartbeat.interrupt_policy,
        HeartbeatInterruptPolicy,
        "heartbeat.interrupt_policy",
    )
    interrupt_policy = replace(
        interrupt_policy,
        extensions=_normalize_string_mapping(
            interrupt_policy.extensions,
            "heartbeat.interrupt_policy.extensions",
        ),
    )
    return replace(
        heartbeat,
        watch_sources=_normalize_watch_sources(heartbeat.watch_sources),
        interrupt_policy=interrupt_policy,
    )


def _normalize_watch_sources(sources: list[WatchConfig]) -> list[WatchConfig]:
    normalized: list[WatchConfig] = []
    for index, source in enumerate(sources):
        source = _normalize_config(source, WatchConfig, f"heartbeat.watch_sources[{index}]")
        thresholds = source.thresholds
        if thresholds is not None:
            thresholds = _normalize_config(
                thresholds,
                ResourceThresholds,
                f"heartbeat.watch_sources[{index}].thresholds",
            )
            thresholds = replace(
                thresholds,
                extensions=_normalize_mapping(
                    thresholds.extensions,
                    f"heartbeat.watch_sources[{index}].thresholds.extensions",
                ),
            )
        normalized.append(
            replace(
                source,
                kind=_normalize_config(
                    source.kind, WatchKind, f"heartbeat.watch_sources[{index}].kind"
                ),
                method=_normalize_optional_config(
                    source.method,
                    FilesystemWatchMethod,
                    f"heartbeat.watch_sources[{index}].method",
                ),
                paths=list(source.paths),
                watch_pids=list(source.watch_pids),
                topics=list(source.topics),
                thresholds=thresholds,
                extensions=_normalize_mapping(
                    source.extensions,
                    f"heartbeat.watch_sources[{index}].extensions",
                ),
            )
        )
    return normalized


def _normalize_tool_policy(value: ToolPolicy) -> ToolPolicy:
    policy = _normalize_config(value, ToolPolicy, "policy.tools")
    return replace(
        policy,
        access=_normalize_tool_access_policy(policy.access),
        rate_limits=_normalize_tool_rate_limit_policy(policy.rate_limits),
        extensions=_normalize_mapping(policy.extensions, "policy.tools.extensions"),
    )


def _normalize_tool_access_policy(value: ToolAccessPolicy) -> ToolAccessPolicy:
    policy = _normalize_config(value, ToolAccessPolicy, "policy.tools.access")
    return replace(
        policy,
        allow=list(policy.allow),
        deny=list(policy.deny),
    )


def _normalize_tool_rate_limit_policy(value: ToolRateLimitPolicy) -> ToolRateLimitPolicy:
    return _normalize_config(value, ToolRateLimitPolicy, "policy.tools.rate_limits")


def _normalize_policy_context(value: PolicyContext) -> PolicyContext:
    context = _normalize_config(value, PolicyContext, "policy.context")
    return replace(
        context,
        extensions=_normalize_mapping(context.extensions, "policy.context.extensions"),
    )


def _normalize_memory_backend(value: MemoryBackend) -> MemoryBackend:
    backend = _normalize_config(value, MemoryBackend, "memory.backend")
    return replace(
        backend,
        options=_normalize_mapping(backend.options, "memory.backend.options"),
        extensions=_normalize_mapping(backend.extensions, "memory.backend.extensions"),
    )


def _normalize_runtime_limits(value: RuntimeLimits) -> RuntimeLimits:
    limits = _normalize_config(value, RuntimeLimits, "runtime.limits")
    return replace(
        limits,
        extensions=_normalize_mapping(limits.extensions, "runtime.limits.extensions"),
    )


def _normalize_runtime_features(value: RuntimeFeatures) -> RuntimeFeatures:
    features = _normalize_config(value, RuntimeFeatures, "runtime.features")
    return replace(
        features,
        fallback=_normalize_runtime_fallback(features.fallback),
        extensions=_normalize_mapping(features.extensions, "runtime.features.extensions"),
    )


def _normalize_runtime_fallback(value: RuntimeFallback) -> RuntimeFallback:
    fallback = _normalize_config(value, RuntimeFallback, "runtime.features.fallback")
    return replace(
        fallback,
        mode=_normalize_config(
            fallback.mode, RuntimeFallbackMode, "runtime.features.fallback.mode"
        ),
        extensions=_normalize_mapping(
            fallback.extensions,
            "runtime.features.fallback.extensions",
        ),
    )


def _normalize_tool_specs(entries: list[ToolSpec | Toolset]) -> list[ToolSpec]:
    normalized: list[ToolSpec] = []
    flattened: list[ToolSpec] = []
    for entry in entries:
        if isinstance(entry, ToolSpec):
            flattened.append(entry)
        elif isinstance(entry, Toolset):
            flattened.extend(entry.tools)
        else:
            raise TypeError(
                f"tools entries must be ToolSpec or Toolset, got {type(entry).__name__}"
            )

    for index, entry in enumerate(flattened):
        if isinstance(entry, ToolSpec):
            handler = entry.handler
            if handler is None:
                raise TypeError(f"tools[{index}].handler must be ToolHandler, got None")
            handler = _normalize_config(handler, ToolHandler, f"tools[{index}].handler")
            normalized.append(
                replace(
                    entry,
                    handler=replace(
                        handler,
                        extensions=_normalize_mapping(
                            handler.extensions,
                            f"tools[{index}].handler.extensions",
                        ),
                    ),
                    extensions=_normalize_mapping(entry.extensions, f"tools[{index}].extensions"),
                )
            )
        else:
            raise TypeError(f"tools entries must be ToolSpec, got {type(entry).__name__}")
    return normalized


def _normalize_capability_specs(entries: list[Any] | None) -> list[CapabilitySpec]:
    if not entries:
        return []

    normalized: list[CapabilitySpec] = []
    for index, entry in enumerate(entries):
        if isinstance(entry, CapabilitySpec):
            normalized.append(_normalize_capability_spec(entry, f"capabilities[{index}]"))
            continue

        capabilities = getattr(entry, "capabilities", None)
        if callable(capabilities):
            provided = capabilities()
            if not isinstance(provided, list | tuple):
                provided = list(provided)
            for provided_index, capability in enumerate(provided):
                if not isinstance(capability, CapabilitySpec):
                    raise TypeError(
                        f"capabilities[{index}].capabilities()[{provided_index}] "
                        f"must be CapabilitySpec, got {type(capability).__name__}"
                    )
                normalized.append(
                    _normalize_capability_spec(
                        capability,
                        f"capabilities[{index}].capabilities()[{provided_index}]",
                    )
                )
            continue

        raise TypeError(
            "capabilities entries must be CapabilitySpec or RuntimeCapabilityProvider, "
            f"got {type(entry).__name__}"
        )
    return normalized


def _normalize_capability_spec(
    capability: CapabilitySpec,
    field_name: str,
) -> CapabilitySpec:
    source = _normalize_config(capability.source, CapabilitySource, f"{field_name}.source")
    tools: list[ToolSpec | Toolset] = []
    for tool_index, tool_entry in enumerate(capability.tools):
        if isinstance(tool_entry, ToolSpec | Toolset):
            tools.append(tool_entry)
        else:
            raise TypeError(
                f"{field_name}.tools[{tool_index}] must be ToolSpec or Toolset, "
                f"got {type(tool_entry).__name__}"
            )
    return replace(
        capability,
        source=source,
        tools=tools,
        metadata=_normalize_mapping(capability.metadata, f"{field_name}.metadata"),
        extensions=_normalize_mapping(capability.extensions, f"{field_name}.extensions"),
    )


def _normalize_safety_rules(rules: list[SafetyRule] | None) -> list[SafetyRule] | None:
    if rules is None:
        return None
    normalized: list[SafetyRule] = []
    for index, rule in enumerate(rules):
        if not isinstance(rule, SafetyRule):
            raise TypeError(f"safety_rules entries must be SafetyRule, got {type(rule).__name__}")
        evaluator = rule.evaluator
        if evaluator is not None:
            evaluator = _normalize_config(
                evaluator, SafetyEvaluator, f"safety_rules[{index}].evaluator"
            )
            evaluator = replace(
                evaluator,
                extensions=_normalize_mapping(
                    evaluator.extensions,
                    f"safety_rules[{index}].evaluator.extensions",
                ),
            )
        normalized.append(
            replace(
                rule,
                tool_names=list(rule.tool_names),
                arg_equals=_normalize_mapping(rule.arg_equals, f"safety_rules[{index}].arg_equals"),
                arg_prefixes=_normalize_string_mapping(
                    rule.arg_prefixes,
                    f"safety_rules[{index}].arg_prefixes",
                ),
                arg_contains_any={
                    name: list(values)
                    for name, values in _normalize_mapping(
                        rule.arg_contains_any,
                        f"safety_rules[{index}].arg_contains_any",
                    ).items()
                },
                evaluator=evaluator,
                extensions=_normalize_mapping(rule.extensions, f"safety_rules[{index}].extensions"),
            )
        )
    return normalized


def _normalize_knowledge_sources(sources: list[KnowledgeSource] | None) -> list[KnowledgeSource]:
    if not sources:
        return []
    normalized: list[KnowledgeSource] = []
    for index, source in enumerate(sources):
        if not isinstance(source, KnowledgeSource):
            raise TypeError(
                f"knowledge entries must be KnowledgeSource, got {type(source).__name__}"
            )
        documents: list[KnowledgeDocument] = []
        for document_index, document in enumerate(source.documents):
            if not isinstance(document, KnowledgeDocument):
                raise TypeError(
                    f"knowledge[{index}].documents[{document_index}] must be KnowledgeDocument, "
                    f"got {type(document).__name__}"
                )
            documents.append(
                replace(
                    document,
                    metadata=_normalize_mapping(
                        document.metadata,
                        f"knowledge[{index}].documents[{document_index}].metadata",
                    ),
                    extensions=_normalize_mapping(
                        document.extensions,
                        f"knowledge[{index}].documents[{document_index}].extensions",
                    ),
                )
            )

        resolver = source.resolver
        if resolver is not None:
            resolver = _normalize_config(
                resolver, KnowledgeResolver, f"knowledge[{index}].resolver"
            )
            resolver = replace(
                resolver,
                extensions=_normalize_mapping(
                    resolver.extensions,
                    f"knowledge[{index}].resolver.extensions",
                ),
            )

        normalized.append(
            replace(
                source,
                documents=documents,
                resolver=resolver,
                metadata=_normalize_mapping(source.metadata, f"knowledge[{index}].metadata"),
                extensions=_normalize_mapping(source.extensions, f"knowledge[{index}].extensions"),
            )
        )
    return normalized
