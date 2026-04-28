from __future__ import annotations

import time
from datetime import datetime, timedelta

import pytest

from loom import (
    Agent,
    Harness,
    HarnessCandidate,
    HarnessOutcome,
    HarnessRequest,
    KnowledgeDocument,
    KnowledgeQuery,
    KnowledgeResolver,
    KnowledgeSource,
    MemoryConfig,
    MemoryExtractor,
    MemoryQuery,
    MemoryRecord,
    MemoryResolver,
    MemorySource,
    MemoryStore,
    Model,
    OrchestrationConfig,
    Runtime,
    RuntimeSignal,
    ScheduleConfig,
    ScheduledJob,
    SessionConfig,
    SignalDecision,
)
from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider
from loom.runtime import JobRegistry, ScheduleTicker


class MockProvider(LLMProvider):
    async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(content="ok")


@pytest.mark.asyncio
async def test_custom_harness_can_select_from_possibilities() -> None:
    async def choose_candidate(request: HarnessRequest) -> HarnessOutcome:
        baseline = await request.run_once()
        candidates = [
            HarnessCandidate(
                id="baseline",
                content=str(baseline["output"]),
                score=0.4,
                rationale="raw runtime output",
            ),
            HarnessCandidate(
                id="expanded",
                content=f"{baseline['output']} with harness strategy",
                score=0.9,
                rationale="custom strategy preferred the richer candidate",
            ),
        ]
        return HarnessOutcome(
            output=candidates[1].content,
            iterations=int(baseline["iterations"]) + 1,
            candidates=candidates,
            selected_candidate_id="expanded",
        )

    agent = Agent(
        model=Model.openai("gpt-test"),
        runtime=Runtime.sdk(harness=Harness.custom(choose_candidate, name="possibility")),
    )
    agent._provider = MockProvider()
    agent._provider_resolved = True

    result = await agent.run("choose")

    assert result.output == "ok with harness strategy"
    harness_events = [event for event in result.events if event.type == "harness.completed"]
    assert harness_events[0].payload["harness"] == "possibility"
    assert harness_events[0].payload["candidates"] == 2


def test_agent_orchestration_true_sets_depth_limited_delegation() -> None:
    agent = Agent(model=Model.openai("gpt-test"), orchestration=True)

    assert agent.config.runtime.extensions["profile"] == "orchestrated"
    assert agent.config.runtime.delegation.max_depth == 3


def test_orchestration_config_max_depth_propagates_and_binds_delegate() -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        orchestration=OrchestrationConfig(max_depth=5),
    )

    engine = agent._build_engine(MockProvider())

    delegation = engine.config.delegation_policy
    assert delegation.max_depth == 5
    assert type(delegation.delegate_policy).__name__ == "SubAgentDelegationPolicy"


def test_runtime_orchestrated_returns_valid_config() -> None:
    runtime = Runtime.orchestrated(max_depth=4, planner=False, gen_eval=False)

    assert runtime.describe()["profile"] == "orchestrated"
    assert runtime.describe()["delegation"] == {
        "policy": "DepthLimitedDelegationPolicy",
        "max_depth": 4,
    }
    assert runtime.extensions["orchestration"]["planner"] is False


def test_agent_orchestration_and_runtime_conflict_raises() -> None:
    with pytest.raises(TypeError):
        Agent(
            model=Model.openai("gpt-test"),
            runtime=Runtime.sdk(),
            orchestration=True,
        )


def test_inject_knowledge_writes_to_surface_not_memory() -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        knowledge=[KnowledgeSource.inline("repo", ["Loom has dashboard knowledge."])],
    )
    engine = agent._build_engine(MockProvider())

    engine._inject_knowledge("dashboard", None)

    surface = engine.context_manager.dashboard.dashboard.knowledge_surface
    assert surface.evidence_packs[0]["content"] == "Loom has dashboard knowledge."
    assert not any(
        "Knowledge:" in message.content for message in engine.context_manager.partitions.memory
    )


def test_dashboard_renders_evidence_content() -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        knowledge=[KnowledgeSource.inline("repo", ["Rendered evidence"])],
    )
    engine = agent._build_engine(MockProvider())

    engine._inject_knowledge("render", None)
    content = engine.context_manager.partitions._format_dashboard().content

    assert "## Knowledge Evidence" in content
    assert "Rendered evidence" in content


def test_knowledge_surface_deduplicates_and_evicts_overflow() -> None:
    agent = Agent(model=Model.openai("gpt-test"))
    engine = agent._build_engine(MockProvider())
    dashboard = engine.context_manager.dashboard

    dashboard.add_evidence({"source": "s", "title": "t", "content": "same", "score": 0.1})
    dashboard.add_evidence({"source": "s", "title": "t", "content": "same", "score": 0.9})
    assert len(dashboard.dashboard.knowledge_surface.evidence_packs) == 1

    for index in range(12):
        dashboard.add_evidence(
            {
                "source": "s",
                "title": str(index),
                "content": str(index),
                "score": float(index),
            }
        )
    engine._evict_knowledge_overflow()

    packs = dashboard.dashboard.knowledge_surface.evidence_packs
    assert len(packs) == 10
    assert min(pack.get("score") or 0 for pack in packs) >= 2.0


def test_agent_knowledge_bridge_and_retrieve_tool() -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        knowledge=[KnowledgeSource.inline("repo", ["Bridge me"])],
    )

    engine = agent._build_engine(MockProvider())

    assert [source.name for source in engine.context_manager._knowledge_sources] == ["repo"]
    assert engine.tool_registry.get("retrieve_knowledge") is not None


def test_retrieve_knowledge_absent_without_knowledge() -> None:
    agent = Agent(model=Model.openai("gpt-test"))
    engine = agent._build_engine(MockProvider())

    assert engine.tool_registry.get("retrieve_knowledge") is None


def test_memory_source_custom_resolver_and_extractor_are_runtime_providers() -> None:
    class RecordingStore(MemoryStore):
        def __init__(self) -> None:
            self.records: list[MemoryRecord] = []

        def search(self, query: MemoryQuery) -> list[MemoryRecord]:
            return [
                MemoryRecord(
                    content=f"remembered {query.text} in {query.session_id}",
                    key="hit-1",
                    score=0.9,
                )
            ]

        def upsert(self, record: MemoryRecord, query: MemoryQuery | None = None) -> None:
            self.records.append(record)

    store = RecordingStore()
    source = MemorySource.long_term(
        "project",
        store=store,
        extractor=MemoryExtractor.callable(
            lambda user, assistant, session_id=None: [
                MemoryRecord(
                    content=f"{user} -> {assistant}",
                    metadata={"session_id": session_id},
                )
            ]
        ),
        instructions="Prefer durable project memory.",
    )

    agent = Agent(model=Model.openai("gpt-test"), memory=MemoryConfig(sources=[source]))
    engine = agent._build_engine(MockProvider())

    assert engine.memory_providers == [source]
    assert source.system_prompt() == "Prefer durable project memory."
    assert source.prefetch("deploy", session_id="s1") == "remembered deploy in s1"

    source.sync_turn("user", "assistant", session_id="s1")

    assert store.records == [
        MemoryRecord(content="user -> assistant", metadata={"session_id": "s1"})
    ]


def test_memory_resolver_callable_validates_records() -> None:
    resolver = MemoryResolver.callable(lambda query: [MemoryRecord(content=query.text, key="k")])

    result = resolver.retrieve(MemoryQuery(text="needle", top_k=1))

    assert result.records[0].content == "needle"
    assert result.records[0].key == "k"


@pytest.mark.asyncio
async def test_memory_source_runs_through_agent_memory_lifecycle() -> None:
    class RecordingStore(MemoryStore):
        def __init__(self) -> None:
            self.records: list[MemoryRecord] = []

        def search(self, query: MemoryQuery) -> list[MemoryRecord]:
            return [MemoryRecord(content=f"source recalled {query.text}")]

        def upsert(self, record: MemoryRecord, query: MemoryQuery | None = None) -> None:
            self.records.append(record)

    class MemoryAwareProvider(LLMProvider):
        async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
            rendered = "\n".join(str(message["content"]) for message in request.messages)
            assert "source recalled remember this" in rendered
            return CompletionResponse(content="stored answer")

    store = RecordingStore()
    source = MemorySource.long_term(
        "project",
        store=store,
        extractor=MemoryExtractor.callable(
            lambda user, assistant, session_id=None: [
                MemoryRecord(content=f"extracted {user} -> {assistant}")
            ]
        ),
    )
    agent = Agent(
        model=Model.openai("gpt-test"),
        memory=MemoryConfig(sources=[source]),
    )
    agent._provider = MemoryAwareProvider()
    agent._provider_resolved = True

    result = await agent.session(SessionConfig(id="memory-source")).run("remember this")

    assert result.output == "stored answer"
    assert store.records == [MemoryRecord(content="extracted remember this -> stored answer")]


def test_knowledge_resolver_factories(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "intro.md").write_text("Directory evidence", encoding="utf-8")

    static_source = KnowledgeSource.dynamic(
        "static",
        KnowledgeResolver.static([KnowledgeDocument(content="Static evidence")]),
    )
    directory_source = KnowledgeSource.from_directory("docs", docs)

    assert static_source.resolve(KnowledgeQuery(text="x", top_k=1)).items[0].source_name == "static"
    assert (
        directory_source.resolve(KnowledgeQuery(text="x", top_k=1)).items[0].content
        == "Directory evidence"
    )


def test_schedule_config_interval_and_once() -> None:
    now = datetime.now()
    interval = ScheduleConfig.interval(minutes=30)
    once = ScheduleConfig.once(now)

    assert interval.compute_next_run(now) == now + timedelta(minutes=30)
    assert once.compute_next_run(None) == now
    assert once.compute_next_run(now) is None


def test_job_registry_and_repeat_limit() -> None:
    registry = JobRegistry()
    job = ScheduledJob(
        id="daily",
        prompt="Summarize",
        schedule=ScheduleConfig.once(datetime.now() - timedelta(seconds=1)),
        repeat=1,
    )

    registry.add(job)
    assert registry.get_due() == [job]
    registry.mark_ran("daily", success=True)

    assert job.enabled is False
    assert job.completed == 1


def test_schedule_ticker_dispatches_due_job() -> None:
    registry = JobRegistry()
    job = ScheduledJob(
        id="now",
        prompt="Run",
        schedule=ScheduleConfig.once(datetime.now() - timedelta(seconds=1)),
        repeat=1,
    )
    registry.add(job)
    dispatched: list[str] = []
    ticker = ScheduleTicker(registry, interval_seconds=0.01)

    try:
        ticker.start(lambda due: dispatched.append(due.id))
        time.sleep(0.05)
    finally:
        ticker.stop()

    assert dispatched == ["now"]


def test_agent_schedule_param_does_not_auto_start() -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        schedule=[
            ScheduledJob(
                id="check",
                prompt="Check",
                schedule=ScheduleConfig.interval(minutes=30),
            )
        ],
    )

    assert agent.config.schedule[0].id == "check"
    assert agent._schedule_ticker is None


def test_agent_schedule_shortcuts_append_jobs() -> None:
    agent = Agent(model=Model.openai("gpt-test"))
    interval_job = agent.every(
        id="check",
        prompt="Check CI",
        minutes=30,
        name="CI check",
        repeat=2,
        metadata={"scope": "ci"},
    )
    once_at = datetime.now() + timedelta(minutes=5)
    once_job = agent.once(once_at, id="daily", prompt="Summarize inbox")
    explicit_job = agent.schedule(
        "cron",
        prompt="Run cron-like check",
        every=ScheduleConfig.interval(hours=1),
    )

    assert [job.id for job in agent.config.schedule] == ["check", "daily", "cron"]
    assert interval_job.schedule.interval_minutes == 30
    assert interval_job.name == "CI check"
    assert interval_job.repeat == 2
    assert interval_job.metadata == {"scope": "ci"}
    assert once_job.schedule.run_at == once_at.isoformat()
    assert explicit_job.prompt == "Run cron-like check"


def test_start_scheduler_requires_jobs() -> None:
    agent = Agent(model=Model.openai("gpt-test"))

    with pytest.raises(ValueError, match="requires at least one scheduled job"):
        agent.start_scheduler()


def test_agent_start_scheduler_runs_due_job(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        schedule=[
            ScheduledJob(
                id="now",
                prompt="Run scheduled prompt",
                schedule=ScheduleConfig.once(datetime.now() - timedelta(seconds=1)),
                repeat=1,
            )
        ],
    )
    prompts: list[str] = []
    signals: list[RuntimeSignal] = []

    class FakeSession:
        async def signal(self, signal: RuntimeSignal) -> SignalDecision:
            signals.append(signal)
            return SignalDecision(action="run", reason="test")

        async def run(self, prompt: str) -> None:
            prompts.append(prompt)

    monkeypatch.setattr(agent, "session", lambda *args, **kwargs: FakeSession())

    try:
        agent.start_scheduler(interval_seconds=0.01)
        deadline = time.time() + 1
        while not prompts and time.time() < deadline:
            time.sleep(0.01)
    finally:
        agent.stop_scheduler()

    assert prompts == ["Run scheduled prompt"]
    assert len(signals) == 1
    signal = signals[0]
    assert signal.source == "cron"
    assert signal.type == "scheduled_job"
    assert signal.session_id == "scheduled:now"


def test_agent_scheduler_respects_non_run_signal_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = Agent(
        model=Model.openai("gpt-test"),
        schedule=[],
    )
    job = ScheduledJob(
        id="observe-only",
        prompt="Do not run",
        schedule=ScheduleConfig.once(datetime.now() - timedelta(seconds=1)),
    )
    prompts: list[str] = []
    signals: list[RuntimeSignal] = []

    class FakeSession:
        async def signal(self, signal: RuntimeSignal) -> SignalDecision:
            signals.append(signal)
            return SignalDecision(action="observe", reason="test")

        async def run(self, prompt: str) -> None:
            prompts.append(prompt)

    monkeypatch.setattr(agent, "session", lambda *args, **kwargs: FakeSession())

    agent._dispatch_scheduled_job(job)

    assert signals
    assert prompts == []
