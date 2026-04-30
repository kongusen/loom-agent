"""User-facing declaration helpers for the public Agent API."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .knowledge import KnowledgeResolver, KnowledgeSource
from .schedule import ScheduleConfig, ScheduledJob

if TYPE_CHECKING:
    from ..runtime.capability import CapabilitySpec
    from ..runtime.signals import (
        SignalAdapter,
        SignalPayloadField,
        SignalStringField,
        SignalUrgency,
    )
else:
    CapabilitySpec = Any
    SignalAdapter = Any
    SignalPayloadField = Any
    SignalStringField = Any
    SignalUrgency = str


@dataclass(slots=True)
class Instructions:
    """Structured instructions rendered into the agent system prompt."""

    role: str = ""
    style: str = ""
    constraints: list[str] = field(default_factory=list)
    content: str = ""

    def render(self) -> str:
        parts: list[str] = []
        if self.role:
            parts.append(f"Role: {self.role}")
        if self.style:
            parts.append(f"Style: {self.style}")
        if self.constraints:
            constraints = "\n".join(f"- {item}" for item in self.constraints)
            parts.append(f"Constraints:\n{constraints}")
        if self.content:
            parts.append(self.content)
        return "\n\n".join(parts)


@dataclass(slots=True)
class Files:
    """User-facing file-system capability declaration."""

    read_only: bool = True
    name: str = "files"

    def capabilities(self) -> list[CapabilitySpec]:
        from ..runtime.capability import Capability

        return [Capability.files(read_only=self.read_only, name=self.name)]


@dataclass(slots=True)
class Web:
    """User-facing web research capability declaration."""

    name: str = "web"

    @classmethod
    def enabled(cls, *, name: str = "web") -> Web:
        return cls(name=name)

    def capabilities(self) -> list[CapabilitySpec]:
        from ..runtime.capability import Capability

        return [Capability.web(name=self.name)]


@dataclass(slots=True)
class Shell:
    """User-facing shell execution capability declaration."""

    require_approval: bool = True
    name: str = "shell"

    @classmethod
    def approval_required(cls, *, name: str = "shell") -> Shell:
        return cls(require_approval=True, name=name)

    @classmethod
    def enabled(cls, *, require_approval: bool = True, name: str = "shell") -> Shell:
        return cls(require_approval=require_approval, name=name)

    def capabilities(self) -> list[CapabilitySpec]:
        from ..runtime.capability import Capability

        return [Capability.shell(require_approval=self.require_approval, name=self.name)]


@dataclass(slots=True)
class MCP:
    """User-facing MCP server capability declaration."""

    name: str | None = None
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def server(cls, name: str, **config: Any) -> MCP:
        return cls(name=name, config=dict(config))

    def capabilities(self) -> list[CapabilitySpec]:
        from ..runtime.capability import Capability

        return [Capability.mcp(self.name, **self.config)]


@dataclass(slots=True)
class Skill:
    """User-facing skill declaration."""

    name: str
    description: str = ""
    content: str | None = None
    path: str | None = None
    when_to_use: str | None = None
    allowed_tools: list[str] = field(default_factory=list)
    argument_hint: str | None = None
    model: str | None = None
    user_invocable: bool = True
    effort: int | None = None
    agent: str | None = None
    context: str = "inline"
    paths: list[str] | None = None
    version: str | None = None

    @classmethod
    def inline(
        cls,
        name: str,
        *,
        content: str,
        description: str = "",
        when_to_use: str | None = None,
        allowed_tools: list[str] | None = None,
        argument_hint: str | None = None,
        model: str | None = None,
        user_invocable: bool = True,
        effort: int | None = None,
        agent: str | None = None,
        context: str = "inline",
        paths: list[str] | None = None,
        version: str | None = None,
    ) -> Skill:
        return cls(
            name=name,
            description=description,
            content=content,
            when_to_use=when_to_use,
            allowed_tools=list(allowed_tools or []),
            argument_hint=argument_hint,
            model=model,
            user_invocable=user_invocable,
            effort=effort,
            agent=agent,
            context=context,
            paths=list(paths) if paths is not None else None,
            version=version,
        )

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        name: str | None = None,
        description: str = "",
    ) -> Skill:
        resolved = Path(path)
        return cls(
            name=name or resolved.stem,
            description=description,
            path=str(resolved),
        )

    @classmethod
    def from_directory(
        cls,
        path: str | Path,
        *,
        name: str | None = None,
        description: str = "",
    ) -> Skill:
        resolved = Path(path)
        return cls(
            name=name or resolved.name or "skills",
            description=description,
            path=str(resolved),
        )

    def capabilities(self) -> list[CapabilitySpec]:
        from ..runtime.capability import Capability

        config: dict[str, Any] = {
            "user_invocable": self.user_invocable,
            "context": self.context,
        }
        if self.content is not None:
            config["content"] = self.content
        if self.path is not None:
            config["path"] = self.path
        if self.when_to_use is not None:
            config["when_to_use"] = self.when_to_use
        if self.allowed_tools:
            config["allowed_tools"] = list(self.allowed_tools)
        if self.argument_hint is not None:
            config["argument_hint"] = self.argument_hint
        if self.model is not None:
            config["model"] = self.model
        if self.effort is not None:
            config["effort"] = self.effort
        if self.agent is not None:
            config["agent"] = self.agent
        if self.paths is not None:
            config["paths"] = list(self.paths)
        if self.version is not None:
            config["version"] = self.version
        return [Capability.skill(self.name, description=self.description, **config)]


@dataclass(slots=True)
class Knowledge:
    """User-facing knowledge source collection."""

    _sources: list[KnowledgeSource] = field(default_factory=list)

    def to_sources(self) -> list[KnowledgeSource]:
        return list(self._sources)

    @classmethod
    def of(cls, *sources: KnowledgeSource) -> Knowledge:
        return cls(_sources=list(sources))

    @classmethod
    def sources(
        cls,
        entries: Iterable[str | Path | KnowledgeSource],
        *,
        name: str = "knowledge",
        glob: str = "**/*.md",
    ) -> Knowledge:
        sources: list[KnowledgeSource] = []
        inline_documents: list[str] = []
        for index, entry in enumerate(entries):
            if isinstance(entry, KnowledgeSource):
                sources.append(entry)
                continue
            path = Path(entry)
            if path.exists():
                if path.is_dir():
                    sources.append(KnowledgeSource.from_directory(path.name or name, path, glob))
                elif path.is_file():
                    sources.append(
                        KnowledgeSource.inline(
                            path.stem or f"{name}-{index}",
                            [path.read_text(encoding="utf-8")],
                        )
                    )
                continue
            inline_documents.append(str(entry))
        if inline_documents:
            sources.append(KnowledgeSource.inline(name, inline_documents))
        return cls(_sources=sources)

    sources_from = sources

    @classmethod
    def inline(
        cls,
        name: str,
        documents: list[str],
        *,
        description: str = "",
    ) -> Knowledge:
        return cls(_sources=[KnowledgeSource.inline(name, documents, description=description)])

    @classmethod
    def from_directory(
        cls,
        path: str | Path,
        *,
        name: str | None = None,
        glob: str = "**/*.md",
        description: str = "",
    ) -> Knowledge:
        resolved = Path(path)
        return cls(
            _sources=[
                KnowledgeSource.from_directory(
                    name or resolved.name or "knowledge",
                    resolved,
                    glob,
                    description=description,
                )
            ]
        )

    @classmethod
    def dynamic(
        cls,
        name: str,
        resolver: KnowledgeResolver,
        *,
        description: str = "",
    ) -> Knowledge:
        return cls(_sources=[KnowledgeSource.dynamic(name, resolver, description=description)])


@dataclass(slots=True)
class Gateway:
    """User-facing external event producer declaration."""

    name: str
    adapter: SignalAdapter

    @classmethod
    def webhook(
        cls,
        name: str,
        *,
        source: str | None = None,
        type: str = "event",
        urgency: SignalUrgency = "normal",
        summary: SignalStringField = None,
        payload: SignalPayloadField = None,
        session_id: SignalStringField = None,
        run_id: SignalStringField = None,
        dedupe_key: SignalStringField = None,
    ) -> Gateway:
        from ..runtime.signals import SignalAdapter

        return cls(
            name=name,
            adapter=SignalAdapter(
                source=source or f"gateway:{name}",
                type=type,
                urgency=urgency,
                summary=summary,
                payload=payload,
                session_id=session_id,
                run_id=run_id,
                dedupe_key=dedupe_key,
            ),
        )

    def adapt(self, event: Any) -> Any:
        return self.adapter.adapt(event)


class Cron:
    """User-facing scheduled job builders."""

    @staticmethod
    def once(
        id: str,
        *,
        prompt: str | None = None,
        at: str | datetime,
        name: str = "",
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledJob:
        return ScheduledJob(
            id=id,
            prompt=prompt or id,
            schedule=ScheduleConfig.once(at),
            name=name,
            enabled=enabled,
            repeat=1,
            metadata=dict(metadata or {}),
        )

    @staticmethod
    def interval(
        id: str,
        *,
        prompt: str | None = None,
        every: str | None = None,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
        name: str = "",
        enabled: bool = True,
        repeat: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledJob:
        parsed_minutes, parsed_hours, parsed_days = _parse_interval(every)
        return ScheduledJob(
            id=id,
            prompt=prompt or id,
            schedule=ScheduleConfig.interval(
                minutes=minutes + parsed_minutes,
                hours=hours + parsed_hours,
                days=days + parsed_days,
            ),
            name=name,
            enabled=enabled,
            repeat=repeat,
            metadata=dict(metadata or {}),
        )

    @staticmethod
    def daily(
        id: str,
        *,
        prompt: str | None = None,
        at: str = "09:00",
        name: str = "",
        enabled: bool = True,
        repeat: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledJob:
        hour, minute = _parse_time(at)
        return ScheduledJob(
            id=id,
            prompt=prompt or id,
            schedule=ScheduleConfig(kind="cron", cron_expr=f"{minute} {hour} * * *"),
            name=name,
            enabled=enabled,
            repeat=repeat,
            metadata=dict(metadata or {}),
        )

    @staticmethod
    def cron(
        id: str,
        *,
        prompt: str | None = None,
        expr: str,
        name: str = "",
        enabled: bool = True,
        repeat: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledJob:
        if not expr.strip():
            raise ValueError("cron expression must not be empty")
        return ScheduledJob(
            id=id,
            prompt=prompt or id,
            schedule=ScheduleConfig(kind="cron", cron_expr=expr),
            name=name,
            enabled=enabled,
            repeat=repeat,
            metadata=dict(metadata or {}),
        )


def _parse_interval(value: str | None) -> tuple[int, int, int]:
    if value is None:
        return 0, 0, 0
    raw = value.strip().lower()
    if not raw:
        raise ValueError("interval string must not be empty")
    unit = raw[-1]
    amount = int(raw[:-1])
    if amount <= 0:
        raise ValueError("interval amount must be positive")
    if unit == "m":
        return amount, 0, 0
    if unit == "h":
        return 0, amount, 0
    if unit == "d":
        return 0, 0, amount
    raise ValueError("interval string must end with m, h, or d")


def _parse_time(value: str) -> tuple[int, int]:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError("daily time must use HH:MM format")
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("daily time must be between 00:00 and 23:59")
    return hour, minute


__all__ = [
    "Instructions",
    "Files",
    "Web",
    "Shell",
    "MCP",
    "Skill",
    "Knowledge",
    "Gateway",
    "Cron",
]
