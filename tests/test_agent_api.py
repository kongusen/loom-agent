"""Tests for Loom's public Agent API."""

from unittest.mock import patch

import pytest

import loom.config as loom_config
from loom import (
    Agent,
    AgentConfig,
    GenerationConfig,
    KnowledgeDocument,
    KnowledgeQuery,
    KnowledgeSource,
    ModelRef,
    RunContext,
    SessionConfig,
    create_agent,
    tool,
)
from loom.config import (
    FilesystemWatchMethod,
    HeartbeatConfig,
    HeartbeatInterruptPolicy,
    KnowledgeBundle,
    KnowledgeCitation,
    KnowledgeEvidence,
    KnowledgeEvidenceItem,
    KnowledgeResolver,
    MemoryBackend,
    MemoryConfig,
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
    ToolPolicy,
    ToolRateLimitPolicy,
    ToolSpec,
    WatchConfig,
    WatchKind,
)
from loom.runtime import RunState


def test_agent_creation():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="Test agent",
            policy=PolicyConfig(
                tools=ToolPolicy(
                    access=ToolAccessPolicy(allow=["read_file"]),
                    rate_limits=ToolRateLimitPolicy(max_calls_per_minute=30),
                ),
                context=PolicyContext.named("repo"),
            ),
            knowledge=[
                KnowledgeSource.inline(
                    "repo-docs",
                    [
                        KnowledgeDocument(content="Loom uses an execution loop.", title="Loop"),
                        KnowledgeDocument(content="Loom supports sessions.", title="Sessions"),
                    ],
                    description="Repository docs",
                )
            ],
            heartbeat=HeartbeatConfig(
                interval=5.0,
                watch_sources=[WatchConfig.filesystem(paths=["./src"], method=FilesystemWatchMethod.HASH)],
            ),
            safety_rules=[
                SafetyRule.block_tool(
                    name="no_delete",
                    tool_names=["delete_file"],
                    reason="blocked",
                )
            ],
            runtime=RuntimeConfig(
                limits=RuntimeLimits(max_iterations=12),
            ),
        )
    )

    assert isinstance(agent, Agent)
    assert agent.config.model.identifier == "anthropic:claude-sonnet-4"
    assert agent.config.instructions == "Test agent"
    assert agent.config.policy.tools.access.allow == ["read_file"]
    assert agent.config.policy.tools.rate_limits.max_calls_per_minute == 30
    assert agent.config.policy.context.name == "repo"
    assert agent.config.knowledge[0].name == "repo-docs"
    assert agent.config.knowledge[0].documents[0].title == "Loop"
    assert agent.config.heartbeat.interval == 5.0
    assert agent.config.heartbeat.watch_sources[0].paths == ["./src"]
    assert agent.config.runtime.limits.max_iterations == 12


def test_agent_config_is_single_source_of_truth():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="Configured once",
            tools=[
                ToolSpec.from_function(
                    lambda query: query,
                    name="sample_tool",
                    description="Echo tool",
                )
            ],
            memory=MemoryConfig(enabled=True, backend=MemoryBackend.in_memory()),
            heartbeat=HeartbeatConfig(interval=3.0),
            safety_rules=[
                SafetyRule.block_tool(
                    name="no_delete",
                    reason="blocked",
                    tool_names=["delete_file"],
                )
            ],
        )
    )

    assert agent.config.instructions == "Configured once"
    assert agent.config.memory.backend.name == "in_memory"
    assert agent.config.heartbeat.interval == 3.0
    assert len(agent.config.tools) == 1
    assert len(agent.config.safety_rules) == 1
    assert not hasattr(agent, "configure")
    assert not hasattr(agent, "with_tools")
    assert not hasattr(agent, "with_instructions")


def test_generation_config_is_stable_object():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            generation=GenerationConfig(
                temperature=0.2,
                max_output_tokens=512,
            ),
        )
    )

    assert agent.config.generation.temperature == 0.2
    assert agent.config.generation.max_output_tokens == 512


def test_session_requires_session_config():
    agent = create_agent(AgentConfig(model=ModelRef.anthropic("claude-sonnet-4")))

    session = agent.session(SessionConfig(id="demo", metadata={"tenant": "acme"}))

    assert session.id == "demo"
    assert session.metadata["tenant"] == "acme"

    with pytest.raises(TypeError):
        agent.session("demo")  # type: ignore[arg-type]


def test_config_module_exports_only_configuration_vocabulary():
    exported = set(loom_config.__all__)

    assert "AgentConfig" in exported
    assert "ModelRef" in exported
    assert "RuntimeConfig" in exported
    assert "KnowledgeSource" in exported
    assert "SessionConfig" not in exported
    assert "RunContext" not in exported


def test_rejects_legacy_dict_configs():
    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model="anthropic:claude-sonnet-4",  # type: ignore[arg-type]
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                generation={"temperature": 0.1},  # type: ignore[arg-type]
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                heartbeat={"interval": 5.0},  # type: ignore[arg-type]
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                safety_rules=[{"name": "no_delete"}],  # type: ignore[list-item]
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                tools=[lambda query: query],  # type: ignore[list-item]
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                knowledge=["docs"],  # type: ignore[list-item]
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                knowledge=[
                    KnowledgeSource.dynamic(
                        "repo",
                        resolver=lambda question: question,  # type: ignore[arg-type]
                    )
                ],
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                knowledge=[
                    KnowledgeSource(
                        name="repo",
                        documents=["raw text"],  # type: ignore[list-item]
                    )
                ],
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                safety_rules=[
                    SafetyRule.custom(
                        name="custom",
                        reason="blocked",
                        evaluator=lambda tool, args: False,  # type: ignore[arg-type]
                    )
                ],
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                memory=MemoryConfig(backend="in_memory"),  # type: ignore[arg-type]
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                policy=PolicyConfig(
                    tools={"access": {"allow": ["read_file"]}},  # type: ignore[arg-type]
                ),
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                policy=PolicyConfig(
                    context="default",  # type: ignore[arg-type]
                ),
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                heartbeat=HeartbeatConfig(
                    interrupt_policy={"low": "queue"},  # type: ignore[arg-type]
                ),
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                heartbeat=HeartbeatConfig(
                    watch_sources=[WatchConfig.filesystem(paths=["./src"], method="hash")],  # type: ignore[arg-type]
                ),
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                heartbeat=HeartbeatConfig(
                    watch_sources=[
                        WatchConfig(
                            kind=WatchKind.RESOURCE,
                            thresholds={"memory_pct": 80},  # type: ignore[arg-type]
                        )
                    ],
                ),
            )
        )

    from loom.safety.veto import VetoRule

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                safety_rules=[
                    VetoRule(
                        name="legacy_rule",
                        predicate=lambda t, a: False,
                        reason="legacy",
                    )
                ],  # type: ignore[list-item]
            )
        )


@pytest.mark.asyncio
async def test_run_without_provider_uses_local_fallback():
    with patch("loom.agent._resolve_provider", return_value=None):
        agent = create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                knowledge=[KnowledgeSource.inline("repo", ["Loom framework"])],
                heartbeat=HeartbeatConfig(
                    watch_sources=[
                        WatchConfig.resource(
                            thresholds=ResourceThresholds(memory_pct=80.0),
                        )
                    ],
                    interrupt_policy=HeartbeatInterruptPolicy(low="queue", high="request", critical="force"),
                ),
            )
        )
        result = await agent.run(
            "Summarize the repo",
            context=RunContext(inputs={"repo": "loom-agent"}),
        )

    assert result.state == RunState.COMPLETED
    assert result.output == "Completed goal: Summarize the repo with context keys ['repo']"
    assert any(event.type == "run.fallback" for event in result.events)
    assert agent.config.heartbeat.watch_sources[0].thresholds.memory_pct == 80.0

    with pytest.raises(TypeError):
        await agent.run("Summarize the repo", context={"repo": "loom-agent"})  # type: ignore[arg-type]


def test_dynamic_knowledge_source_context_is_declarative():
    resolver = KnowledgeResolver.callable(
        lambda query: KnowledgeEvidence(
            query=query,
            items=[
                KnowledgeEvidenceItem(
                    source_name="repo",
                    content=f"Answer for {query.text}",
                    title="Dynamic Result",
                )
            ],
        ),
        description="Lookup docs dynamically",
    )
    source = KnowledgeSource.dynamic(
        "repo",
        resolver=resolver,
        description="Repository docs",
    )

    payload = source.to_context_payload()

    assert payload["name"] == "repo"
    assert payload["resolver"]["mode"] == "callable"
    assert "handler" not in payload["resolver"]


def test_knowledge_payload_uses_metadata_field():
    source = KnowledgeSource.inline(
        "repo",
        [
            KnowledgeDocument(
                content="Loom uses sessions.",
                title="Sessions",
                metadata={"section": "runtime"},
            )
        ],
        metadata={"scope": "internal"},
    )

    payload = source.to_context_payload()

    assert payload["metadata"] == {"scope": "internal"}
    assert payload["documents"][0]["metadata"] == {"section": "runtime"}
    assert "attributes" not in payload
    assert "attributes" not in payload["documents"][0]


def test_agent_resolves_knowledge_into_stable_bundle():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            knowledge=[
                KnowledgeSource.inline(
                    "repo",
                    [
                        KnowledgeDocument(
                            content="Sessions preserve state across runs.",
                            title="Sessions",
                            uri="file:///repo/sessions.md",
                        )
                    ],
                )
            ],
        )
    )

    bundle = agent.resolve_knowledge(KnowledgeQuery(text="session state", top_k=1))

    assert isinstance(bundle, KnowledgeBundle)
    assert bundle.items[0].source_name == "repo"
    assert bundle.citations[0].title == "Sessions"
    assert bundle.evidences[0].query.text == "session state"


def test_run_context_serializes_knowledge_bundle():
    evidence = KnowledgeEvidence(
        query=KnowledgeQuery(text="sessions"),
        items=[
            KnowledgeEvidenceItem(
                source_name="repo",
                content="Sessions preserve run state.",
            )
        ],
        citations=[
            KnowledgeCitation(
                source_name="repo",
                title="Sessions",
            )
        ],
    )
    bundle = KnowledgeBundle(
        query=KnowledgeQuery(text="sessions"),
        evidences=[evidence],
        items=evidence.items,
        citations=evidence.citations,
    )

    payload = RunContext(inputs={"repo": "loom-agent"}, knowledge=bundle).to_payload()

    assert payload["repo"] == "loom-agent"
    assert payload["knowledge"]["query"]["text"] == "sessions"
    assert payload["knowledge"]["items"][0]["source_name"] == "repo"


def test_knowledge_payload_preserves_scores_and_relevance():
    evidence_item = KnowledgeEvidenceItem(
        source_name="repo",
        content="Sessions preserve run state.",
        score=0.9,
    )
    citation = KnowledgeCitation(
        source_name="repo",
        title="Sessions",
        snippet="Sessions preserve run state.",
    )
    evidence = KnowledgeEvidence(
        query=KnowledgeQuery(text="sessions"),
        items=[evidence_item],
        citations=[citation],
        relevance_score=0.8,
        metadata={"scope": "runtime"},
    )
    bundle = KnowledgeBundle(
        query=KnowledgeQuery(text="sessions"),
        evidences=[evidence],
        items=[evidence_item],
        citations=[citation],
        relevance_score=0.75,
    )

    payload = bundle.to_context_payload()

    assert payload["items"][0]["score"] == 0.9
    assert payload["evidences"][0]["relevance_score"] == 0.8
    assert payload["relevance_score"] == 0.75
    assert payload["evidences"][0]["metadata"] == {"scope": "runtime"}


def test_tool_decorator_returns_declared_tool_spec():
    @tool(read_only=True)
    def search_docs(query: str) -> str:
        return query

    assert isinstance(search_docs, ToolSpec)
    assert search_docs.name == "search_docs"
    assert search_docs.read_only is True
    assert search_docs.parameters[0].name == "query"


def test_custom_safety_rule_uses_evaluator_adapter():
    rule = SafetyRule.custom(
        name="business_hours_only",
        reason="blocked",
        evaluator=SafetyEvaluator.callable(
            lambda tool, args: tool == "modify_config" and args.get("env") == "prod"
        ),
    )

    assert rule.matches("modify_config", {"env": "prod"}) is True
    assert rule.matches("modify_config", {"env": "dev"}) is False


def test_rejects_legacy_runtime_objects():
    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                runtime=RuntimeConfig(
                    limits={"max_iterations": 8},  # type: ignore[arg-type]
                ),
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                policy=PolicyConfig(
                    tools=ToolPolicy(
                        access={"allow": ["read_file"]},  # type: ignore[arg-type]
                    ),
                ),
            )
        )

    with pytest.raises(TypeError):
        create_agent(
            AgentConfig(
                model=ModelRef.anthropic("claude-sonnet-4"),
                runtime=RuntimeConfig(
                    features=RuntimeFeatures(
                        fallback="local_summary",  # type: ignore[arg-type]
                    ),
                ),
            )
        )


@pytest.mark.asyncio
async def test_runtime_fallback_mode_can_fail_closed():
    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            runtime=RuntimeConfig(
                features=RuntimeFeatures(
                    fallback=RuntimeFallback(mode=RuntimeFallbackMode.ERROR),
                ),
            ),
        )
    )

    result = await agent.run("Summarize the repo")

    assert result.state == RunState.FAILED
    assert any(event.type == "run.failed.provider_unavailable" for event in result.events)


@pytest.mark.asyncio
async def test_stream_executes_run_and_emits_terminal_event():
    agent = create_agent(AgentConfig(model=ModelRef.anthropic("claude-sonnet-4")))

    received = []
    async for event in agent.stream("Inspect the project layout"):
        received.append(event.type)

    assert received[0] == "run.started"
    assert received[-1] == "run.completed"


@pytest.mark.asyncio
async def test_engine_finalizes_plain_provider_response_without_completion_phrase():
    from loom.providers.base import CompletionParams, LLMProvider
    from loom.runtime.engine import AgentEngine, EngineConfig

    class MockProvider(LLMProvider):
        async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
            return "provider smoke test ok"

        def stream(self, messages: list, params: CompletionParams | None = None):
            async def _gen():
                yield "provider smoke test ok"
            return _gen()

    engine = AgentEngine(
        provider=MockProvider(),
        config=EngineConfig(max_iterations=4, enable_heartbeat=False, enable_memory=False),
    )

    result = await engine.execute(
        goal="Reply with exactly: provider smoke test ok",
        instructions="You are a concise assistant.",
    )

    assert result["status"] == "success"
    assert result["output"] == "provider smoke test ok"


@pytest.mark.asyncio
async def test_agent_run_executes_tool_call_round_trip():
    from loom.providers.base import CompletionParams, CompletionResponse, LLMProvider
    from loom.types import ToolCall

    @tool(description="Add two integers", read_only=True)
    def add(a: int, b: int) -> str:
        return str(a + b)

    class MockProvider(LLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
            return ""

        async def _complete_response(
            self,
            messages: list,
            params: CompletionParams | None = None,
        ) -> CompletionResponse:
            self.calls += 1
            if self.calls == 1:
                assert params is not None
                assert params.tools[0]["name"] == "add"
                return CompletionResponse(
                    tool_calls=[
                        ToolCall(
                            id="call_add_1",
                            name="add",
                            arguments={"a": 2, "b": 3},
                        )
                    ]
                )

            assert any(
                message["role"] == "tool"
                and message["tool_call_id"] == "call_add_1"
                and message["content"] == "5"
                for message in messages
            )
            return CompletionResponse(content="The answer is 5.")

        def stream(self, messages: list, params: CompletionParams | None = None):
            async def _gen():
                yield "The answer is 5."
            return _gen()

    agent = create_agent(
        AgentConfig(
            model=ModelRef.openai("gpt-test"),
            instructions="Use tools when needed.",
            tools=[add],
        )
    )
    agent._provider = MockProvider()
    agent._provider_resolved = True

    result = await agent.run("What is 2 + 3?")

    assert result.state == RunState.COMPLETED
    assert result.output == "The answer is 5."
    assert any(event.type == "tools.requested" for event in result.events)
    assert any(event.type == "tools.executed" for event in result.events)
