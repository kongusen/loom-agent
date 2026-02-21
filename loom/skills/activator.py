"""Skill activator — trigger matching for skills."""

from __future__ import annotations

import re
from typing import Any

from ..types import SkillTrigger, SkillActivation


def match_trigger(skill: Any, input_text: str) -> SkillActivation | None:
    trigger: SkillTrigger | None = getattr(skill, "trigger", None)
    if not trigger:
        return SkillActivation(skill=skill, score=getattr(skill, "priority", 0.0), reason="always active")

    result = _evaluate(trigger, input_text)
    if not result:
        return None
    score = getattr(skill, "priority", 0.5) * result[0]
    return SkillActivation(skill=skill, score=score, reason=result[1])


def _evaluate(trigger: SkillTrigger, text: str) -> tuple[float, str] | None:
    if trigger.type == "keyword":
        lower = text.lower()
        matched = [k for k in trigger.keywords if k.lower() in lower]
        if not matched:
            return None
        if trigger.match_all and len(matched) < len(trigger.keywords):
            return None
        return (len(matched) / max(len(trigger.keywords), 1), f"keywords: {', '.join(matched)}")

    if trigger.type == "pattern" and trigger.pattern:
        if re.search(trigger.pattern, text, re.IGNORECASE):
            return (1.0, f"pattern: /{trigger.pattern}/")
        return None

    if trigger.type == "semantic":
        # Semantic matching via embedding similarity (set at runtime)
        embedder = getattr(trigger, "_embedder", None)
        if not embedder:
            return None
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None  # caller should use async path
            score = loop.run_until_complete(_semantic_score(embedder, trigger, text))
        except RuntimeError:
            return None
        if score and score >= trigger.threshold:
            return (score, f"semantic: {score:.2f}")
        return None

    if trigger.type == "custom" and trigger.evaluator:
        result = trigger.evaluator(text)
        if result is not None and result > 0:
            return (min(result, 1.0), "custom evaluator")
        return None

    return None


async def match_trigger_async(skill: Any, input_text: str, embedder: Any = None) -> SkillActivation | None:
    """Async version supporting semantic triggers."""
    trigger: SkillTrigger | None = getattr(skill, "trigger", None)
    if not trigger:
        return SkillActivation(skill=skill, score=getattr(skill, "priority", 0.0), reason="always active")

    if trigger.type == "semantic" and embedder:
        score = await _semantic_score(embedder, trigger, input_text)
        if score and score >= trigger.threshold:
            s = getattr(skill, "priority", 0.5) * score
            return SkillActivation(skill=skill, score=s, reason=f"semantic: {score:.2f}")
        return None

    result = _evaluate(trigger, input_text)
    if not result:
        return None
    score = getattr(skill, "priority", 0.5) * result[0]
    return SkillActivation(skill=skill, score=score, reason=result[1])


async def _semantic_score(embedder: Any, trigger: SkillTrigger, text: str) -> float | None:
    try:
        kw_text = " ".join(trigger.keywords) if trigger.keywords else ""
        if not kw_text:
            return None
        vecs = await embedder.embed_batch([kw_text, text])
        dot = sum(a * b for a, b in zip(vecs[0], vecs[1]))
        na = sum(x * x for x in vecs[0]) ** 0.5
        nb = sum(x * x for x in vecs[1]) ** 0.5
        return dot / max(na * nb, 1e-10)
    except Exception:
        return None
