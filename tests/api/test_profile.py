"""Test API profile and knowledge"""

from pathlib import Path

import pytest
from loom.api import (
    AgentProfile,
    AgentConfig,
    KnowledgeRegistry,
    KnowledgeSource,
    TrustTier,
    PolicySet,
)


class TestProfile:
    """Test AgentProfile"""

    def test_profile_creation(self):
        """Test profile creation"""
        config = AgentConfig(name="test")
        profile = AgentProfile(
            id="test",
            name="Test Profile",
            config=config
        )
        assert profile.id == "test"
        assert profile.name == "Test Profile"

    def test_profile_from_preset(self):
        """Test profile from preset"""
        profile = AgentProfile.from_preset("coding")
        assert profile.id == "coding"
        assert "coding-core" in profile.skills

    def test_profile_from_yaml(self, tmp_path: Path):
        """Test profile loading from YAML."""
        profile_path = tmp_path / "profile.yaml"
        profile_path.write_text(
            """
id: repo-assistant
name: Repo Assistant
skills:
  - code-review
  - refactor
knowledge_sources:
  - wiki
config:
  name: repo-assistant
  system_prompt: You review repositories.
  llm:
    model: gpt-4.1-mini
    temperature: 0.2
    max_tokens: 2048
  tools:
    allow:
      - Read
      - Grep
  policy:
    max_depth: 7
    enable_verification: true
""".strip()
        )

        profile = AgentProfile.from_yaml(str(profile_path))
        assert profile.id == "repo-assistant"
        assert profile.name == "Repo Assistant"
        assert profile.skills == ["code-review", "refactor"]
        assert profile.knowledge_sources == ["wiki"]
        assert profile.config.system_prompt == "You review repositories."
        assert profile.config.llm.model == "gpt-4.1-mini"
        assert profile.config.llm.max_tokens == 2048
        assert profile.config.tools.allow == ["Read", "Grep"]
        assert profile.config.policy.max_depth == 7
        assert profile.config.policy.enable_verification is True

    def test_profile_from_yaml_missing_file(self):
        """Test missing profile YAML raises file error."""
        with pytest.raises(FileNotFoundError):
            AgentProfile.from_yaml("/nonexistent/profile.yaml")


class TestKnowledge:
    """Test KnowledgeRegistry"""

    def test_registry_creation(self):
        """Test registry creation"""
        registry = KnowledgeRegistry()
        assert isinstance(registry.sources, dict)

    def test_register_source(self):
        """Test register source"""
        registry = KnowledgeRegistry()
        source = KnowledgeSource(
            id="docs",
            type="web",
            scope="global",
            trust_tier=TrustTier.HIGH
        )
        registry.register(source)
        assert registry.get("docs") is not None

    def test_list_by_scope(self):
        """Test list by scope"""
        registry = KnowledgeRegistry()
        source1 = KnowledgeSource(
            id="s1", type="web", scope="global", trust_tier=TrustTier.HIGH
        )
        source2 = KnowledgeSource(
            id="s2", type="web", scope="project", trust_tier=TrustTier.MEDIUM
        )
        registry.register(source1)
        registry.register(source2)

        global_sources = registry.list_by_scope("global")
        assert len(global_sources) == 1


class TestPolicy:
    """Test PolicySet"""

    def test_policy_creation(self):
        """Test policy creation"""
        policy = PolicySet(id="test", name="Test Policy")
        assert policy.id == "test"
        assert isinstance(policy.deny, list)
