"""Tests for Loom's public Agent API."""

from unittest.mock import patch

import pytest

import loom.config as loom_config
from loom import (
    Agent,
    AgentConfig,
    AgentSpec,
    AttentionPolicy,
    Capability,
    CapabilityRegistry,
    CapabilitySource,
    DelegationPolicy,
    DelegationRequest,
    DelegationResult,
    FeedbackDecision,
    FeedbackEvent,
    FeedbackPolicy,
    FileSessionStore,
    Generation,
    GenerationConfig,
    GovernanceDecision,
    GovernancePolicy,
    GovernanceRequest,
    InMemorySessionStore,
    KnowledgeDocument,
    KnowledgeQuery,
    KnowledgeSource,
    Memory,
    MemoryProvider,
    Model,
    ModelRef,
    QualityContract,
    QualityGate,
    QualityResult,
    RunContext,
    Runtime,
    RuntimeSignal,
    RuntimeTask,
    SessionConfig,
    SessionStore,
    Toolset,
    TranscriptRecord,
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
from loom.config import (
    Toolset as ConfigToolset,
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
                watch_sources=[
                    WatchConfig.filesystem(paths=["./src"], method=FilesystemWatchMethod.HASH)
                ],
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


def test_runtime_accepts_delegation_policy() -> None:
    delegation = DelegationPolicy.none()
    agent = Agent(
        model=Model.openai("gpt-test"),
        runtime=Runtime(delegation=delegation),
    )

    assert agent.config.runtime.delegation is delegation
    assert DelegationRequest(goal="task").goal == "task"
    assert DelegationResult(success=True, output="ok", depth=1).success is True


def test_runtime_accepts_governance_policy() -> None:
    governance = GovernancePolicy.deny_all("blocked")
    agent = Agent(
        model=Model.openai("gpt-test"),
        runtime=Runtime(governance=governance),
    )

    assert agent.config.runtime.governance is governance
    assert GovernanceRequest(tool_name="Read").tool_name == "Read"
    assert GovernanceDecision(allowed=True).allowed is True


def test_runtime_accepts_feedback_policy() -> None:
    feedback = FeedbackPolicy.collector()
    agent = Agent(
        model=Model.openai("gpt-test"),
        runtime=Runtime(feedback=feedback),
    )

    assert agent.config.runtime.feedback is feedback
    assert FeedbackEvent(type="tool_result").type == "tool_result"
    assert FeedbackDecision(accepted=True).accepted is True


def test_runtime_presets_compose_existing_policies() -> None:
    sdk = Runtime.sdk()
    long_running = Runtime.long_running(criteria=["tests stay green"])
    supervised = Runtime.supervised(criteria=["human approval before release"])
    autonomous = Runtime.autonomous(max_depth=3, max_iterations=150)

    assert sdk.extensions["profile"] == "sdk"
    assert sdk.harness is not None
    assert sdk.governance is not None
    assert sdk.feedback is not None

    assert long_running.extensions["profile"] == "long_running"
    assert long_running.context is not None
    assert long_running.continuity is not None
    assert long_running.quality is not None
    assert long_running.feedback is not None

    assert supervised.extensions["profile"] == "supervised"
    assert supervised.quality is not None
    assert supervised.governance is not None
    assert supervised.feedback is not None

    assert autonomous.extensions["profile"] == "autonomous"
    assert autonomous.limits.max_iterations == 150
    assert autonomous.delegation.max_depth == 3
    assert autonomous.context is not None


def test_runtime_profile_snapshots_are_stable() -> None:
    snapshots = {
        "sdk": Runtime.sdk().describe(),
        "long_running": Runtime.long_running(criteria=["ship safely"]).describe(),
        "supervised": Runtime.supervised(criteria=["reviewed"]).describe(),
        "autonomous": Runtime.autonomous(max_depth=3).describe(),
    }

    assert snapshots == {
        "sdk": {
            "profile": "sdk",
            "limits": {"max_iterations": 32, "max_context_tokens": 64000},
            "features": {"enable_safety": True, "fallback": "local_summary"},
            "policies": {
                "context": None,
                "continuity": None,
                "harness": "SingleRunHarness",
                "quality": None,
                "delegation": None,
                "governance": "DefaultGovernancePolicy",
                "feedback": "NoopFeedbackPolicy",
                "skill_injection": "SkillInjectionPolicy",
                "session_restore": "SessionRestorePolicy",
            },
            "session_restore": {
                "enabled": True,
                "include_transcript": True,
                "include_context": False,
                "include_events": False,
                "include_artifacts": False,
                "max_transcripts": 8,
                "max_messages": 24,
                "max_runtime_items": 12,
                "max_chars": 12000,
            },
            "delegation": None,
        },
        "long_running": {
            "profile": "long_running",
            "limits": {"max_iterations": 128, "max_context_tokens": 200000},
            "features": {"enable_safety": True, "fallback": "local_summary"},
            "policies": {
                "context": "ManagedContextProtocol",
                "continuity": "HandoffContinuityPolicy",
                "harness": "SingleRunHarness",
                "quality": "CriteriaQualityGate",
                "delegation": None,
                "governance": "DefaultGovernancePolicy",
                "feedback": "CollectingFeedbackPolicy",
                "skill_injection": "SkillInjectionPolicy",
                "session_restore": "SessionRestorePolicy",
            },
            "session_restore": {
                "enabled": True,
                "include_transcript": True,
                "include_context": True,
                "include_events": True,
                "include_artifacts": True,
                "max_transcripts": 8,
                "max_messages": 24,
                "max_runtime_items": 12,
                "max_chars": 12000,
            },
            "delegation": None,
        },
        "supervised": {
            "profile": "supervised",
            "limits": {"max_iterations": 80, "max_context_tokens": 120000},
            "features": {"enable_safety": True, "fallback": "local_summary"},
            "policies": {
                "context": "ManagedContextProtocol",
                "continuity": "HandoffContinuityPolicy",
                "harness": "SingleRunHarness",
                "quality": "CriteriaQualityGate",
                "delegation": "NoopDelegationPolicy",
                "governance": "DefaultGovernancePolicy",
                "feedback": "CollectingFeedbackPolicy",
                "skill_injection": "SkillInjectionPolicy",
                "session_restore": "SessionRestorePolicy",
            },
            "session_restore": {
                "enabled": True,
                "include_transcript": True,
                "include_context": True,
                "include_events": True,
                "include_artifacts": True,
                "max_transcripts": 8,
                "max_messages": 24,
                "max_runtime_items": 12,
                "max_chars": 12000,
            },
            "delegation": {"policy": "NoopDelegationPolicy"},
        },
        "autonomous": {
            "profile": "autonomous",
            "limits": {"max_iterations": 200, "max_context_tokens": 200000},
            "features": {"enable_safety": True, "fallback": "local_summary"},
            "policies": {
                "context": "ManagedContextProtocol",
                "continuity": "HandoffContinuityPolicy",
                "harness": "SingleRunHarness",
                "quality": "CriteriaQualityGate",
                "delegation": "DepthLimitedDelegationPolicy",
                "governance": "DefaultGovernancePolicy",
                "feedback": "CollectingFeedbackPolicy",
                "skill_injection": "SkillInjectionPolicy",
                "session_restore": "SessionRestorePolicy",
            },
            "session_restore": {
                "enabled": True,
                "include_transcript": True,
                "include_context": True,
                "include_events": True,
                "include_artifacts": True,
                "max_transcripts": 8,
                "max_messages": 24,
                "max_runtime_items": 12,
                "max_chars": 12000,
            },
            "delegation": {"policy": "DepthLimitedDelegationPolicy", "max_depth": 3},
        },
    }


def test_runtime_context_limit_reaches_engine_config() -> None:
    from loom.providers.base import CompletionResponse, LLMProvider

    class MockProvider(LLMProvider):
        async def _complete_response(self, messages, params=None):
            return CompletionResponse(content="ok")

    agent = Agent(
        model=Model.openai("gpt-test"),
        runtime=Runtime.sdk(max_context_tokens=12345),
    )
    engine = agent._build_engine(MockProvider())

    assert engine.config.max_tokens == 12345
    assert engine.config.completion_max_tokens == 4096


def test_runtime_profile_presets_accept_overrides() -> None:
    quality = QualityGate.pass_fail()
    feedback = FeedbackPolicy.none()

    runtime = Runtime.long_running(
        max_context_tokens=64000,
        quality=quality,
        feedback=feedback,
        extensions={"tenant": "acme"},
    )

    assert runtime.limits.max_context_tokens == 64000
    assert runtime.quality is quality
    assert runtime.feedback is feedback
    assert runtime.extensions == {"profile": "long_running", "tenant": "acme"}


def test_agent_direct_constructor_is_primary_api():
    search = ToolSpec.from_function(lambda query: query, name="search", read_only=True)

    agent = Agent(
        model=Model.openai("gpt-test"),
        instructions="Direct constructor",
        generation=Generation(temperature=0.1, max_output_tokens=256),
        tools=[search],
        memory=True,
        runtime=Runtime(limits=RuntimeLimits(max_iterations=7)),
    )

    assert agent.config.model.identifier == "openai:gpt-test"
    assert agent.config.instructions == "Direct constructor"
    assert agent.config.generation.temperature == 0.1
    assert agent.config.generation.max_output_tokens == 256
    assert agent.config.tools[0].name == "search"
    assert agent.config.memory.enabled is True
    assert agent.config.runtime.limits.max_iterations == 7


def test_agent_direct_constructor_accepts_toolset():
    search = ToolSpec.from_function(lambda query: query, name="search", read_only=True)
    read_doc = ToolSpec.from_function(lambda path: path, name="read_doc", read_only=True)

    tools = Toolset.of(
        search,
        Toolset.of(read_doc, name="docs"),
        name="research",
        description="Research tools",
    )

    agent = Agent(
        model=Model.openai("gpt-test"),
        tools=tools,
    )

    assert tools.name == "research"
    assert len(tools) == 2
    assert [tool.name for tool in agent.config.tools] == ["search", "read_doc"]


def test_agent_direct_constructor_accepts_mixed_tool_entries():
    search = ToolSpec.from_function(lambda query: query, name="search", read_only=True)
    summarize = ToolSpec.from_function(lambda text: text, name="summarize", read_only=True)

    agent = Agent(
        model=Model.openai("gpt-test"),
        tools=[Toolset.of(search, name="research"), summarize],
    )

    assert [tool.name for tool in agent.config.tools] == ["search", "summarize"]


def test_builtin_toolset_factories_expose_ideal_user_api():
    files = Toolset.files()
    files_rw = Toolset.files(read_only=False)
    web = Toolset.web()
    shell = Toolset.shell()
    mcp = Toolset.mcp()

    assert [tool.name for tool in files] == ["Read", "Glob", "Grep"]
    assert [tool.name for tool in files_rw] == ["Read", "Glob", "Grep", "Write", "Edit"]
    assert all(tool.read_only for tool in files)
    assert [tool.name for tool in web] == ["WebFetch", "WebSearch"]
    assert [tool.name for tool in shell] == ["Bash"]
    assert shell.tools[0].read_only is False
    assert shell.tools[0].requires_permission is True
    assert [tool.name for tool in mcp] == ["ListMcpResources", "ReadMcpResource", "MCPTool"]


def test_capability_factories_expose_ideal_user_api():
    files = Capability.files()
    files_rw = Capability.files(read_only=False)
    web = Capability.web()
    shell = Capability.shell(require_approval=False)
    mcp = Capability.mcp("github", command="gh")
    skill = Capability.skill("repo-review", version="1")

    assert files.source == CapabilitySource.BUILTIN
    assert [tool.name for tool in files.to_tools()] == ["Read", "Glob", "Grep"]
    assert [tool.name for tool in files_rw.to_tools()] == ["Read", "Glob", "Grep", "Write", "Edit"]
    assert [tool.name for tool in web.to_tools()] == ["WebFetch", "WebSearch"]
    assert [tool.name for tool in shell.to_tools()] == ["Bash"]
    assert shell.to_tools()[0].requires_permission is False
    assert mcp.name == "mcp:github"
    assert mcp.metadata["server"] == "github"
    assert mcp.metadata["config"] == {"command": "gh"}
    assert [tool.name for tool in mcp.to_tools()] == [
        "ListMcpResources",
        "ReadMcpResource",
        "MCPTool",
    ]
    assert skill.source == CapabilitySource.SKILL
    assert skill.to_tools() == []


def test_agent_direct_constructor_accepts_capabilities():
    search = ToolSpec.from_function(lambda query: query, name="search", read_only=True)

    agent = Agent(
        model=Model.openai("gpt-test"),
        tools=[search],
        capabilities=[
            Capability.files(read_only=True),
            Capability.web(),
        ],
    )

    assert [capability.name for capability in agent.config.capabilities] == ["files", "web"]
    assert [tool.name for tool in agent.config.tools] == [
        "search",
        "Read",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
    ]


def test_agent_config_accepts_capabilities():
    agent = create_agent(
        AgentConfig(
            model=Model.openai("gpt-test"),
            capabilities=[Capability.files(read_only=True)],
        )
    )

    assert [capability.name for capability in agent.config.capabilities] == ["files"]
    assert [tool.name for tool in agent.config.tools] == ["Read", "Glob", "Grep"]


def test_capability_registry_compiles_registered_capabilities():
    registry = CapabilityRegistry([Capability.files()])
    registry.register(Capability.skill("repo-review"))

    assert registry.get("files") is not None
    assert [capability.name for capability in registry.list()] == ["files", "skill:repo-review"]
    assert [capability.name for capability in registry.list_capabilities()] == [
        "files",
        "skill:repo-review",
    ]
    assert [tool.name for tool in registry.compile_tools()] == ["Read", "Glob", "Grep"]


def test_mcp_capability_activates_explicit_server_into_runtime_engine():
    from loom.providers.base import LLMProvider

    class MockProvider(LLMProvider):
        async def _complete(self, prompt: str, **kwargs):
            return {"content": "ok"}

    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.mcp(
                "docs",
                instructions="Use docs carefully.",
                mock_tools=[
                    {
                        "name": "search_docs",
                        "description": "Search docs",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ],
                mock_resources=[{"uri": "file:///docs", "content": "docs body"}],
            )
        ],
    )

    engine = agent._build_engine(MockProvider())

    assert agent.ecosystem.mcp_bridge.servers["docs"].connected is True
    assert "Use docs carefully." in agent.ecosystem.get_system_prompt_additions()
    assert engine.tool_registry.get("mcp__docs__search_docs") is not None


def test_skill_capability_registers_explicit_skill_content():
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.skill(
                "repo-review",
                description="Review repository changes.",
                content="# Review\nCheck diffs and tests.",
                when_to_use="review,diff",
                allowed_tools=["Read", "Grep"],
            )
        ],
    )

    skill = agent.ecosystem.skill_registry.get("repo-review")

    assert skill is not None
    assert skill.description == "Review repository changes."
    assert skill.content == "# Review\nCheck diffs and tests."
    assert skill.when_to_use == "review,diff"
    assert skill.allowed_tools == ["Read", "Grep"]


def test_skill_capability_without_content_still_activates_declaration():
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[Capability.skill("repo-review")],
    )

    assert "skill:repo-review" in agent.ecosystem.capability_registry.active_capabilities
    assert agent.ecosystem.skill_registry.get("repo-review") is None


@pytest.mark.asyncio
async def test_agent_run_accepts_runtime_task():
    from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider

    class MockProvider(LLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.requests: list[CompletionRequest] = []

        async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
            self.requests.append(request)
            return CompletionResponse(content="task handled")

    agent = Agent(model=Model.openai("gpt-test"))
    provider = MockProvider()
    agent._provider = provider
    agent._provider_resolved = True

    result = await agent.run(
        RuntimeTask(
            goal="Summarize repository",
            input={"repo": "loom-agent"},
            criteria=["mention runtime language"],
            metadata={"source": "test"},
        )
    )

    assert result.output == "task handled"
    text = "\n".join(str(message["content"]) for message in provider.requests[0].messages)
    assert "Summarize repository" in text
    assert "repo: loom-agent" in text
    assert "mention runtime language" in text


def test_continuity_policy_handoff_wraps_context_renewal():
    from loom.context import ContextPartitions
    from loom.runtime import ContinuityPolicy

    partitions = ContextPartitions()
    partitions.working.goal_progress = "Implemented signal runtime"
    partitions.working.plan = ["abstract harness"]
    partitions.working.last_signal_ts = "2026-04-27T10:00:00"

    result = ContinuityPolicy.handoff().renew(
        partitions,
        RuntimeTask(goal="Refactor runtime language"),
        sprint=2,
    )

    assert result.context.working.goal_progress == "Implemented signal runtime"
    assert result.context.working.last_signal_ts == "2026-04-27T10:00:00"
    assert result.artifact.goal == "Refactor runtime language"
    assert result.artifact.sprint == 2
    assert result.artifact.open_tasks == ["abstract harness"]


@pytest.mark.asyncio
async def test_harness_single_run_uses_runtime_task_contract():
    from loom.runtime import Harness, HarnessContext

    class Runner:
        async def run(self, task: RuntimeTask):
            return type("Result", (), {"output": f"ran:{task.goal}"})()

    outcome = await Harness.single_run().run(
        RuntimeTask(goal="Build SDK abstraction"),
        HarnessContext(runner=Runner()),
    )

    assert outcome.output == "ran:Build SDK abstraction"
    assert outcome.passed is True


def test_runtime_signal_projects_into_dashboard():
    from loom.context.dashboard import DashboardManager
    from loom.runtime import SignalDecision

    dashboard = DashboardManager()
    signal = RuntimeSignal.create(
        "CPU usage exceeded 90%",
        source="heartbeat",
        type="alert",
        urgency="high",
        payload={"cpu_pct": 93},
    )
    decision = AttentionPolicy().decide(signal)

    dashboard.ingest_signal(signal, decision)

    state = dashboard.dashboard
    assert state.last_signal_ts == signal.observed_at.isoformat()
    assert state.last_hb_ts == signal.observed_at.isoformat()
    assert state.interrupt_requested is True
    assert state.event_surface.pending_events[0]["event_id"] == signal.id
    assert state.event_surface.pending_events[0]["summary"] == "CPU usage exceeded 90%"
    assert state.event_surface.recent_event_decisions[0]["action"] == "interrupt"
    assert isinstance(decision, SignalDecision)


@pytest.mark.asyncio
async def test_agent_signal_is_visible_to_next_run_context():
    from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider

    class MockProvider(LLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.requests: list[CompletionRequest] = []

        async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
            self.requests.append(request)
            return CompletionResponse(content="saw signal")

    agent = Agent(model=Model.openai("gpt-test"))
    provider = MockProvider()
    agent._provider = provider
    agent._provider_resolved = True

    decision = await agent.signal(
        "Daily summary job is due",
        source="cron",
        type="job",
        session_id="cron:daily-summary",
    )
    result = await agent.session(SessionConfig(id="cron:daily-summary")).run(
        "What should I handle next?"
    )

    assert decision.action == "run"
    assert result.output == "saw signal"
    assert provider.requests
    contents = [str(message["content"]) for message in provider.requests[0].messages]
    assert any("Daily summary job is due" in content for content in contents)


def test_agent_direct_constructor_accepts_model_string_and_memory_false():
    agent = Agent(model="anthropic:claude-sonnet-4", memory=False)

    assert agent.config.model.identifier == "anthropic:claude-sonnet-4"
    assert agent.config.memory is None


def test_agent_from_config_and_from_spec_keep_config_path():
    spec = AgentSpec(model=Model.openai("gpt-test"), instructions="Reusable")

    assert Agent.from_config(spec).config.instructions == "Reusable"
    assert Agent.from_spec(spec).config.model.identifier == "openai:gpt-test"


def test_agent_constructor_rejects_ambiguous_config_and_direct_fields():
    with pytest.raises(TypeError):
        Agent(
            config=AgentConfig(model=ModelRef.anthropic("claude-sonnet-4")),
            model=Model.openai("gpt-test"),
        )

    with pytest.raises(ValueError):
        Agent(model="missing-provider-separator")


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


@pytest.mark.asyncio
async def test_memory_provider_prefetch_and_sync_turn():
    from loom.providers.base import CompletionParams, CompletionResponse, LLMProvider

    class RecorderMemory(MemoryProvider):
        name = "recorder"

        def __init__(self) -> None:
            self.synced: list[tuple[str, str, str | None]] = []

        def system_prompt(self) -> str:
            return "Use recalled memory carefully."

        def prefetch(self, query: str, *, session_id: str | None = None) -> str:
            return f"recalled for {query} in {session_id}"

        def sync_turn(
            self,
            user_content: str,
            assistant_content: str,
            *,
            session_id: str | None = None,
        ) -> None:
            self.synced.append((user_content, assistant_content, session_id))

    class MockProvider(LLMProvider):
        async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
            return ""

        async def _complete_response(
            self,
            messages: list,
            params: CompletionParams | None = None,
        ) -> CompletionResponse:
            assert any(
                message["role"] == "system"
                and "Use recalled memory carefully." in str(message["content"])
                for message in messages
            )
            assert any(
                "recalled for remember me in memory-session" in str(message["content"])
                for message in messages
            )
            return CompletionResponse(content="remembered")

        def stream(self, messages: list, params: CompletionParams | None = None):
            async def _gen():
                yield "remembered"

            return _gen()

    memory = RecorderMemory()
    agent = Agent(
        model=Model.openai("gpt-test"),
        memory=MemoryConfig(providers=[memory]),
    )
    agent._provider = MockProvider()
    agent._provider_resolved = True

    result = await agent.session(SessionConfig(id="memory-session")).run("remember me")

    assert result.output == "remembered"
    assert memory.synced == [("remember me", "remembered", "memory-session")]


@pytest.mark.asyncio
async def test_memory_provider_errors_are_isolated(caplog):
    from loom.providers.base import CompletionParams, CompletionResponse, LLMProvider

    class BrokenMemory(MemoryProvider):
        name = "broken"

        def system_prompt(self) -> str:
            raise RuntimeError("system prompt failed")

        def prefetch(self, query: str, *, session_id: str | None = None) -> str:
            raise RuntimeError("prefetch failed")

        def sync_turn(
            self,
            user_content: str,
            assistant_content: str,
            *,
            session_id: str | None = None,
        ) -> None:
            raise RuntimeError("sync failed")

    class UnavailableMemory(MemoryProvider):
        name = "off"
        called = False

        def is_available(self) -> bool:
            return False

        def prefetch(self, query: str, *, session_id: str | None = None) -> str:
            self.called = True
            return "should not appear"

    class GoodMemory(MemoryProvider):
        name = "good"

        def __init__(self) -> None:
            self.synced: list[tuple[str, str, str | None]] = []

        def system_prompt(self) -> str:
            return "Use good memory."

        def prefetch(self, query: str, *, session_id: str | None = None) -> str:
            return f"good recall for {query} in {session_id}"

        def sync_turn(
            self,
            user_content: str,
            assistant_content: str,
            *,
            session_id: str | None = None,
        ) -> None:
            self.synced.append((user_content, assistant_content, session_id))

    class MockProvider(LLMProvider):
        async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
            return ""

        async def _complete_response(
            self,
            messages: list,
            params: CompletionParams | None = None,
        ) -> CompletionResponse:
            text = "\n".join(str(message["content"]) for message in messages)
            assert "Use good memory." in text
            assert "good recall for remember safely in safe-session" in text
            assert "should not appear" not in text
            return CompletionResponse(content="safe")

        def stream(self, messages: list, params: CompletionParams | None = None):
            async def _gen():
                yield "safe"

            return _gen()

    unavailable = UnavailableMemory()
    good = GoodMemory()
    agent = Agent(
        model=Model.openai("gpt-test"),
        memory=MemoryConfig(providers=[BrokenMemory(), unavailable, good]),
    )
    agent._provider = MockProvider()
    agent._provider_resolved = True

    caplog.set_level("WARNING")
    result = await agent.session(SessionConfig(id="safe-session")).run("remember safely")

    assert result.output == "safe"
    assert unavailable.called is False
    assert good.synced == [("remember safely", "safe", "safe-session")]
    assert "Memory provider broken failed during system_prompt" in caplog.text
    assert "Memory provider broken failed during prefetch" in caplog.text
    assert "Memory provider broken failed during sync_turn" in caplog.text


@pytest.mark.asyncio
async def test_session_store_records_session_and_run():
    from loom.providers.base import CompletionParams, CompletionResponse, LLMProvider

    class MockProvider(LLMProvider):
        async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
            return ""

        async def _complete_response(
            self,
            messages: list,
            params: CompletionParams | None = None,
        ) -> CompletionResponse:
            return CompletionResponse(content="stored")

        def stream(self, messages: list, params: CompletionParams | None = None):
            async def _gen():
                yield "stored"

            return _gen()

    store = InMemorySessionStore()
    agent = Agent(
        model=Model.openai("gpt-test"),
        session_store=store,
    )
    agent._provider = MockProvider()
    agent._provider_resolved = True

    session = agent.session(SessionConfig(id="stored-session", metadata={"tenant": "acme"}))
    result = await session.run("persist this")

    assert result.output == "stored"
    assert store.sessions["stored-session"].metadata["tenant"] == "acme"
    saved_run = store.runs[result.run_id]
    assert saved_run.session_id == "stored-session"
    assert saved_run.state == "completed"
    assert saved_run.output == "stored"
    assert store.load_run(result.run_id) is saved_run
    assert store.list_runs("stored-session") == [saved_run]


@pytest.mark.asyncio
async def test_file_session_store_persists_sessions_and_runs(tmp_path):
    from loom.providers.base import CompletionParams, CompletionResponse, LLMProvider

    class MockProvider(LLMProvider):
        async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
            return ""

        async def _complete_response(
            self,
            messages: list,
            params: CompletionParams | None = None,
        ) -> CompletionResponse:
            return CompletionResponse(content="stored on disk")

        def stream(self, messages: list, params: CompletionParams | None = None):
            async def _gen():
                yield "stored on disk"

            return _gen()

    path = tmp_path / "sessions.json"
    store = FileSessionStore(path)
    agent = Agent(
        model=Model.openai("gpt-test"),
        session_store=store,
    )
    agent._provider = MockProvider()
    agent._provider_resolved = True

    result = await agent.session(
        SessionConfig(id="disk-session", metadata={"tenant": "acme"}),
    ).run("persist this")

    reloaded = FileSessionStore(path)
    session_record = reloaded.load_session("disk-session")

    assert result.output == "stored on disk"
    assert session_record is not None
    assert session_record.metadata["tenant"] == "acme"
    saved_run = reloaded.load_run(result.run_id)
    assert saved_run is not None
    assert saved_run.session_id == "disk-session"
    assert saved_run.output == "stored on disk"
    assert reloaded.list_runs("disk-session") == [saved_run]
    transcript = reloaded.load_transcript(result.run_id)
    assert transcript is not None
    assert transcript.prompt == "persist this"
    assert transcript.output == "stored on disk"
    assert transcript.messages == [
        {"role": "user", "content": "persist this"},
        {"role": "assistant", "content": "stored on disk"},
    ]
    assert reloaded.list_transcripts("disk-session") == [transcript]

    reloaded.delete_session("disk-session")
    assert reloaded.load_session("disk-session") is None
    assert reloaded.load_run(result.run_id) is None
    assert reloaded.load_transcript(result.run_id) is None


@pytest.mark.asyncio
async def test_session_store_restores_transcript_into_reopened_session():
    from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider

    class MockProvider(LLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.requests: list[CompletionRequest] = []

        async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
            self.requests.append(request)
            return CompletionResponse(content="second answer")

    store = InMemorySessionStore()
    store.save_transcript(
        TranscriptRecord(
            id="run-1",
            session_id="restore-session",
            prompt="first question",
            output="first answer",
            messages=[
                {"role": "user", "content": "first question"},
                {"role": "assistant", "content": "first answer"},
            ],
        )
    )
    agent = Agent(model=Model.openai("gpt-test"), session_store=store)
    provider = MockProvider()
    agent._provider = provider
    agent._provider_resolved = True

    result = await agent.session(SessionConfig(id="restore-session")).run("second question")

    assert result.output == "second answer"
    contents = [message["content"] for message in provider.requests[0].messages]
    assert contents[-3:] == ["first question", "first answer", "second question"]
    assert store.load_transcript(result.run_id) is not None


@pytest.mark.asyncio
async def test_session_restore_policy_restores_runtime_view_with_budget():
    from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider
    from loom.runtime import SessionRestorePolicy

    class MockProvider(LLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.requests: list[CompletionRequest] = []

        async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
            self.requests.append(request)
            return CompletionResponse(content="runtime restored")

    store = InMemorySessionStore()
    store.save_transcript(
        TranscriptRecord(
            id="run-1",
            session_id="restore-runtime",
            prompt="first task",
            output="first answer",
            messages=[
                {"role": "user", "content": "first task"},
                {"role": "assistant", "content": "first answer"},
            ],
            context={"ticket": "LOOM-1", "notes": "restore this context"},
            events=[
                {
                    "type": "signal.received",
                    "payload": {"summary": "cron fired", "urgency": "high"},
                },
                {
                    "type": "tools.executed",
                    "payload": {"tool_name": "mcp__docs__search_docs", "count": 1},
                },
            ],
            artifacts=[
                {
                    "kind": "text",
                    "title": "Search Result",
                    "uri": "run://run-1/output",
                    "metadata": {"content": "docs say runtime restore works"},
                }
            ],
        )
    )
    agent = Agent(
        model=Model.openai("gpt-test"),
        runtime=Runtime(session_restore=SessionRestorePolicy.window(max_chars=900)),
        session_store=store,
    )
    provider = MockProvider()
    agent._provider = provider
    agent._provider_resolved = True

    result = await agent.session(SessionConfig(id="restore-runtime")).run("continue")

    assert result.output == "runtime restored"
    rendered = "\n".join(str(message["content"]) for message in provider.requests[0].messages)
    assert "first task" in rendered
    assert "first answer" in rendered
    assert "Restored Runtime State" in rendered
    assert "signal.received" in rendered
    assert "cron fired" in rendered
    assert "mcp__docs__search_docs" in rendered
    assert "Search Result" in rendered
    assert len(rendered) < 1400


@pytest.mark.asyncio
async def test_session_restore_policy_limits_restored_transcript_window():
    from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider
    from loom.runtime import SessionRestorePolicy

    class MockProvider(LLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.requests: list[CompletionRequest] = []

        async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
            self.requests.append(request)
            return CompletionResponse(content="windowed")

    store = InMemorySessionStore()
    for index in range(4):
        store.save_transcript(
            TranscriptRecord(
                id=f"run-{index}",
                session_id="windowed-session",
                prompt=f"question {index}",
                output=f"answer {index}",
                messages=[
                    {"role": "user", "content": f"question {index}"},
                    {"role": "assistant", "content": f"answer {index}"},
                ],
            )
        )
    agent = Agent(
        model=Model.openai("gpt-test"),
        runtime=Runtime(
            session_restore=SessionRestorePolicy.transcript_only(
                max_transcripts=2,
                max_messages=4,
            )
        ),
        session_store=store,
    )
    provider = MockProvider()
    agent._provider = provider
    agent._provider_resolved = True

    await agent.session(SessionConfig(id="windowed-session")).run("latest")

    rendered = [str(message["content"]) for message in provider.requests[0].messages]
    assert "question 0" not in rendered
    assert "answer 1" not in rendered
    assert "question 2" in rendered
    assert "answer 3" in rendered
    assert rendered[-1] == "latest"


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
    assert "AgentSpec" in exported
    assert "ModelRef" in exported
    assert "Model" in exported
    assert "RuntimeConfig" in exported
    assert "Runtime" in exported
    assert "MemoryProvider" in exported
    assert "Toolset" in exported
    assert "KnowledgeSource" in exported
    assert "SessionConfig" not in exported
    assert "RunContext" not in exported


def test_new_configuration_aliases_preserve_existing_contracts():
    assert AgentSpec is AgentConfig
    assert Model is ModelRef
    assert Generation is GenerationConfig
    assert Memory is MemoryConfig
    assert Runtime is RuntimeConfig
    assert Toolset is ConfigToolset
    assert loom_config.Toolset is ConfigToolset
    assert issubclass(InMemorySessionStore, SessionStore)
    assert issubclass(FileSessionStore, SessionStore)
    assert Model.openai("gpt-test").identifier == "openai:gpt-test"
    assert QualityContract(goal="g", criteria=["c"]).criteria == ["c"]
    assert QualityResult(passed=True).passed is True
    assert Runtime(quality=QualityGate.pass_fail()).quality is not None
    assert Runtime(feedback=FeedbackPolicy.none()).feedback is not None


def test_legacy_compat_surface_has_removal_window():
    from loom import __version__
    from loom.compat import (
        LEGACY_PUBLIC_API_COMPAT_UNTIL,
        LEGACY_PUBLIC_API_REMOVAL_VERSION,
    )
    from loom.compat.v0 import AgentConfig as LegacyAgentConfig
    from loom.compat.v0 import ModelRef as LegacyModelRef

    assert __version__ == "0.8.0"
    assert LEGACY_PUBLIC_API_COMPAT_UNTIL == "0.8.x"
    assert LEGACY_PUBLIC_API_REMOVAL_VERSION == "0.9.0"
    assert LegacyAgentConfig is AgentConfig
    assert LegacyModelRef is ModelRef


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
                    interrupt_policy=HeartbeatInterruptPolicy(
                        low="queue", high="request", critical="force"
                    ),
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
    from loom.providers.base import (
        CompletionParams,
        CompletionRequest,
        CompletionResponse,
        LLMProvider,
    )
    from loom.types import ToolCall

    @tool(description="Add two integers", read_only=True)
    def add(a: int, b: int) -> str:
        return str(a + b)

    class MockProvider(LLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0
            self.requests: list[CompletionRequest] = []

        async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
            return ""

        async def _complete_response(
            self,
            messages: list,
            params: CompletionParams | None = None,
        ) -> CompletionResponse:
            raise AssertionError("engine should use complete_request")

        async def complete_request(self, request: CompletionRequest) -> CompletionResponse:
            self.requests.append(request)
            messages = request.messages
            params = request.params
            self.calls += 1
            if self.calls == 1:
                assert params is not None
                assert params.tools[0]["name"] == "add"
                assert request.tools[0].name == "add"
                assert [parameter.name for parameter in request.tools[0].parameters] == ["a", "b"]
                assert request.metadata["tool_count"] == 1
                assert request.metadata["iteration"] == 1
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
    lifecycle_events: list[str] = []
    tool_events: list[dict] = []

    def track_lifecycle(**payload):
        lifecycle_events.append(payload["event_name"])

    def track_tool(**payload):
        tool_events.append(payload)

    agent.on("before_run", track_lifecycle)
    agent.on("after_run", track_lifecycle)
    agent.on("tool_result", track_tool)

    result = await agent.run("What is 2 + 3?")

    assert result.state == RunState.COMPLETED
    assert result.output == "The answer is 5."
    assert any(event.type == "tools.requested" for event in result.events)
    assert any(event.type == "tools.executed" for event in result.events)
    assert lifecycle_events == ["before_run", "after_run"]
    assert tool_events[0]["tool_name"] == "add"
    assert tool_events[0]["success"] is True
    assert tool_events[0]["result"] == "5"
    assert len(agent._provider.requests) == 2


@pytest.mark.asyncio
async def test_agent_runtime_exposes_semantic_hooks():
    from loom.providers.base import (
        CompletionRequest,
        CompletionResponse,
        LLMProvider,
    )
    from loom.types import ToolCall

    @tool(description="Echo text", read_only=True)
    def echo(text: str) -> str:
        return text

    class MockProvider(LLMProvider):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
            self.calls += 1
            if self.calls == 1:
                return CompletionResponse(
                    tool_calls=[ToolCall(id="call_echo_1", name="echo", arguments={"text": "ok"})]
                )
            return CompletionResponse(content="done")

    agent = Agent(model=Model.openai("gpt-test"), tools=[echo])
    agent._provider = MockProvider()
    agent._provider_resolved = True
    events: list[str] = []
    payloads: list[dict] = []

    def track(**payload):
        events.append(payload["event_name"])
        payloads.append(payload)

    agent.on("before_llm", track)
    agent.on("after_llm", track)
    agent.on("before_tool", track)
    agent.on("after_tool", track)

    result = await agent.run("use echo")

    assert result.output == "done"
    assert events == [
        "before_llm",
        "after_llm",
        "before_tool",
        "after_tool",
        "before_llm",
        "after_llm",
    ]
    assert payloads[0]["request"].metadata["iteration"] == 1
    assert payloads[2]["tool_name"] == "echo"
    assert payloads[3]["success"] is True


@pytest.mark.asyncio
async def test_provider_health_check_failure_triggers_fallback_error():
    from loom.providers.base import CompletionParams, CompletionResponse, LLMProvider

    class MockProvider(LLMProvider):
        async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
            return ""

        async def _complete_response(
            self,
            messages: list,
            params: CompletionParams | None = None,
        ) -> CompletionResponse:
            if params is not None and params.max_tokens == 1:
                raise RuntimeError("provider ping failed")
            return CompletionResponse(content="ok")

        def stream(self, messages: list, params: CompletionParams | None = None):
            async def _gen():
                yield "ok"

            return _gen()

    with patch("loom.agent._resolve_provider", return_value=MockProvider()):
        agent = create_agent(
            AgentConfig(
                model=ModelRef.openai("gpt-test"),
                runtime=RuntimeConfig(
                    features=RuntimeFeatures(
                        fallback=RuntimeFallback(mode=RuntimeFallbackMode.ERROR),
                    ),
                ),
            )
        )
        result = await agent.run("check health")

    assert result.state == RunState.FAILED
    assert any(event.type == "run.failed.provider_unavailable" for event in result.events)


@pytest.mark.asyncio
async def test_provider_health_check_can_be_disabled_via_runtime_extensions():
    from loom.providers.base import CompletionParams, CompletionResponse, LLMProvider

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
            return CompletionResponse(content="provider smoke test ok")

        def stream(self, messages: list, params: CompletionParams | None = None):
            async def _gen():
                yield "provider smoke test ok"

            return _gen()

    provider = MockProvider()
    with patch("loom.agent._resolve_provider", return_value=provider):
        agent = create_agent(
            AgentConfig(
                model=ModelRef.openai("gpt-test"),
                runtime=RuntimeConfig(
                    extensions={"provider_health_check": False},
                ),
            )
        )
        result = await agent.run("check health toggle")

    assert result.state == RunState.COMPLETED
    assert provider.calls == 1


def test_runtime_compression_policy_is_propagated_to_engine():
    from loom.providers.base import CompletionParams, LLMProvider

    class MockProvider(LLMProvider):
        async def _complete(self, messages: list, params: CompletionParams | None = None) -> str:
            return "ok"

        def stream(self, messages: list, params: CompletionParams | None = None):
            async def _gen():
                yield "ok"

            return _gen()

    agent = create_agent(
        AgentConfig(
            model=ModelRef.openai("gpt-test"),
            runtime=RuntimeConfig(
                extensions={
                    "compression_policy": {
                        "snip_at": 0.61,
                        "micro_at": 0.72,
                        "collapse_at": 0.86,
                        "auto_compact_at": 0.97,
                    }
                },
            ),
        )
    )

    engine = agent._build_engine(MockProvider())

    policy = engine.context_manager.compressor.policy
    assert policy.snip_at == 0.61
    assert policy.micro_at == 0.72
    assert policy.collapse_at == 0.86
    assert policy.auto_compact_at == 0.97
