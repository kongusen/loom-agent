"""Session and run primitives for the public Loom agent API."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any  # noqa: F401 – Any used in run_streaming annotation
from uuid import uuid4

from ..config import (
    KnowledgeBundle,
    KnowledgeCitation,
    KnowledgeEvidence,
    KnowledgeEvidenceItem,
    KnowledgeQuery,
)

if TYPE_CHECKING:
    from ..agent import Agent


def generate_id() -> str:
    """Generate a stable opaque identifier."""
    return str(uuid4())


class RunState(Enum):
    """State for one agent execution."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class SessionConfig:
    """Stable configuration for one stateful session."""

    id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_metadata(self) -> dict[str, Any]:
        payload = dict(self.metadata)
        payload.update(self.extensions)
        return payload


@dataclass(slots=True)
class RunContext:
    """Structured runtime context for one run."""

    inputs: dict[str, Any] = field(default_factory=dict)
    knowledge: KnowledgeBundle | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload = dict(self.inputs)
        if self.knowledge is not None:
            payload["knowledge"] = self.knowledge.to_context_payload()
        payload.update(self.extensions)
        return payload


@dataclass
class RunEvent:
    """Structured event emitted during a run."""

    id: str = field(default_factory=generate_id)
    run_id: str = ""
    type: str = ""
    ts: datetime = field(default_factory=datetime.now)
    visibility: str = "user"
    payload: dict[str, Any] = field(default_factory=dict)


Event = RunEvent


@dataclass
class Artifact:
    """Stable execution artifact."""

    id: str = field(default_factory=generate_id)
    run_id: str = ""
    kind: str = ""
    title: str = ""
    uri: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunResult:
    """Materialized result of a run."""

    run_id: str = ""
    state: RunState = RunState.COMPLETED
    output: str = ""
    artifacts: list[Artifact] = field(default_factory=list)
    events: list[RunEvent] = field(default_factory=list)
    error: dict[str, Any] | None = None
    duration_ms: int = 0


class Run:
    """A single execution within a session."""

    def __init__(self, session: Session, prompt: str, context: RunContext | None = None):
        self.session = session
        self.id = generate_id()
        self.prompt = prompt
        self.context = _normalize_run_context(context)
        self.state = RunState.QUEUED
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        self.output = ""
        self._events: list[RunEvent] = []
        self._artifacts: list[Artifact] = []
        self._event_queue: asyncio.Queue[RunEvent] = asyncio.Queue()
        self._task: asyncio.Task[RunResult] | None = None
        self._result: RunResult | None = None

    async def wait(self) -> RunResult:
        """Execute the run and wait for completion."""
        if self._result is not None:
            return self._result
        if self._task is None:
            self._task = asyncio.create_task(self._execute())
        self._result = await self._task
        return self._result

    async def events(self) -> AsyncIterator[RunEvent]:
        """Stream run events while execution is in progress."""
        if self._task is None:
            self._task = asyncio.create_task(self._execute())

        next_index = 0
        seen_ids: set[str] = set()

        while True:
            while next_index < len(self._events):
                event = self._events[next_index]
                next_index += 1
                if event.id in seen_ids:
                    continue
                seen_ids.add(event.id)
                yield event

            if self.state in {RunState.COMPLETED, RunState.FAILED, RunState.CANCELLED}:
                break

            event = await self._event_queue.get()
            if event.id in seen_ids:
                continue
            seen_ids.add(event.id)
            yield event

    async def artifacts(self) -> list[Artifact]:
        """Return artifacts produced by the run."""
        await self.wait()
        return self._artifacts.copy()

    async def transcript(self) -> dict[str, Any]:
        """Return a serializable execution transcript."""
        await self.wait()
        return {
            "run_id": self.id,
            "session_id": self.session.id,
            "state": self.state.value,
            "prompt": self.prompt,
            "context": self.context.to_payload(),
            "output": self.output,
            "events": [event.__dict__ for event in self._events],
            "artifacts": [artifact.__dict__ for artifact in self._artifacts],
        }

    async def _execute(self) -> RunResult:
        if self.state == RunState.CANCELLED:
            return self._build_result()

        self.state = RunState.RUNNING
        self.updated_at = datetime.now()
        await self._publish_event(
            "run.started",
            {"prompt": self.prompt, "session_id": self.session.id},
        )

        try:
            # Build an async token callback that emits run.token events
            stream_output: bool = bool(
                self.session.agent.config.generation.extensions.get("stream", False)
                if self.session.agent.config.generation
                else False
            )

            async def _on_token(text: str) -> None:
                await self._publish_event("run.token", {"text": text})

            payload = await self.session._execute(
                self.prompt,
                self.context,
                run_id=self.id,
                token_callback=_on_token if stream_output else None,
            )
            status = payload.get("status", "success")
            self.output = str(payload.get("output", ""))

            for raw_event in payload.get("events", []):
                event_payload = dict(raw_event)
                event_type = str(event_payload.pop("type", "run.step"))
                await self._publish_event(event_type, event_payload)

            for raw_artifact in payload.get("artifacts", []):
                artifact = self._coerce_artifact(raw_artifact)
                self._artifacts.append(artifact)

            summary_artifact = Artifact(
                run_id=self.id,
                kind="text",
                title="Run Output",
                uri=f"run://{self.id}/output",
                metadata={"content": self.output, "session_id": self.session.id},
            )
            self._artifacts.append(summary_artifact)
            await self._publish_event(
                "artifact.created",
                {"artifact_id": summary_artifact.id, "kind": summary_artifact.kind},
            )

            self.state = RunState.COMPLETED if status == "success" else RunState.FAILED
            self.updated_at = datetime.now()

            if self.state == RunState.COMPLETED:
                await self._publish_event("run.completed", {"output": self.output})
                return self._build_result()

            error = {"message": status}
            await self._publish_event("run.failed", error, visibility="audit")
            return self._build_result(error=error)
        except Exception as exc:
            self.state = RunState.FAILED
            self.updated_at = datetime.now()
            error = {"message": str(exc)}
            await self._publish_event("run.failed", error, visibility="audit")
            return self._build_result(error=error)

    async def _publish_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        visibility: str = "user",
    ) -> None:
        event = RunEvent(
            run_id=self.id,
            type=event_type,
            visibility=visibility,
            payload=payload,
        )
        self._events.append(event)
        self._event_queue.put_nowait(event)

    def _coerce_artifact(self, value: Artifact | dict[str, Any]) -> Artifact:
        if isinstance(value, Artifact):
            return value
        return Artifact(
            run_id=self.id,
            kind=str(value.get("kind", "text")),
            title=str(value.get("title", "Artifact")),
            uri=str(value.get("uri", f"run://{self.id}/artifact/{generate_id()}")),
            metadata=dict(value.get("metadata", {})),
        )

    def _build_result(self, error: dict[str, Any] | None = None) -> RunResult:
        duration_ms = int(
            max(0.0, (self.updated_at - self.created_at).total_seconds()) * 1000
        )
        return RunResult(
            run_id=self.id,
            state=self.state,
            output=self.output,
            artifacts=self._artifacts.copy(),
            events=self._events.copy(),
            error=error,
            duration_ms=duration_ms,
        )


class Session:
    """Stateful interaction scope for an agent."""

    def __init__(
        self,
        agent: Agent,
        config: SessionConfig | None = None,
    ):
        self.config = _normalize_session_config(config)
        self.agent = agent
        self.id = self.config.id or generate_id()
        self.metadata = self.config.to_metadata()
        self.created_at = datetime.now()
        self._runs: dict[str, Run] = {}
        self._closed = False
        self._engine: Any | None = None

    def start(self, prompt: str, context: RunContext | None = None) -> Run:
        """Create a new run in this session."""
        if self._closed:
            raise RuntimeError("Session is closed")
        run = Run(self, prompt, context=context)
        self._runs[run.id] = run
        return run

    async def run(self, prompt: str, context: RunContext | None = None) -> RunResult:
        """Convenience method to start and await a run."""
        return await self.start(prompt, context=context).wait()

    async def stream(
        self,
        prompt: str,
        context: RunContext | None = None,
    ) -> AsyncIterator[RunEvent]:
        """Convenience method to stream a run."""
        async for event in self.start(prompt, context=context).events():
            yield event

    async def run_streaming(
        self,
        prompt: str,
        context: RunContext | None = None,
    ) -> AsyncIterator[Any]:
        """Stream typed Mode B events directly (no RunEvent wrapper).

        Yields ``StreamEvent`` instances — ``TextDelta``, ``ThinkingDelta``,
        ``ToolCallEvent``, ``ToolResultEvent``, ``DoneEvent``, ``ErrorEvent``.
        """
        from ..types.stream import ErrorEvent

        if self._engine is None:
            provider = self.agent._get_provider()
            if provider is not None:
                self._engine = self.agent._build_engine(provider)

        if self._engine is None:
            yield ErrorEvent(message="Provider unavailable")
            return

        context = _normalize_run_context(context)
        merged_context = context.to_payload()
        if self.agent.config.knowledge:
            merged_context.setdefault(
                "knowledge_sources",
                [source.to_context_payload() for source in self.agent.config.knowledge],
            )

        session_id = (
            self.id
            if (self.agent.config.memory and self.agent.config.memory.enabled)
            else None
        )

        async for event in self._engine.execute_streaming(
            goal=prompt,
            instructions=self.agent.config.instructions,
            context=merged_context,
            session_id=session_id,
        ):
            yield event

    def get_run(self, run_id: str) -> Run | None:
        """Look up a previously created run."""
        return self._runs.get(run_id)

    def list_runs(self) -> list[Run]:
        """List runs in creation order."""
        return list(self._runs.values())

    async def close(self) -> None:
        """Close the session and release run references."""
        self.expire()

    def expire(self) -> None:
        """Immediately release resources so the agent can evict old sessions."""
        self._closed = True
        self._runs.clear()
        self._engine = None

    async def _execute(
        self,
        prompt: str,
        context: RunContext | None = None,
        *,
        run_id: str,
        token_callback: "Any | None" = None,
    ) -> dict[str, Any]:
        if self._engine is None:
            provider = self.agent._get_provider()
            if provider is not None:
                self._engine = self.agent._build_engine(provider)

        return await self.agent._execute(
            prompt,
            context=context,
            session_id=self.id,
            run_id=run_id,
            engine=self._engine,
            token_callback=token_callback,
        )


def _normalize_mapping(value: dict[str, Any], field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be dict, got {type(value).__name__}")
    return dict(value)


def _normalize_session_config(config: SessionConfig | None) -> SessionConfig:
    if config is None:
        return SessionConfig()
    if not isinstance(config, SessionConfig):
        raise TypeError(f"session config must be SessionConfig, got {type(config).__name__}")
    return SessionConfig(
        id=config.id,
        metadata=_normalize_mapping(config.metadata, "session.metadata"),
        extensions=_normalize_mapping(config.extensions, "session.extensions"),
    )


def _normalize_run_context(context: RunContext | None) -> RunContext:
    if context is None:
        return RunContext()
    if not isinstance(context, RunContext):
        raise TypeError(f"context must be RunContext, got {type(context).__name__}")
    return RunContext(
        inputs=_normalize_mapping(context.inputs, "context.inputs"),
        knowledge=_normalize_knowledge_bundle(context.knowledge, "context.knowledge"),
        extensions=_normalize_mapping(context.extensions, "context.extensions"),
    )


def _normalize_knowledge_bundle(
    bundle: KnowledgeBundle | None,
    field_name: str,
) -> KnowledgeBundle | None:
    if bundle is None:
        return None
    if not isinstance(bundle, KnowledgeBundle):
        raise TypeError(f"{field_name} must be KnowledgeBundle, got {type(bundle).__name__}")
    query = bundle.query
    if not isinstance(query, KnowledgeQuery):
        raise TypeError(f"{field_name}.query must be KnowledgeQuery, got {type(query).__name__}")
    normalized_query = KnowledgeQuery(
        text=query.text,
        goal=query.goal,
        top_k=query.top_k,
        source_names=list(query.source_names),
        metadata=_normalize_mapping(query.metadata, f"{field_name}.query.metadata"),
        extensions=_normalize_mapping(query.extensions, f"{field_name}.query.extensions"),
    )

    evidences: list[KnowledgeEvidence] = []
    for index, entry in enumerate(bundle.evidences):
        if not isinstance(entry, KnowledgeEvidence):
            raise TypeError(f"{field_name}.evidences[{index}] must be KnowledgeEvidence, got {type(entry).__name__}")
        evidence_items: list[KnowledgeEvidenceItem] = []
        for item_index, item in enumerate(entry.items):
            if not isinstance(item, KnowledgeEvidenceItem):
                raise TypeError(
                    f"{field_name}.evidences[{index}].items[{item_index}] must be KnowledgeEvidenceItem, "
                    f"got {type(item).__name__}"
                )
            evidence_items.append(
                KnowledgeEvidenceItem(
                    source_name=item.source_name,
                    content=item.content,
                    title=item.title,
                    uri=item.uri,
                    score=item.score,
                    metadata=_normalize_mapping(
                        item.metadata,
                        f"{field_name}.evidences[{index}].items[{item_index}].metadata",
                    ),
                    extensions=_normalize_mapping(
                        item.extensions,
                        f"{field_name}.evidences[{index}].items[{item_index}].extensions",
                    ),
                )
            )
        evidence_citations: list[KnowledgeCitation] = []
        for citation_index, citation in enumerate(entry.citations):
            if not isinstance(citation, KnowledgeCitation):
                raise TypeError(
                    f"{field_name}.evidences[{index}].citations[{citation_index}] must be KnowledgeCitation, "
                    f"got {type(citation).__name__}"
                )
            evidence_citations.append(
                KnowledgeCitation(
                    source_name=citation.source_name,
                    title=citation.title,
                    uri=citation.uri,
                    snippet=citation.snippet,
                    metadata=_normalize_mapping(
                        citation.metadata,
                        f"{field_name}.evidences[{index}].citations[{citation_index}].metadata",
                    ),
                    extensions=_normalize_mapping(
                        citation.extensions,
                        f"{field_name}.evidences[{index}].citations[{citation_index}].extensions",
                    ),
                )
            )
        evidences.append(
                KnowledgeEvidence(
                    query=normalized_query,
                    items=evidence_items,
                    citations=evidence_citations,
                    relevance_score=entry.relevance_score,
                    metadata=_normalize_mapping(entry.metadata, f"{field_name}.evidences[{index}].metadata"),
                    extensions=_normalize_mapping(entry.extensions, f"{field_name}.evidences[{index}].extensions"),
            )
        )

    items: list[KnowledgeEvidenceItem] = []
    for index, item in enumerate(bundle.items):
        if not isinstance(item, KnowledgeEvidenceItem):
            raise TypeError(f"{field_name}.items[{index}] must be KnowledgeEvidenceItem, got {type(item).__name__}")
        items.append(
            KnowledgeEvidenceItem(
                source_name=item.source_name,
                content=item.content,
                title=item.title,
                uri=item.uri,
                score=item.score,
                metadata=_normalize_mapping(item.metadata, f"{field_name}.items[{index}].metadata"),
                extensions=_normalize_mapping(item.extensions, f"{field_name}.items[{index}].extensions"),
            )
        )

    citations: list[KnowledgeCitation] = []
    for index, citation in enumerate(bundle.citations):
        if not isinstance(citation, KnowledgeCitation):
            raise TypeError(f"{field_name}.citations[{index}] must be KnowledgeCitation, got {type(citation).__name__}")
        citations.append(
            KnowledgeCitation(
                source_name=citation.source_name,
                title=citation.title,
                uri=citation.uri,
                snippet=citation.snippet,
                metadata=_normalize_mapping(citation.metadata, f"{field_name}.citations[{index}].metadata"),
                extensions=_normalize_mapping(citation.extensions, f"{field_name}.citations[{index}].extensions"),
            )
        )

    return KnowledgeBundle(
        query=normalized_query,
        evidences=evidences,
        items=items,
        citations=citations,
        relevance_score=bundle.relevance_score,
        metadata=_normalize_mapping(bundle.metadata, f"{field_name}.metadata"),
        extensions=_normalize_mapping(bundle.extensions, f"{field_name}.extensions"),
    )
