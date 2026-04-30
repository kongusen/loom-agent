"""Context coordination runtime extracted from AgentEngine internals."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from ..types import Message

MAX_EVIDENCE_PACKS = 10


class ContextRuntime:
    """Owns context initialization, rendering, and knowledge/skill injection."""

    def __init__(
        self,
        *,
        context_manager: Any,
        ecosystem_manager: Any,
        skill_injection_policy: Any,
        emit: Callable[..., None],
    ) -> None:
        self.context_manager = context_manager
        self.ecosystem_manager = ecosystem_manager
        self.skill_injection_policy = skill_injection_policy
        self.emit = emit

    def initialize_context(self, goal: str, instructions: str, context: dict[str, Any] | None) -> None:
        partitions = self.context_manager.partitions
        if instructions:
            partitions.system.append(Message(role="system", content=instructions))
        partitions.working.goal_progress = f"Goal: {goal}"
        partitions.working.scratchpad = goal
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            partitions.memory.append(Message(role="system", content=f"Context:\n{context_str}"))
        self.inject_knowledge(goal, context)
        self.inject_runtime_skills(goal, context)

    def inject_knowledge(self, goal: str, _context: dict[str, Any] | None) -> None:
        sources = getattr(self.context_manager, "_knowledge_sources", None)
        if not sources:
            return

        from ..config import KnowledgeQuery, KnowledgeSource

        query = KnowledgeQuery(text=goal, goal=goal)
        total_items = 0
        self.context_manager.dashboard.add_question(goal)
        for source in sources:
            if not isinstance(source, KnowledgeSource):
                continue
            evidence = source.resolve(query)
            for item in evidence.items:
                self.context_manager.dashboard.add_evidence(
                    {
                        "source": source.name,
                        "title": item.title or "",
                        "content": item.content,
                        "uri": item.uri or "",
                        "score": item.score,
                    }
                )
                total_items += 1
            for citation in evidence.citations:
                if citation.uri or citation.title:
                    self.context_manager.dashboard.add_evidence(
                        {
                            "source": source.name,
                            "title": citation.title or "",
                            "content": citation.snippet or "",
                            "uri": citation.uri or "",
                            "citation": citation.uri or citation.title or source.name,
                        }
                    )
        if total_items:
            self.evict_knowledge_overflow()
            self.emit("knowledge_injected", sources=len(sources), items=total_items)

    def evict_knowledge_overflow(self, max_packs: int = MAX_EVIDENCE_PACKS) -> None:
        packs = self.context_manager.dashboard.dashboard.knowledge_surface.evidence_packs
        if len(packs) <= max_packs:
            return
        packs.sort(key=lambda pack: pack.get("score") or 0.0, reverse=True)
        evicted = packs[max_packs:]
        del packs[max_packs:]
        self.emit("knowledge_evicted", count=len(evicted))

    def inject_runtime_skills(self, goal: str, context: dict[str, Any] | None) -> None:
        self.context_manager.partitions.skill = []
        if self.ecosystem_manager is None:
            return

        from ..runtime.skills import SkillInjection

        ctx_injection = getattr(self.context_manager, "_skill_injection", None)
        policy = ctx_injection or self.skill_injection_policy or SkillInjection.matching()
        selected = policy.select(
            self.ecosystem_manager.skill_registry,
            goal=goal,
            context=context,
        )
        rendered = policy.render(selected)
        self.context_manager.partitions.skill.extend(rendered)
        if rendered:
            self.emit(
                "skills_injected",
                skills=[skill.name for skill in selected],
                count=len(rendered),
            )

    def inject_session_history(self, history: list[dict[str, Any]] | None) -> None:
        if not history:
            return
        for entry in history:
            role = entry.get("role")
            if role not in {"system", "user", "assistant"}:
                continue
            content = entry.get("content", "")
            self.context_manager.partitions.history.append(
                Message(
                    role=cast("Any", role),
                    content=content if isinstance(content, str) else str(content),
                )
            )

    def build_messages(self, goal: str) -> list[Message]:
        render = getattr(self.context_manager, "render", None)
        if callable(render):
            return cast("list[Message]", render(goal))
        messages = self.context_manager.partitions.get_all_messages()
        if not messages or messages[-1].role != "user":
            messages.append(Message(role="user", content=goal))
        return messages
