"""Public Loom agent API."""

from __future__ import annotations

import inspect
import logging
import os
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, TypeVar

from .config import (
    AgentConfig,
    FilesystemWatchMethod,
    GenerationConfig,
    HeartbeatConfig,
    HeartbeatInterruptPolicy,
    KnowledgeBundle,
    KnowledgeDocument,
    KnowledgeEvidence,
    KnowledgeQuery,
    KnowledgeResolver,
    KnowledgeSource,
    MemoryBackend,
    MemoryConfig,
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
    ToolSpec,
    WatchConfig,
    WatchKind,
)
from .providers.base import LLMProvider
from .runtime import RunContext, RunEvent, RunResult, Session, SessionConfig
from .runtime.engine import AgentEngine, EngineConfig
from .runtime.heartbeat import Heartbeat, WatchSource
from .runtime.heartbeat import HeartbeatConfig as RuntimeHeartbeatConfig
from .tools.base import Tool, ToolMetadata
from .tools.governance import GovernanceConfig

if TYPE_CHECKING:
    from .tools.schema import Tool as ToolSchema

logger = logging.getLogger(__name__)


@dataclass
class Agent:
    """Loom's single public agent API."""

    config: AgentConfig
    _sessions: dict[str, Session] = field(default_factory=dict, init=False, repr=False)
    _compiled_tools: list[Tool] = field(default_factory=list, init=False, repr=False)
    _provider: LLMProvider | None = field(default=None, init=False, repr=False)
    _provider_resolved: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        config = _normalize_config(self.config, AgentConfig, "config")
        declared_tools = _normalize_tool_specs(config.tools)
        config = replace(
            config,
            model=_normalize_model_ref(config.model),
            tools=declared_tools,
            policy=_normalize_policy_config(config.policy),
            memory=_normalize_memory_config(config.memory),
            heartbeat=_normalize_heartbeat_config(config.heartbeat),
            generation=_normalize_generation_config(config.generation),
            runtime=_normalize_runtime_config(config.runtime),
            knowledge=_normalize_knowledge_sources(config.knowledge),
            safety_rules=_normalize_safety_rules(config.safety_rules),
        )
        self.config = config
        self._compiled_tools = [_compile_tool_spec(tool) for tool in declared_tools]

    def resolve_knowledge(self, query: KnowledgeQuery) -> KnowledgeBundle:
        """Resolve configured knowledge sources for one retrieval request."""
        if not isinstance(query, KnowledgeQuery):
            raise TypeError(f"query must be KnowledgeQuery, got {type(query).__name__}")
        evidence: list[KnowledgeEvidence] = []
        for source in self.config.knowledge:
            resolved = source.resolve(query)
            if resolved.items or resolved.citations:
                evidence.append(resolved)
        return _build_knowledge_bundle(query, evidence)

    async def run(
        self,
        prompt: str,
        context: RunContext | None = None,
    ) -> RunResult:
        """Execute a one-off run."""
        return await self.session().run(prompt, context=context)

    async def stream(
        self,
        prompt: str,
        context: RunContext | None = None,
    ) -> AsyncIterator[RunEvent]:
        """Stream events for a one-off run."""
        async for event in self.session().stream(prompt, context=context):
            yield event

    def session(
        self,
        config: SessionConfig | None = None,
    ) -> Session:
        """Get or create a stateful session."""
        if config is None:
            return Session(self)
        if not isinstance(config, SessionConfig):
            raise TypeError(f"session config must be SessionConfig, got {type(config).__name__}")

        if config.id is not None and config.id in self._sessions:
            session = self._sessions[config.id]
            metadata = config.to_metadata()
            if metadata:
                session.metadata.update(metadata)
            return session

        session = Session(self, config=config)
        self._sessions[session.id] = session
        return session

    async def _execute(
        self,
        prompt: str,
        context: RunContext | None = None,
        *,
        session_id: str | None,
        run_id: str,
        engine: AgentEngine | None = None,
    ) -> dict[str, Any]:
        provider = self._get_provider()
        if provider is None:
            fallback = self.config.runtime.features.fallback if self.config.runtime else RuntimeFallback()
            if fallback.mode == RuntimeFallbackMode.ERROR:
                return {
                    "status": "provider_unavailable",
                    "output": "",
                    "events": [
                        {
                            "type": "run.failed.provider_unavailable",
                            "run_id": run_id,
                        }
                    ],
                    "artifacts": [],
                }
            return {
                "status": "success",
                "output": self._local_output(prompt, context),
                "events": [
                    {
                        "type": "run.fallback",
                        "mode": "local_summary",
                        "run_id": run_id,
                    }
                ],
                "artifacts": [],
            }

        if engine is None:
            engine = self._build_engine(provider)

        merged_context = context.to_payload() if context is not None else {}
        if self.config.knowledge:
            merged_context.setdefault(
                "knowledge_sources",
                [source.to_context_payload() for source in self.config.knowledge],
            )

        return await engine.execute(
            goal=prompt,
            instructions=self.config.instructions,
            context=merged_context,
            session_id=session_id if self.config.memory and self.config.memory.enabled else None,
        )

    def _build_engine(self, provider: LLMProvider) -> AgentEngine:
        engine = AgentEngine(
            provider=provider,
            config=EngineConfig(
                max_iterations=self.config.runtime.limits.max_iterations if self.config.runtime else 100,
                max_tokens=self.config.generation.max_output_tokens
                or (self.config.runtime.limits.max_context_tokens if self.config.runtime else 200000)
                or 200000,
                model=self.config.model.name,
                temperature=self.config.generation.temperature,
                completion_max_tokens=self.config.generation.max_output_tokens or 4096,
                enable_heartbeat=self.config.heartbeat is not None,
                enable_safety=self.config.runtime.features.enable_safety if self.config.runtime else True,
                enable_memory=bool(self.config.memory and self.config.memory.enabled),
            ),
            tools=[self._convert_tool_to_schema(tool) for tool in self._compiled_tools],
        )

        self._configure_governance(engine)
        self._configure_heartbeat(engine)
        self._configure_safety(engine)
        return engine

    def _configure_governance(self, engine: AgentEngine) -> None:
        policy = self.config.policy or PolicyConfig()
        tool_policy = policy.tools or ToolPolicy()
        access = tool_policy.access or ToolAccessPolicy()
        rate_limits = tool_policy.rate_limits or ToolRateLimitPolicy()

        engine.tool_governance.config = GovernanceConfig(
            allow_tools=set(access.allow),
            deny_tools=set(access.deny),
            allow_destructive=access.allow_destructive,
            read_only_only=access.read_only_only,
            max_calls_per_minute=rate_limits.max_calls_per_minute,
            current_context=policy.context.name,
        )

    def _configure_heartbeat(self, engine: AgentEngine) -> None:
        if not self.config.heartbeat:
            return

        hb_config = RuntimeHeartbeatConfig(
            T_hb=self.config.heartbeat.interval,
            delta_hb=self.config.heartbeat.min_entropy_delta,
            watch_sources=[
                WatchSource(type=source.kind.value, config=source.to_runtime_config())
                for source in self.config.heartbeat.watch_sources
            ],
            interrupt_policy=self.config.heartbeat.interrupt_policy.to_runtime_config(),
        )
        engine.heartbeat = Heartbeat(hb_config)

    def _configure_safety(self, engine: AgentEngine) -> None:
        if not self.config.safety_rules or engine.veto_authority is None:
            return

        from .safety.veto import VetoRule

        for rule in self.config.safety_rules:
            engine.veto_authority.add_rule(
                VetoRule(
                    name=rule.name,
                    predicate=rule.matches,
                    reason=rule.reason,
                )
            )

    def _convert_tool_to_schema(self, tool: Tool) -> ToolSchema:
        from .tools.schema import Tool as ToolSchema
        from .tools.schema import ToolDefinition, ToolParameter

        input_schema = tool.input_schema()
        properties = input_schema.get("properties", {})
        required = set(input_schema.get("required", []))

        definition = ToolDefinition(
            name=tool.metadata.name,
            description=tool.metadata.description,
            parameters=[
                ToolParameter(
                    name=parameter_name,
                    type=str(parameter_schema.get("type", "string")),
                    description=str(parameter_schema.get("description", "")),
                    required=parameter_name in required,
                    default=parameter_schema.get("default"),
                )
                for parameter_name, parameter_schema in properties.items()
            ],
            is_read_only=tool.metadata.is_read_only,
            is_destructive=tool.metadata.is_destructive,
            is_concurrency_safe=tool.metadata.is_concurrency_safe,
        )

        async def handler(**kwargs: Any) -> Any:
            result = tool.call(**kwargs)
            payload = result.get("result", result)
            if inspect.isawaitable(payload):
                return await payload
            return payload

        return ToolSchema(definition=definition, handler=handler)

    def _get_provider(self) -> LLMProvider | None:
        if not self._provider_resolved:
            self._provider = _resolve_provider(self.config.model)
            self._provider_resolved = True
        return self._provider

    def _local_output(self, prompt: str, context: RunContext | None) -> str:
        if context is not None:
            payload = context.to_payload()
            if payload:
                return f"Completed goal: {prompt} with context keys {sorted(payload.keys())}"
        return f"Completed goal: {prompt}"


def create_agent(config: AgentConfig) -> Agent:
    """Construct a public Loom agent from one top-level config object."""
    return Agent(config=config)


def tool(
    func: Callable | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    read_only: bool = False,
    destructive: bool = False,
    concurrency_safe: bool = False,
    requires_permission: bool | None = None,
) -> ToolSpec | Callable[[Callable], ToolSpec]:
    """Build a stable ToolSpec from a Python function."""

    def decorator(inner: Callable) -> ToolSpec:
        return ToolSpec.from_function(
            inner,
            name=name,
            description=description,
            read_only=read_only,
            destructive=destructive,
            concurrency_safe=concurrency_safe,
            requires_permission=requires_permission,
        )

    if func is not None:
        return decorator(func)
    return decorator


def _tool_spec_to_tool(spec: ToolSpec) -> Tool:
    metadata = ToolMetadata(
        name=spec.name,
        description=spec.description,
        is_read_only=spec.read_only,
        is_destructive=spec.destructive,
        is_concurrency_safe=spec.concurrency_safe,
        requires_permission=spec.requires_permission,
    )
    schema = spec.to_input_schema()

    class DeclaredTool(Tool):
        def __init__(self) -> None:
            super().__init__(metadata)
            self._schema = schema
            self._handler = spec.handler

        def call(self, **kwargs: Any) -> dict[str, Any]:
            if self._handler is None:
                raise RuntimeError(f"Tool '{spec.name}' does not have a local handler")
            result = self._handler.invoke(**kwargs)
            return {"result": result}

        def input_schema(self) -> dict[str, Any]:
            return self._schema

    return DeclaredTool()


def _resolve_provider(model: ModelRef) -> LLMProvider | None:
    provider_name = model.provider.lower()

    try:
        if provider_name == "anthropic":
            api_key = os.getenv(model.api_key_env or "ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(f"{model.api_key_env or 'ANTHROPIC_API_KEY'} not set")
            from .providers.anthropic import AnthropicProvider

            return AnthropicProvider(api_key=api_key, base_url=model.api_base)

        if provider_name == "openai":
            api_key = os.getenv(model.api_key_env or "OPENAI_API_KEY")
            if not api_key:
                raise ValueError(f"{model.api_key_env or 'OPENAI_API_KEY'} not set")
            from .providers.openai import OpenAIProvider

            return OpenAIProvider(
                api_key=api_key,
                base_url=model.api_base or os.getenv("OPENAI_BASE_URL"),
                organization=model.organization,
            )

        if provider_name == "gemini":
            api_env = model.api_key_env
            api_key = os.getenv(api_env) if api_env else os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError(f"{api_env or 'GEMINI_API_KEY or GOOGLE_API_KEY'} not set")
            from .providers.gemini import GeminiProvider

            return GeminiProvider(api_key=api_key)

        if provider_name == "qwen":
            api_key = os.getenv(model.api_key_env or "DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError(f"{model.api_key_env or 'DASHSCOPE_API_KEY'} not set")
            from .providers.qwen import QwenProvider

            return QwenProvider(api_key=api_key)

        if provider_name == "ollama":
            from .providers.ollama import OllamaProvider

            return OllamaProvider(
                base_url=model.api_base or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
            )

        raise ValueError(f"Unknown provider: {provider_name}")
    except Exception as exc:
        logger.warning("Failed to initialize provider %s: %s", provider_name, exc)
        return None


T = TypeVar("T")


def _normalize_config(value: T, expected_type: type[T], field_name: str) -> T:
    if not isinstance(value, expected_type):
        raise TypeError(f"{field_name} must be {expected_type.__name__}, got {type(value).__name__}")
    return value


def _normalize_optional_config(value: T | None, expected_type: type[T], field_name: str) -> T | None:
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
    return replace(
        memory,
        backend=_normalize_memory_backend(memory.backend),
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
                kind=_normalize_config(source.kind, WatchKind, f"heartbeat.watch_sources[{index}].kind"),
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
        mode=_normalize_config(fallback.mode, RuntimeFallbackMode, "runtime.features.fallback.mode"),
        extensions=_normalize_mapping(
            fallback.extensions,
            "runtime.features.fallback.extensions",
        ),
    )


def _normalize_tool_specs(entries: list[ToolSpec]) -> list[ToolSpec]:
    normalized: list[ToolSpec] = []
    for index, entry in enumerate(entries):
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


def _compile_tool_spec(spec: ToolSpec) -> Tool:
    return _tool_spec_to_tool(spec)


def _normalize_safety_rules(rules: list[SafetyRule] | None) -> list[SafetyRule] | None:
    if rules is None:
        return None
    normalized: list[SafetyRule] = []
    for index, rule in enumerate(rules):
        if not isinstance(rule, SafetyRule):
            raise TypeError(f"safety_rules entries must be SafetyRule, got {type(rule).__name__}")
        evaluator = rule.evaluator
        if evaluator is not None:
            evaluator = _normalize_config(evaluator, SafetyEvaluator, f"safety_rules[{index}].evaluator")
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
            raise TypeError(f"knowledge entries must be KnowledgeSource, got {type(source).__name__}")
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
            resolver = _normalize_config(resolver, KnowledgeResolver, f"knowledge[{index}].resolver")
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


def _build_knowledge_bundle(
    query: KnowledgeQuery,
    evidences: list[KnowledgeEvidence],
) -> KnowledgeBundle:
    items: list[Any] = []
    citations: list[Any] = []
    relevance_values: list[float] = []

    for evidence in evidences:
        items.extend(evidence.items)
        citations.extend(evidence.citations)
        if evidence.relevance_score is not None:
            relevance_values.append(evidence.relevance_score)

    items.sort(key=lambda item: item.score if item.score is not None else 0.0, reverse=True)

    relevance_score = sum(relevance_values) / len(relevance_values) if relevance_values else None
    return KnowledgeBundle(
        query=query,
        evidences=evidences,
        items=items,
        citations=citations,
        relevance_score=relevance_score,
    )
