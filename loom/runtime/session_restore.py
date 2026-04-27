"""Session restoration policy for persisted runtime transcripts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .session_store import TranscriptRecord


@dataclass(frozen=True, slots=True)
class SessionRestorePolicy:
    """Decides what persisted session state enters the next run context."""

    enabled: bool = True
    include_transcript: bool = True
    include_context: bool = False
    include_events: bool = False
    include_artifacts: bool = False
    max_transcripts: int = 8
    max_messages: int = 24
    max_runtime_items: int = 12
    max_chars: int = 12000

    @classmethod
    def none(cls) -> SessionRestorePolicy:
        return cls(enabled=False)

    @classmethod
    def transcript_only(
        cls,
        *,
        max_transcripts: int = 8,
        max_messages: int = 24,
        max_chars: int = 12000,
    ) -> SessionRestorePolicy:
        return cls(
            include_transcript=True,
            include_context=False,
            include_events=False,
            include_artifacts=False,
            max_transcripts=max_transcripts,
            max_messages=max_messages,
            max_chars=max_chars,
        )

    @classmethod
    def window(
        cls,
        *,
        max_transcripts: int = 8,
        max_messages: int = 24,
        max_runtime_items: int = 12,
        max_chars: int = 12000,
        include_context: bool = True,
        include_events: bool = True,
        include_artifacts: bool = True,
    ) -> SessionRestorePolicy:
        return cls(
            include_transcript=True,
            include_context=include_context,
            include_events=include_events,
            include_artifacts=include_artifacts,
            max_transcripts=max_transcripts,
            max_messages=max_messages,
            max_runtime_items=max_runtime_items,
            max_chars=max_chars,
        )

    @classmethod
    def runtime_state(
        cls,
        *,
        max_transcripts: int = 8,
        max_runtime_items: int = 12,
        max_chars: int = 12000,
    ) -> SessionRestorePolicy:
        return cls(
            include_transcript=False,
            include_context=True,
            include_events=True,
            include_artifacts=True,
            max_transcripts=max_transcripts,
            max_runtime_items=max_runtime_items,
            max_chars=max_chars,
        )

    def build_history(self, transcripts: list[TranscriptRecord]) -> list[dict[str, Any]]:
        """Render persisted transcripts into provider-safe history messages."""
        if not self.enabled:
            return []

        selected = transcripts[-max(0, self.max_transcripts):] if self.max_transcripts else []
        messages: list[dict[str, Any]] = []

        if self.include_transcript:
            for transcript in selected:
                messages.extend(self._restore_messages(transcript.messages))

        runtime_block = self._render_runtime_state(selected)
        if runtime_block:
            messages.append({"role": "system", "content": runtime_block})

        return self._trim_to_budget(messages)

    def _restore_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        restored: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role")
            if role not in {"user", "assistant"}:
                continue
            content = message.get("content", "")
            restored.append({
                "role": role,
                "content": content if isinstance(content, str) else str(content),
            })
        if self.max_messages <= 0:
            return []
        return restored[-self.max_messages:]

    def _render_runtime_state(self, transcripts: list[TranscriptRecord]) -> str:
        sections: list[str] = []
        for transcript in transcripts:
            details: list[str] = []
            if self.include_context and transcript.context:
                details.append(f"Context: {_compact_json(transcript.context)}")
            if self.include_events and transcript.events:
                details.append(
                    "Events: "
                    + "; ".join(
                        _summarize_event(event)
                        for event in transcript.events[-self.max_runtime_items:]
                    )
                )
            if self.include_artifacts and transcript.artifacts:
                details.append(
                    "Artifacts: "
                    + "; ".join(
                        _summarize_artifact(artifact)
                        for artifact in transcript.artifacts[-self.max_runtime_items:]
                    )
                )
            if details:
                sections.append(
                    f"Run {transcript.id} ({transcript.prompt})\n" + "\n".join(details)
                )

        if not sections:
            return ""
        return "## Restored Runtime State\n" + "\n\n".join(sections)

    def _trim_to_budget(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.max_chars <= 0:
            return []
        selected: list[dict[str, Any]] = []
        total = 0
        for message in reversed(messages):
            content = str(message.get("content", ""))
            cost = len(content)
            if cost > self.max_chars:
                content = content[-self.max_chars:]
                cost = len(content)
                message = {**message, "content": content}
            if selected and total + cost > self.max_chars:
                continue
            selected.append(message)
            total += cost
            if total >= self.max_chars:
                break
        return list(reversed(selected))


def _summarize_event(event: dict[str, Any]) -> str:
    event_type = str(event.get("type", "event"))
    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        return event_type
    summary = (
        payload.get("summary")
        or payload.get("tool_name")
        or payload.get("name")
        or payload.get("content")
        or payload.get("output")
    )
    if summary is None:
        return f"{event_type} {_compact_json(payload)}"
    return f"{event_type} {summary}"


def _summarize_artifact(artifact: dict[str, Any]) -> str:
    title = artifact.get("title") or artifact.get("kind") or "artifact"
    uri = artifact.get("uri")
    metadata = artifact.get("metadata", {})
    content = metadata.get("content") if isinstance(metadata, dict) else None
    parts = [str(title)]
    if uri:
        parts.append(str(uri))
    if content:
        parts.append(str(content))
    return " ".join(parts)


def _compact_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except TypeError:
        return str(value)
