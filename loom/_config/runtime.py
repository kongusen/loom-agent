"""Configuration contracts for the public Loom API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import RuntimeFallbackMode


@dataclass(slots=True)
class RuntimeFallback:
    """Stable runtime fallback behavior."""

    mode: RuntimeFallbackMode = RuntimeFallbackMode.LOCAL_SUMMARY
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeLimits:
    """Stable execution limits for the runtime."""

    max_iterations: int = 100
    max_context_tokens: int | None = None
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeFeatures:
    """Stable runtime feature flags."""

    enable_safety: bool = True
    fallback: RuntimeFallback = field(default_factory=RuntimeFallback)
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeConfig:
    """Execution-engine configuration exposed on the public API."""

    limits: RuntimeLimits = field(default_factory=RuntimeLimits)
    features: RuntimeFeatures = field(default_factory=RuntimeFeatures)
    continuity: Any | None = None
    context: Any | None = None
    harness: Any | None = None
    quality: Any | None = None
    delegation: Any | None = None
    governance: Any | None = None
    feedback: Any | None = None
    skill_injection: Any | None = None
    session_restore: Any | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def describe(self) -> dict[str, Any]:
        """Return a stable, serializable summary of this runtime profile."""
        return {
            "profile": self.extensions.get("profile", "custom"),
            "limits": {
                "max_iterations": self.limits.max_iterations,
                "max_context_tokens": self.limits.max_context_tokens,
            },
            "features": {
                "enable_safety": self.features.enable_safety,
                "fallback": self.features.fallback.mode.value,
            },
            "policies": {
                "context": _component_name(self.context),
                "continuity": _component_name(self.continuity),
                "harness": _component_name(self.harness),
                "quality": _component_name(self.quality),
                "delegation": _component_name(self.delegation),
                "governance": _component_name(self.governance),
                "feedback": _component_name(self.feedback),
                "skill_injection": _component_name(self.skill_injection),
                "session_restore": _component_name(self.session_restore),
            },
            "session_restore": _session_restore_summary(self.session_restore),
            "delegation": _delegation_summary(self.delegation),
        }

    @classmethod
    def sdk(
        cls,
        *,
        max_iterations: int = 32,
        max_context_tokens: int | None = 64000,
        limits: RuntimeLimits | None = None,
        features: RuntimeFeatures | None = None,
        harness: Any | None = None,
        governance: Any | None = None,
        feedback: Any | None = None,
        skill_injection: Any | None = None,
        session_restore: Any | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> RuntimeConfig:
        """Build the default SDK runtime profile.

        This profile keeps the kernel small: one run, default governance, and
        no feedback collection unless the caller opts in.
        """
        from ..runtime.feedback import FeedbackPolicy
        from ..runtime.governance import GovernancePolicy
        from ..runtime.harness import Harness
        from ..runtime.session_restore import SessionRestorePolicy
        from ..runtime.skills import SkillInjectionPolicy

        return cls(
            limits=limits or RuntimeLimits(
                max_iterations=max_iterations,
                max_context_tokens=max_context_tokens,
            ),
            features=features or RuntimeFeatures(),
            harness=harness or Harness.single_run(),
            governance=governance or GovernancePolicy.default(),
            feedback=feedback or FeedbackPolicy.none(),
            skill_injection=skill_injection or SkillInjectionPolicy.matching(),
            session_restore=session_restore or SessionRestorePolicy.transcript_only(),
            extensions=_profile_extensions("sdk", extensions),
        )

    @classmethod
    def long_running(
        cls,
        *,
        criteria: list[str] | None = None,
        max_iterations: int = 128,
        max_context_tokens: int = 200000,
        limits: RuntimeLimits | None = None,
        features: RuntimeFeatures | None = None,
        context: Any | None = None,
        continuity: Any | None = None,
        harness: Any | None = None,
        quality: Any | None = None,
        governance: Any | None = None,
        feedback: Any | None = None,
        skill_injection: Any | None = None,
        session_restore: Any | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> RuntimeConfig:
        """Build a runtime profile for long-running SDK tasks."""
        from ..runtime.context import ContextProtocol
        from ..runtime.continuity import ContinuityPolicy
        from ..runtime.feedback import FeedbackPolicy
        from ..runtime.governance import GovernancePolicy
        from ..runtime.harness import Harness
        from ..runtime.quality import QualityGate
        from ..runtime.session_restore import SessionRestorePolicy
        from ..runtime.skills import SkillInjectionPolicy

        resolved_continuity = continuity or ContinuityPolicy.handoff()
        return cls(
            limits=limits or RuntimeLimits(
                max_iterations=max_iterations,
                max_context_tokens=max_context_tokens,
            ),
            features=features or RuntimeFeatures(),
            context=context or ContextProtocol.manager(
                max_tokens=max_context_tokens,
                continuity=resolved_continuity,
            ),
            continuity=resolved_continuity,
            harness=harness or Harness.single_run(),
            quality=quality or QualityGate.criteria(criteria or []),
            governance=governance or GovernancePolicy.default(),
            feedback=feedback or FeedbackPolicy.collector(),
            skill_injection=skill_injection or SkillInjectionPolicy.matching(),
            session_restore=session_restore or SessionRestorePolicy.window(),
            extensions=_profile_extensions("long_running", extensions),
        )

    @classmethod
    def supervised(
        cls,
        *,
        criteria: list[str] | None = None,
        max_iterations: int = 80,
        max_context_tokens: int = 120000,
        limits: RuntimeLimits | None = None,
        features: RuntimeFeatures | None = None,
        context: Any | None = None,
        continuity: Any | None = None,
        harness: Any | None = None,
        quality: Any | None = None,
        delegation: Any | None = None,
        governance: Any | None = None,
        feedback: Any | None = None,
        skill_injection: Any | None = None,
        session_restore: Any | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> RuntimeConfig:
        """Build a runtime profile for quality-gated supervised work."""
        from ..runtime.context import ContextProtocol
        from ..runtime.continuity import ContinuityPolicy
        from ..runtime.delegation import DelegationPolicy
        from ..runtime.feedback import FeedbackPolicy
        from ..runtime.governance import GovernancePolicy
        from ..runtime.harness import Harness
        from ..runtime.quality import QualityGate
        from ..runtime.session_restore import SessionRestorePolicy
        from ..runtime.skills import SkillInjectionPolicy

        resolved_continuity = continuity or ContinuityPolicy.handoff()
        return cls(
            limits=limits or RuntimeLimits(
                max_iterations=max_iterations,
                max_context_tokens=max_context_tokens,
            ),
            features=features or RuntimeFeatures(),
            context=context or ContextProtocol.manager(
                max_tokens=max_context_tokens,
                continuity=resolved_continuity,
            ),
            continuity=resolved_continuity,
            harness=harness or Harness.single_run(),
            quality=quality or QualityGate.criteria(criteria or []),
            delegation=delegation or DelegationPolicy.none(),
            governance=governance or GovernancePolicy.default(),
            feedback=feedback or FeedbackPolicy.collector(),
            skill_injection=skill_injection or SkillInjectionPolicy.matching(),
            session_restore=session_restore or SessionRestorePolicy.window(),
            extensions=_profile_extensions("supervised", extensions),
        )

    @classmethod
    def autonomous(
        cls,
        *,
        max_depth: int = 5,
        criteria: list[str] | None = None,
        max_iterations: int = 200,
        max_context_tokens: int = 200000,
        limits: RuntimeLimits | None = None,
        features: RuntimeFeatures | None = None,
        context: Any | None = None,
        continuity: Any | None = None,
        harness: Any | None = None,
        quality: Any | None = None,
        delegation: Any | None = None,
        governance: Any | None = None,
        feedback: Any | None = None,
        skill_injection: Any | None = None,
        session_restore: Any | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> RuntimeConfig:
        """Build a runtime profile for autonomous, depth-limited work."""
        from ..runtime.context import ContextProtocol
        from ..runtime.continuity import ContinuityPolicy
        from ..runtime.delegation import DelegationPolicy
        from ..runtime.feedback import FeedbackPolicy
        from ..runtime.governance import GovernancePolicy
        from ..runtime.harness import Harness
        from ..runtime.quality import QualityGate
        from ..runtime.session_restore import SessionRestorePolicy
        from ..runtime.skills import SkillInjectionPolicy

        resolved_continuity = continuity or ContinuityPolicy.handoff()
        return cls(
            limits=limits or RuntimeLimits(
                max_iterations=max_iterations,
                max_context_tokens=max_context_tokens,
            ),
            features=features or RuntimeFeatures(),
            context=context or ContextProtocol.manager(
                max_tokens=max_context_tokens,
                continuity=resolved_continuity,
            ),
            continuity=resolved_continuity,
            harness=harness or Harness.single_run(),
            quality=quality or QualityGate.criteria(criteria or []),
            delegation=delegation or DelegationPolicy.depth_limited(max_depth),
            governance=governance or GovernancePolicy.default(),
            feedback=feedback or FeedbackPolicy.collector(),
            skill_injection=skill_injection or SkillInjectionPolicy.matching(),
            session_restore=session_restore or SessionRestorePolicy.window(),
            extensions=_profile_extensions("autonomous", extensions),
        )


def _profile_extensions(
    profile: str,
    extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {"profile": profile, **dict(extensions or {})}


def _component_name(value: Any | None) -> str | None:
    if value is None:
        return None
    return type(value).__name__


def _session_restore_summary(value: Any | None) -> dict[str, Any] | None:
    if value is None:
        return None
    fields = (
        "enabled",
        "include_transcript",
        "include_context",
        "include_events",
        "include_artifacts",
        "max_transcripts",
        "max_messages",
        "max_runtime_items",
        "max_chars",
    )
    return {
        field: getattr(value, field)
        for field in fields
        if hasattr(value, field)
    }


def _delegation_summary(value: Any | None) -> dict[str, Any] | None:
    if value is None:
        return None
    summary: dict[str, Any] = {"policy": type(value).__name__}
    max_depth = getattr(value, "max_depth", None)
    if max_depth is not None:
        summary["max_depth"] = max_depth
    return summary
