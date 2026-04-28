"""17 - Runtime Kernel Platform.

A compact application-style demo showing how the runtime kernel coordinates
the seven primary mechanisms introduced by the public 0.8.1 API:

1. Tool use
2. Memory
3. Skills
4. Harness
5. Gateway/orchestration
6. Knowledge
7. Cron

The demo loads provider keys from `.env` when present. Without a provider key,
Loom falls back to its local summary path, so the composition remains runnable.

Run:
    python examples/17_runtime_kernel_platform.py

Optional:
    LOOM_DEMO_RUN_CRON=1 python examples/17_runtime_kernel_platform.py
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from loom import (
    Agent,
    Capability,
    Generation,
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
    RunContext,
    Runtime,
    RuntimeTask,
    ScheduleConfig,
    ScheduledJob,
    SessionConfig,
    SignalAdapter,
    SkillInjection,
    tool,
)
from loom.config import KnowledgeEvidence, KnowledgeEvidenceItem


def load_dotenv(path: str | Path = ".env") -> None:
    """Small `.env` loader for examples without adding a dependency."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def resolve_model():
    provider = os.getenv("LOOM_PROVIDER")
    if provider is None:
        if os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            provider = "gemini"
        elif os.getenv("DASHSCOPE_API_KEY"):
            provider = "qwen"
        else:
            provider = "openai"

    provider = provider.lower()
    model_name = os.getenv("LOOM_MODEL_NAME")
    if provider == "anthropic":
        return Model.anthropic(model_name or "claude-sonnet-4")
    if provider == "gemini":
        return Model.gemini(model_name or "gemini-2.5-pro")
    if provider == "qwen":
        return Model.qwen(model_name or "qwen-max")
    if provider == "ollama":
        return Model.ollama(model_name or "llama3", api_base=os.getenv("OLLAMA_BASE_URL"))
    return Model.openai(
        model_name or os.getenv("OPENAI_MODEL") or "gpt-4o",
        api_base=os.getenv("OPENAI_BASE_URL"),
        api_key_env="OPENAI_API_KEY",
    )


@dataclass
class InMemoryPreferenceStore(MemoryStore):
    """Tiny custom memory store used to demonstrate the MemoryStore boundary."""

    records: dict[str, MemoryRecord] = field(default_factory=dict)

    def search(self, query: MemoryQuery) -> list[MemoryRecord]:
        query_terms = Counter(query.text.lower().split())
        ranked: list[MemoryRecord] = []
        for record in self.records.values():
            record_terms = Counter(record.content.lower().split())
            overlap = sum((query_terms & record_terms).values())
            ranked.append(
                MemoryRecord(
                    key=record.key,
                    content=record.content,
                    score=float(overlap),
                    metadata=dict(record.metadata),
                )
            )
        ranked.sort(key=lambda item: item.score or 0.0, reverse=True)
        return ranked[: query.top_k]

    def upsert(self, record: MemoryRecord, query: MemoryQuery | None = None) -> None:
        key = record.key or hashlib.sha1(record.content.encode("utf-8")).hexdigest()[:12]
        metadata = dict(record.metadata)
        if query is not None and query.session_id:
            metadata.setdefault("session_id", query.session_id)
        self.records[key] = MemoryRecord(
            key=key,
            content=record.content,
            score=record.score,
            metadata=metadata,
        )


def extract_memory(
    user_content: str,
    assistant_content: str,
    *,
    session_id: str | None = None,
) -> list[MemoryRecord]:
    """Extract durable preferences from completed turns."""
    _ = assistant_content, session_id
    marker = "remember:"
    lowered = user_content.lower()
    if marker not in lowered:
        return []
    start = lowered.index(marker) + len(marker)
    content = user_content[start:].strip()
    return [MemoryRecord(content=content, metadata={"kind": "explicit_preference"})] if content else []


def build_knowledge_source() -> KnowledgeSource:
    """Show both fixed documents and a user-defined resolver."""

    def resolve_runbook(query: KnowledgeQuery) -> KnowledgeEvidence:
        source_name = query.source_names[0] if query.source_names else "ops-runbook"
        text = query.text.lower()
        items: list[KnowledgeEvidenceItem] = []
        if "incident" in text or "deploy" in text or "platform" in text:
            items.append(
                KnowledgeEvidenceItem(
                    source_name=source_name,
                    title="Incident Platform Runbook",
                    content=(
                        "For production incidents: assess blast radius, check service health, "
                        "prepare a rollback path, and require release-owner approval before "
                        "executing production changes."
                    ),
                    uri="runbook://incident-platform",
                    score=0.96,
                )
            )
        return KnowledgeEvidence(query=query, items=items, relevance_score=0.96 if items else 0.0)

    return KnowledgeSource.dynamic(
        "ops-runbook",
        KnowledgeResolver.callable(resolve_runbook, description="Runtime ops runbook resolver"),
        description="Dynamic operational knowledge",
    )


@tool(description="Read a service health snapshot", read_only=True)
async def lookup_service_status(service: str) -> str:
    samples = {
        "checkout": "checkout is degraded: p95 latency is 2.4s and error rate is 3.1%",
        "payments": "payments is healthy: p95 latency is 180ms and error rate is 0.02%",
    }
    return samples.get(service, f"{service} status is unknown")


@tool(description="Draft a bounded change plan", read_only=True)
async def create_change_plan(service: str, risk: str) -> str:
    return (
        f"Change plan for {service}: run canary, watch {risk}, keep rollback ready, "
        "and request release-owner approval before production execution."
    )


async def bounded_harness(request: HarnessRequest) -> HarnessOutcome:
    """A user-defined harness that can call the underlying runtime once."""
    result = await request.run_once()
    output = result.get("output", str(result)) if isinstance(result, dict) else str(result)
    candidate = HarnessCandidate(
        id="single-runtime-pass",
        content=output,
        score=1.0,
        rationale="Selected the bounded runtime pass for this demo.",
    )
    return HarnessOutcome(
        output=output,
        passed=True,
        iterations=int(result.get("iterations", 1)) if isinstance(result, dict) else 1,
        candidates=[candidate],
        selected_candidate_id=candidate.id,
        metadata={"harness": "bounded_harness", "session_id": request.session_id},
    )


def build_agent(memory_store: InMemoryPreferenceStore) -> Agent:
    memory_store.upsert(
        MemoryRecord(
            key="deploy-style",
            content="The platform team prefers canary deploys with explicit rollback notes.",
        )
    )
    memory = MemoryConfig(
        sources=[
            MemorySource.long_term(
                "team-preferences",
                resolver=MemoryResolver.from_store(memory_store),
                extractor=MemoryExtractor.callable(extract_memory),
                store=memory_store,
                instructions="Use recalled team preferences when planning operational work.",
                top_k=3,
            )
        ]
    )

    runtime = Runtime.orchestrated(
        max_depth=2,
        planner=True,
        max_iterations=24,
        harness=Harness.custom(bounded_harness, name="bounded_harness"),
        skill_injection=SkillInjection.matching(max_skills=2, max_tokens=1200),
    )

    return Agent(
        model=resolve_model(),
        generation=Generation(max_output_tokens=700),
        instructions=(
            "You are an operations agent platform. Use tools for live facts, "
            "knowledge for policy, memory for team preferences, and keep actions bounded."
        ),
        tools=[lookup_service_status, create_change_plan],
        capabilities=[
            Capability.files(read_only=True),
            Capability.skill(
                "incident-platform",
                description="Operational incident planning skill",
                content=(
                    "When handling incident or deploy work, produce: situation, evidence, "
                    "risk, plan, rollback, and approval status."
                ),
                when_to_use="incident, deploy, platform, rollback",
                allowed_tools=["lookup_service_status", "create_change_plan"],
            ),
        ],
        knowledge=[
            KnowledgeSource.inline(
                "faq",
                [
                    KnowledgeDocument(
                        title="Approval FAQ",
                        content="Production changes require release-owner approval.",
                    )
                ],
            ),
            build_knowledge_source(),
        ],
        memory=memory,
        runtime=runtime,
        schedule=[
            ScheduledJob(
                id="daily-health",
                name="Daily health digest",
                prompt="Summarize checkout and payments health for the operations channel.",
                schedule=ScheduleConfig.interval(hours=24),
                metadata={"channel": "ops"},
            )
        ],
    )


async def main() -> None:
    load_dotenv()
    memory_store = InMemoryPreferenceStore()
    agent = build_agent(memory_store)
    session = agent.session(SessionConfig(id="platform-demo", metadata={"app": "ops-platform"}))

    gateway = SignalAdapter(
        source="gateway:slack",
        type="message",
        summary=lambda event: event["text"],
        payload=lambda event: {"channel": event["channel"]},
        dedupe_key=lambda event: event["event_id"],
    )
    gateway_decision = await session.receive(
        {
            "event_id": "evt-checkout-1",
            "channel": "ops",
            "text": "Checkout latency is rising; prepare an incident response.",
        },
        adapter=gateway,
        urgency="high",
    )

    task = RuntimeTask(
        goal=(
            "Remember: checkout incident responses must include owner approval. "
            "Build a response plan for the checkout incident and cite the runtime signals."
        ),
        input={"service": "checkout", "risk": "latency regression"},
        criteria=["grounded", "bounded", "approval-aware"],
        metadata={"skills": ["incident-platform"]},
    )
    result = await session.run(
        task,
        context=RunContext(
            inputs={
                "platform_surface": "ops dashboard",
                "expected_sections": ["situation", "evidence", "plan", "rollback"],
            }
        ),
    )

    print("=== Runtime Kernel Platform Demo ===")
    print(f"Model:              {agent.config.model.identifier}")
    print(f"Runtime profile:    {agent.config.runtime.describe()['profile']}")
    print(f"Gateway decision:   {gateway_decision.action}")
    print(f"Scheduled jobs:     {len(agent.config.schedule)}")
    print(f"Memory records:     {len(memory_store.records)}")
    print(f"Run state:          {result.state.value}")
    print(f"Output:             {result.output}")

    recall = agent.config.memory.sources[0].prefetch("checkout deploy approval", session_id=session.id)
    print("\n=== Recalled Memory ===")
    print(recall or "(empty)")

    print("\n=== Mechanism Map ===")
    print("Tool use:           lookup_service_status, create_change_plan")
    print("Memory:             MemorySource + custom MemoryStore/Extractor")
    print("Skills:             Capability.skill + SkillInjection")
    print("Harness:            Harness.custom(bounded_harness)")
    print("Gateway/orch:       SignalAdapter + Runtime.orchestrated(max_depth=2)")
    print("Knowledge:          inline FAQ + custom KnowledgeResolver")
    print("Cron:               ScheduledJob + ScheduleConfig.interval")

    if os.getenv("LOOM_DEMO_RUN_CRON") == "1":
        agent.once(
            datetime.now() + timedelta(seconds=1),
            id="demo-once",
            prompt="Acknowledge the scheduled health check in one sentence.",
            name="Demo one-shot cron",
        )
        ticker = agent.start_scheduler(interval_seconds=0.25)
        await asyncio.sleep(1.5)
        agent.stop_scheduler()
        print(f"\nCron ticker stopped: {not ticker.running}")


if __name__ == "__main__":
    asyncio.run(main())
