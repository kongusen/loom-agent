"""Runtime skill injection policy."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ..ecosystem.skill import Skill, SkillRegistry
from ..utils import count_tokens


@dataclass(slots=True)
class SkillInjection:
    """Select and render skills into the runtime ``C_skill`` partition.

    This is a sub-configuration of ``ContextPolicy``, not a standalone Policy.
    Use ``ContextPolicy.manager(skill_injection=SkillInjection.matching(...))``
    or pass directly to ``Runtime(skill_injection=...)``.
    """

    max_skills: int = 3
    max_tokens: int = 4000
    include_metadata: bool = True

    @classmethod
    def matching(
        cls,
        *,
        max_skills: int = 3,
        max_tokens: int = 4000,
        include_metadata: bool = True,
    ) -> SkillInjection:
        """Inject explicitly selected or task-matched skills."""
        return cls(
            max_skills=max_skills,
            max_tokens=max_tokens,
            include_metadata=include_metadata,
        )

    @classmethod
    def none(cls) -> SkillInjection:
        """Disable runtime skill injection."""
        return cls(max_skills=0, max_tokens=0)

    def select(
        self,
        registry: SkillRegistry,
        *,
        goal: str,
        context: dict[str, Any] | None = None,
    ) -> list[Skill]:
        """Select explicit skills first, then skills whose ``when_to_use`` matches."""
        if self.max_skills <= 0 or self.max_tokens <= 0:
            return []

        selected: list[Skill] = []
        seen: set[str] = set()

        for name in _explicit_skill_names(context or {}):
            skill = registry.get(name)
            if skill is not None and skill.name not in seen:
                selected.append(skill)
                seen.add(skill.name)

        for skill in registry.match_task(goal):
            if skill.name not in seen:
                selected.append(skill)
                seen.add(skill.name)

        return selected[: self.max_skills]

    def render(self, skills: Iterable[Skill]) -> list[str]:
        """Render selected skills as ``ContextPartitions.skill`` entries."""
        entries: list[str] = []
        remaining = self.max_tokens
        for skill in skills:
            if remaining <= 0:
                break
            rendered = self._render_one(skill, remaining)
            if not rendered:
                continue
            entries.append(rendered)
            remaining -= count_tokens(rendered)
        return entries

    def _render_one(self, skill: Skill, budget_tokens: int) -> str:
        header: list[str] = [f"### Skill: {skill.name}"]
        if self.include_metadata and skill.description:
            header.append(f"Description: {skill.description}")
        if self.include_metadata and skill.when_to_use:
            header.append(f"When to use: {skill.when_to_use}")
        if self.include_metadata and skill.allowed_tools:
            header.append(f"Allowed tools: {', '.join(skill.allowed_tools)}")

        prefix = "\n".join(header)
        prefix_tokens = count_tokens(prefix)
        content_budget = max(0, budget_tokens - prefix_tokens)
        if content_budget <= 0:
            return prefix

        content = skill.content.strip()
        content = _truncate_to_token_budget(content, content_budget)
        if not content:
            return prefix
        return f"{prefix}\n\n{content}"


def _explicit_skill_names(context: dict[str, Any]) -> list[str]:
    names: list[str] = []
    _extend_names(names, context.get("skill"))
    _extend_names(names, context.get("skills"))
    _extend_names(names, context.get("skill_names"))
    _extend_names(names, context.get("skillNames"))

    metadata = context.get("task_metadata")
    if isinstance(metadata, dict):
        _extend_names(names, metadata.get("skill"))
        _extend_names(names, metadata.get("skills"))
        _extend_names(names, metadata.get("skill_names"))
        _extend_names(names, metadata.get("skillNames"))

    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        if name not in seen:
            deduped.append(name)
            seen.add(name)
    return deduped


def _extend_names(target: list[str], value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str):
        target.append(value.removeprefix("skill:"))
        return
    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, str):
                target.append(item.removeprefix("skill:"))


def _truncate_to_token_budget(text: str, budget_tokens: int) -> str:
    if budget_tokens <= 0:
        return ""
    if count_tokens(text) <= budget_tokens:
        return text
    max_chars = max(0, budget_tokens * 4)
    if max_chars <= 1:
        return ""
    return text[: max_chars - 1].rstrip() + "..."


__all__ = ["SkillInjection"]
