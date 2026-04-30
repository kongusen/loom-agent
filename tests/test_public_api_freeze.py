"""Frozen public API expectations for the 0.8.x stabilization line."""

import loom
import loom.config as loom_config
import loom.orchestration as loom_orchestration
import loom.runtime as loom_runtime


def test_top_level_stable_sdk_exports() -> None:
    stable = {
        "Agent",
        "Model",
        "Runtime",
        "Instructions",
        "Files",
        "Web",
        "Shell",
        "MCP",
        "Skill",
        "Knowledge",
        "Gateway",
        "Cron",
        "OrchestrationConfig",
        "ScheduleConfig",
        "ScheduledJob",
        "Generation",
        "Memory",
        "MemorySource",
        "MemoryResolver",
        "MemoryExtractor",
        "MemoryStore",
        "Toolset",
        "RuntimeTask",
        "RuntimeSignal",
        "SignalAdapter",
        "AttentionPolicy",
        "SessionConfig",
        "RunContext",
        "SessionStore",
        "FileSessionStore",
        "InMemorySessionStore",
        "SessionRestorePolicy",
        "SkillInjection",
        "ContextPolicy",
        "ContinuityPolicy",
        "Harness",
        "HarnessRequest",
        "HarnessCandidate",
        "QualityGate",
        "DelegationPolicy",
        "GovernancePolicy",
        "FeedbackPolicy",
        "tool",
        "KnowledgeResolver",
    }

    assert stable <= set(loom.__all__)


def test_removed_legacy_entry_points_are_not_top_level_exports() -> None:
    assert "AgentConfig" not in loom.__all__
    assert "ModelRef" not in loom.__all__
    assert "GenerationConfig" not in loom.__all__
    assert "ContextProtocol" not in loom.__all__
    assert "SkillInjectionPolicy" not in loom.__all__
    assert "Capability" not in loom.__all__
    assert "CapabilitySpec" not in loom.__all__
    assert "CapabilitySource" not in loom.__all__
    assert "CapabilityRegistry" not in loom.__all__
    assert "RuntimeCapabilityProvider" not in loom.__all__


def test_config_facade_is_advanced_configuration_only() -> None:
    exported = set(loom_config.__all__)

    assert "AgentConfig" in exported
    assert "RuntimeConfig" in exported
    assert "PolicyConfig" in exported
    assert "Model" in exported
    assert "Generation" in exported
    assert "ModelRef" not in exported
    assert "GenerationConfig" not in exported
    assert "SessionConfig" not in exported
    assert "RunContext" not in exported
    assert "SignalAdapter" not in exported
    assert "ContextProtocol" not in exported
    assert "SkillInjectionPolicy" not in exported


def test_runtime_facade_contains_runtime_mechanism_contracts() -> None:
    exported = set(loom_runtime.__all__)

    assert "RuntimeSignal" in exported
    assert "SignalAdapter" in exported
    assert "RuntimeSignalAdapter" in exported
    assert "SignalQueue" in exported
    assert "AgentLoop" in exported
    assert "Capability" in exported
    assert "JobRegistry" in exported
    assert "ScheduleTicker" in exported
    assert "ContextProtocol" not in exported
    assert "RuntimeContextProtocol" not in exported
    assert "ManagedContextProtocol" not in exported
    assert "SkillInjectionPolicy" not in exported
    assert "Event" not in exported


def test_orchestration_facade_uses_runtime_quality_contracts() -> None:
    exported = set(loom_orchestration.__all__)

    assert "GeneratorEvaluatorLoop" in exported
    assert "SprintResult" in exported
    assert "SprintContract" not in exported
