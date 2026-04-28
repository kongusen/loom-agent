"""Frozen public API expectations for the 0.8.x stabilization line."""

import loom
import loom.config as loom_config
import loom.runtime as loom_runtime


def test_top_level_stable_sdk_exports() -> None:
    stable = {
        "Agent",
        "Model",
        "Runtime",
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
        "Capability",
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
        "SkillInjectionPolicy",
        "ContextPolicy",
        "ContextProtocol",
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


def test_legacy_entry_points_are_explicitly_compatibility_exports() -> None:
    compatibility = {
        "AgentConfig",
        "AgentSpec",
        "ModelRef",
        "GenerationConfig",
        "create_agent",
    }

    assert compatibility <= set(loom.__all__)
    assert loom.AgentSpec is loom.AgentConfig
    assert loom.Model is loom.ModelRef
    assert loom.Generation is loom.GenerationConfig


def test_config_facade_is_advanced_configuration_only() -> None:
    exported = set(loom_config.__all__)

    assert "AgentConfig" in exported
    assert "RuntimeConfig" in exported
    assert "PolicyConfig" in exported
    assert "SessionConfig" not in exported
    assert "RunContext" not in exported
    assert "SignalAdapter" not in exported


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
